"""create_appointments

Revision ID: 004_create_appointments
Revises: 003_doctors_office_hours
Create Date: 2026-11-10 10:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_create_appointments'
down_revision: Union[str, None] = '003_doctors_office_hours'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUS_VALUES = ('PLANNED', 'COMPLETED', 'CANCELLED_BY_PATIENT', 'CANCELLED_BY_OFFICE', 'NO_SHOW')


def upgrade() -> None:
    op.create_table(
        'appointments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=False), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=False), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum(*STATUS_VALUES, name='appointmentstatus'), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id']),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('start_at < end_at', name='ck_appointments_range'),
    )
    op.create_index(op.f('ix_appointments_id'), 'appointments', ['id'], unique=False)
    op.create_index(op.f('ix_appointments_patient_id'), 'appointments', ['patient_id'], unique=False)
    op.create_index('ix_appointments_doctor_start', 'appointments', ['doctor_id', 'start_at'], unique=False)

    # Obsazené 15min sloty – UNIQUE(doctor_id, slot_start) je DB pojistka proti překryvu
    op.create_table(
        'appointment_slots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('appointment_id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('slot_start', sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('doctor_id', 'slot_start', name='uq_appointment_slots_doctor_slot'),
    )
    op.create_index(
        op.f('ix_appointment_slots_appointment_id'), 'appointment_slots', ['appointment_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_appointment_slots_appointment_id'), table_name='appointment_slots')
    op.drop_table('appointment_slots')
    op.drop_index('ix_appointments_doctor_start', table_name='appointments')
    op.drop_index(op.f('ix_appointments_patient_id'), table_name='appointments')
    op.drop_index(op.f('ix_appointments_id'), table_name='appointments')
    op.drop_table('appointments')
    sa.Enum(name='appointmentstatus').drop(op.get_bind(), checkfirst=True)
