"""appointment_cancellation

Revision ID: 006_appointment_cancellation
Revises: 005_visits_and_procedures
Create Date: 2026-11-11 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006_appointment_cancellation'
down_revision: Union[str, None] = '005_visits_and_procedures'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Evidence zrušení / nedostavení (FP5) – rezervace se nemaže, jen mění stav
    op.add_column('appointments', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('appointments', sa.Column('cancelled_by_user_id', sa.Integer(), nullable=True))
    op.add_column('appointments', sa.Column('cancellation_note', sa.Text(), nullable=True))
    op.create_foreign_key(
        'fk_appointments_cancelled_by_user', 'appointments', 'users',
        ['cancelled_by_user_id'], ['id'], ondelete='SET NULL',
    )
    # Výpočet spolehlivosti pacienta (počty podle stavu v časovém okně)
    op.create_index(
        'ix_appointments_patient_status_start', 'appointments', ['patient_id', 'status', 'start_at'], unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_appointments_patient_status_start', table_name='appointments')
    op.drop_constraint('fk_appointments_cancelled_by_user', 'appointments', type_='foreignkey')
    op.drop_column('appointments', 'cancellation_note')
    op.drop_column('appointments', 'cancelled_by_user_id')
    op.drop_column('appointments', 'cancelled_at')
