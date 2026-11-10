"""create_doctors_and_office_hours

Revision ID: 003_doctors_office_hours
Revises: 002_create_patients_table
Create Date: 2026-11-10 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_doctors_office_hours'
down_revision: Union[str, None] = '002_create_patients_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'doctors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('specialization', sa.String(length=100), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=False, server_default='#0284c7'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(op.f('ix_doctors_id'), 'doctors', ['id'], unique=False)

    op.create_table(
        'office_hours',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('weekday', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('weekday >= 0 AND weekday <= 6', name='ck_office_hours_weekday'),
        sa.CheckConstraint('start_time < end_time', name='ck_office_hours_range'),
    )
    op.create_index(op.f('ix_office_hours_id'), 'office_hours', ['id'], unique=False)
    op.create_index(op.f('ix_office_hours_doctor_id'), 'office_hours', ['doctor_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_office_hours_doctor_id'), table_name='office_hours')
    op.drop_index(op.f('ix_office_hours_id'), table_name='office_hours')
    op.drop_table('office_hours')
    op.drop_index(op.f('ix_doctors_id'), table_name='doctors')
    op.drop_table('doctors')
