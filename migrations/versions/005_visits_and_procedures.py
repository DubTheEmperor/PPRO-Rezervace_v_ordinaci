"""visits_and_procedures

Revision ID: 005_visits_and_procedures
Revises: 004_create_appointments
Create Date: 2026-11-11 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005_visits_and_procedures'
down_revision: Union[str, None] = '004_create_appointments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Číselník výkonů
    op.create_table(
        'procedures',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('points >= 0', name='ck_procedures_points'),
    )
    op.create_index(op.f('ix_procedures_id'), 'procedures', ['id'], unique=False)
    op.create_index(op.f('ix_procedures_code'), 'procedures', ['code'], unique=True)

    # Záznam o návštěvě (1:1 k rezervaci)
    op.create_table(
        'visits',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('appointment_id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'CLOSED', name='visitstatus'), nullable=False),
        sa.Column('clinical_note', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('updated_by_user_id', sa.Integer(), nullable=True),
        sa.Column('closed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id']),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id']),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['closed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('appointment_id'),
    )
    op.create_index(op.f('ix_visits_id'), 'visits', ['id'], unique=False)
    op.create_index(op.f('ix_visits_doctor_id'), 'visits', ['doctor_id'], unique=False)
    op.create_index(op.f('ix_visits_patient_id'), 'visits', ['patient_id'], unique=False)

    # Asociační entita M:N Návštěva ↔ Výkon (počet + snapshot bodů)
    op.create_table(
        'visit_procedures',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('visit_id', sa.Integer(), nullable=False),
        sa.Column('procedure_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('points_per_unit', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['visit_id'], ['visits.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['procedure_id'], ['procedures.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('visit_id', 'procedure_id', name='uq_visit_procedures_visit_procedure'),
        sa.CheckConstraint('quantity >= 1', name='ck_visit_procedures_quantity'),
        sa.CheckConstraint('points_per_unit >= 0', name='ck_visit_procedures_points'),
    )
    op.create_index(op.f('ix_visit_procedures_visit_id'), 'visit_procedures', ['visit_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_visit_procedures_visit_id'), table_name='visit_procedures')
    op.drop_table('visit_procedures')
    op.drop_index(op.f('ix_visits_patient_id'), table_name='visits')
    op.drop_index(op.f('ix_visits_doctor_id'), table_name='visits')
    op.drop_index(op.f('ix_visits_id'), table_name='visits')
    op.drop_table('visits')
    sa.Enum(name='visitstatus').drop(op.get_bind(), checkfirst=True)
    op.drop_index(op.f('ix_procedures_code'), table_name='procedures')
    op.drop_index(op.f('ix_procedures_id'), table_name='procedures')
    op.drop_table('procedures')
