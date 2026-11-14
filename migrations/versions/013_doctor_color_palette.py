"""doctor_color_palette

Barvy lékařů jsou nově jen z palety „Tlumené klidné“ (validuje DTO, viz
src/business/doctor_colors.py). Datová migrace:
- tři demo barvy ze seedu se převedou na odpovídající barvy palety,
- ostatní lékaři s barvou mimo paletu dostanou postupně (podle id) první volnou
  barvu palety, aby API nevracelo barvy, které formulář neumí zobrazit,
- výchozí hodnota sloupce se změní na první barvu palety.

Downgrade vrací jen tři demo barvy a původní výchozí hodnotu; barvy ostatních
lékařů převedené na paletu se nevracejí (původní hodnota se neukládá).

Paleta je zde jako konstanta – migrace nezávisí na aplikačním kódu.

Revision ID: 013_doctor_color_palette
Revises: 012_drop_doctor_specialization
Create Date: 2026-11-15 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '013_doctor_color_palette'
down_revision: Union[str, None] = '012_drop_doctor_specialization'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PALETTE = ['#3E5C9A', '#5F7F3B', '#7A4E8C', '#8A6D3B', '#4F5B66']
DEMO_MAPPING = {
    '#0284C7': '#3E5C9A',
    '#059669': '#5F7F3B',
    '#9333EA': '#7A4E8C',
}
OLD_DEFAULT = '#0284c7'

_set_color = sa.text("UPDATE doctors SET color = :new WHERE id = :id")


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, color FROM doctors ORDER BY id")).fetchall()

    colors = {row.id: (row.color or '').upper() for row in rows}
    for doctor_id, color in colors.items():
        if color in DEMO_MAPPING:
            colors[doctor_id] = DEMO_MAPPING[color]

    used = [c for c in colors.values() if c in PALETTE]
    for doctor_id, color in colors.items():
        if color not in PALETTE:
            free = next((c for c in PALETTE if c not in used), PALETTE[len(used) % len(PALETTE)])
            colors[doctor_id] = free
            used.append(free)

    for row in rows:
        if colors[row.id] != row.color:
            bind.execute(_set_color, {"id": row.id, "new": colors[row.id]})

    op.alter_column('doctors', 'color', server_default=PALETTE[0])


def downgrade() -> None:
    bind = op.get_bind()
    for old, new in DEMO_MAPPING.items():
        bind.execute(
            sa.text("UPDATE doctors SET color = :old WHERE upper(color) = :new"),
            {"old": old.lower(), "new": new},
        )
    op.alter_column('doctors', 'color', server_default=OLD_DEFAULT)
