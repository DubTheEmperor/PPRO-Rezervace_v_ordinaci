"""create_patients_table

Revision ID: 002_create_patients_table
Revises: 001_initial_users
Create Date: 2026-10-30 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_create_patients_table'
down_revision: Union[str, None] = '001_initial_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'patients',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('first_name', sa.String(length=50), nullable=False),
        sa.Column('last_name', sa.String(length=50), nullable=False),
        sa.Column('birth_year', sa.Integer(), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('insurance_number', sa.String(length=20), nullable=False),
        sa.Column('insurance_company_code', sa.String(length=10), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False
        ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_patients_id'), 'patients', ['id'], unique=False)
    op.create_index(op.f('ix_patients_last_name'), 'patients', ['last_name'], unique=False)
    op.create_index(op.f('ix_patients_phone_number'), 'patients', ['phone_number'], unique=False)
    op.create_index(op.f('ix_patients_insurance_number'), 'patients', ['insurance_number'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_patients_insurance_number'), table_name='patients')
    op.drop_index(op.f('ix_patients_phone_number'), table_name='patients')
    op.drop_index(op.f('ix_patients_last_name'), table_name='patients')
    op.drop_index(op.f('ix_patients_id'), table_name='patients')
    op.drop_table('patients')
