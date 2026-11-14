"""drop_doctor_specialization

Lékaři ordinace mají stejné zaměření, specializace se v systému neeviduje
(sloupec `doctors.specialization` se odstraňuje). Demo lékař MUDr. Tomáš Malý
dostane stejnou odbornost pro výkazy jako kolegové (001) – jen pokud má stále
původní hodnotu ze seedu (101).

Downgrade vrací prázdný sloupec (původní texty se nevrátí) a odbornost 101.

Revision ID: 012_drop_doctor_specialization
Revises: 011_rename_demo_receptionist
Create Date: 2026-11-14 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '012_drop_doctor_specialization'
down_revision: Union[str, None] = '011_rename_demo_receptionist'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO_DOCTOR = 'MUDr. Tomáš Malý'

_set_specialty = sa.text(
    "UPDATE doctors SET specialty_code = :new WHERE full_name = :name AND specialty_code = :old"
)


def upgrade() -> None:
    op.drop_column('doctors', 'specialization')
    op.get_bind().execute(_set_specialty, {"name": DEMO_DOCTOR, "old": "101", "new": "001"})


def downgrade() -> None:
    op.add_column('doctors', sa.Column('specialization', sa.String(length=100), nullable=True))
    op.get_bind().execute(_set_specialty, {"name": DEMO_DOCTOR, "old": "001", "new": "101"})
