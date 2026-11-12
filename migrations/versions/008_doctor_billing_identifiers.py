"""doctor_billing_identifiers

Identifikátory lékaře pro vykazování pojišťovnám (FP7): IČP (identifikační
číslo pracoviště, 8 číslic) a kód odbornosti (3 číslice). Obě pole jsou
nepovinná – v demu obsahují syntetické hodnoty ze seedu.

Revision ID: 008_doctor_billing_identifiers
Revises: 007_drop_notes
Create Date: 2026-11-12 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '008_doctor_billing_identifiers'
down_revision: Union[str, None] = '007_drop_notes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('doctors', sa.Column('icp', sa.String(length=8), nullable=True))
    op.add_column('doctors', sa.Column('specialty_code', sa.String(length=3), nullable=True))


def downgrade() -> None:
    op.drop_column('doctors', 'specialty_code')
    op.drop_column('doctors', 'icp')
