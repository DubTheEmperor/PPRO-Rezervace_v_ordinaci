"""office_hours_kind

Typ bloku ordinačních hodin: OFFICE (ordinuje v ordinaci, lze rezervovat) nebo
ELSEWHERE (pravidelně ordinuje na jiném pracovišti, rezervovat nelze) a povinné
místo (`location`) u jiného pracoviště.

Revision ID: 009_office_hours_kind
Revises: 008_doctor_billing_identifiers
Create Date: 2026-11-13 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '009_office_hours_kind'
down_revision: Union[str, None] = '008_doctor_billing_identifiers'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'office_hours',
        sa.Column('kind', sa.String(length=16), nullable=False, server_default='OFFICE'),
    )
    op.add_column('office_hours', sa.Column('location', sa.String(length=100), nullable=True))
    op.create_check_constraint(
        'ck_office_hours_kind', 'office_hours', "kind IN ('OFFICE', 'ELSEWHERE')"
    )
    op.create_check_constraint(
        'ck_office_hours_location', 'office_hours', "kind = 'OFFICE' OR location IS NOT NULL"
    )

    # Demo data: MUDr. Malý ordinuje v úterý odpoledne na jiné adrese (zadání FP2).
    # Doplní se jen do existující databáze s demo lékařem a jen když úterní odpoledne
    # nekoliduje s jiným blokem; nová databáze dostane blok ze seedu.
    op.execute("""
        INSERT INTO office_hours (doctor_id, weekday, start_time, end_time, kind, location)
        SELECT d.id, 1, '13:00', '17:00', 'ELSEWHERE', 'Poliklinika Jih'
        FROM doctors d
        WHERE d.full_name = 'MUDr. Tomáš Malý'
          AND NOT EXISTS (
            SELECT 1 FROM office_hours oh
            WHERE oh.doctor_id = d.id AND oh.weekday = 1
              AND oh.start_time < '17:00' AND oh.end_time > '13:00'
          )
    """)


def downgrade() -> None:
    # Bez sloupce `kind` by bloky jiného pracoviště byly rezervovatelné – proto se smažou
    op.execute("DELETE FROM office_hours WHERE kind = 'ELSEWHERE'")
    op.drop_constraint('ck_office_hours_location', 'office_hours', type_='check')
    op.drop_constraint('ck_office_hours_kind', 'office_hours', type_='check')
    op.drop_column('office_hours', 'location')
    op.drop_column('office_hours', 'kind')
