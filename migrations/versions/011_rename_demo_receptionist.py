"""rename_demo_receptionist

Datová migrace: demo recepční se zobrazuje jako „Věra Nováková“ bez doplňku
„(Recepce)“ – roli ukazuje štítek v rozhraní, ostatní demo profily doplněk nemají.
Jméno se změní jen tehdy, pokud ho mezitím nikdo neupravil.

Revision ID: 011_rename_demo_receptionist
Revises: 010_doctor_sick_days
Create Date: 2026-11-14 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '011_rename_demo_receptionist'
down_revision: Union[str, None] = '010_doctor_sick_days'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_NAME = 'Věra Nováková (Recepce)'
NEW_NAME = 'Věra Nováková'

_rename = sa.text(
    "UPDATE users SET full_name = :new WHERE username = 'vera' AND full_name = :old"
)


def upgrade() -> None:
    op.get_bind().execute(_rename, {"old": OLD_NAME, "new": NEW_NAME})


def downgrade() -> None:
    op.get_bind().execute(_rename, {"old": NEW_NAME, "new": OLD_NAME})
