"""doctor_sick_days

Nemoc lékaře (otevřený bod 5): tabulka nemocných dnů lékaře, nové stavy rezervace
TO_RESCHEDULE (K přeobjednání) a RESCHEDULED (Přeobjednáno) a odkaz na novou
rezervaci `appointments.rescheduled_to_id`.

Revision ID: 010_doctor_sick_days
Revises: 009_office_hours_kind
Create Date: 2026-11-13 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '010_doctor_sick_days'
down_revision: Union[str, None] = '009_office_hours_kind'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_STATUSES = ('PLANNED', 'COMPLETED', 'CANCELLED_BY_PATIENT', 'CANCELLED_BY_OFFICE', 'NO_SHOW')
NEW_STATUSES = ('TO_RESCHEDULE', 'RESCHEDULED')


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == 'postgresql'


def upgrade() -> None:
    if _is_postgres():
        # Nové hodnoty enumu musí být potvrzené dřív, než je někdo použije
        with op.get_context().autocommit_block():
            for value in NEW_STATUSES:
                op.execute(f"ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS '{value}'")

    op.create_table(
        'doctor_sick_days',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('doctor_id', 'day', name='uq_doctor_sick_days_doctor_day'),
    )
    op.create_index('ix_doctor_sick_days_doctor_id', 'doctor_sick_days', ['doctor_id'])

    op.add_column('appointments', sa.Column('rescheduled_to_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_appointments_rescheduled_to', 'appointments', 'appointments',
        ['rescheduled_to_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    # Termíny čekající na přeobjednání mají stále obsazené sloty – vrátí se do plánu.
    # Přeobjednané termíny už sloty nemají a nahradila je nová rezervace – zrušeno ordinací.
    op.execute("UPDATE appointments SET status = 'PLANNED' WHERE status = 'TO_RESCHEDULE'")
    op.execute("UPDATE appointments SET status = 'CANCELLED_BY_OFFICE' WHERE status = 'RESCHEDULED'")

    op.drop_constraint('fk_appointments_rescheduled_to', 'appointments', type_='foreignkey')
    op.drop_column('appointments', 'rescheduled_to_id')
    op.drop_index('ix_doctor_sick_days_doctor_id', table_name='doctor_sick_days')
    op.drop_table('doctor_sick_days')

    if _is_postgres():
        # PostgreSQL neumí hodnotu z enumu odebrat – typ se vytvoří znovu bez nových stavů
        values = ", ".join(f"'{v}'" for v in OLD_STATUSES)
        op.execute("ALTER TYPE appointmentstatus RENAME TO appointmentstatus_old")
        op.execute(f"CREATE TYPE appointmentstatus AS ENUM ({values})")
        op.execute(
            "ALTER TABLE appointments ALTER COLUMN status TYPE appointmentstatus "
            "USING status::text::appointmentstatus"
        )
        op.execute("DROP TYPE appointmentstatus_old")
