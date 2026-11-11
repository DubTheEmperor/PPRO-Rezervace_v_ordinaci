"""drop_notes

Odstranění volné poznámky k pacientovi a poznámky ke zrušení rezervace
(rozhodnutí vývojáře – viz README, changelog 2026-11-11).

Revision ID: 007_drop_notes
Revises: 006_appointment_cancellation
Create Date: 2026-11-11 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '007_drop_notes'
down_revision: Union[str, None] = '006_appointment_cancellation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('appointments', 'cancellation_note')
    op.drop_column('patients', 'notes')


def downgrade() -> None:
    op.add_column('patients', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('appointments', sa.Column('cancellation_note', sa.Text(), nullable=True))
