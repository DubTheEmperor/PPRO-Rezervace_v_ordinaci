"""FP7 – Měsíční výkaz pro pojišťovny (API, oprávnění, součty bodů, exporty CSV/PDF)."""
from datetime import date, datetime, timedelta
import pytest
from src.business.scheduling import local_now, slot_starts
from src.infrastructure.models.appointment_model import AppointmentModel, AppointmentStatus
from src.infrastructure.models.visit_model import VisitModel, VisitStatus
from src.infrastructure.repositories.appointment_repository import AppointmentRepository
from src.infrastructure.repositories.procedure_repository import ProcedureRepository
from src.infrastructure.repositories.visit_repository import VisitRepository
from tests.helpers import auth, create_patient

URL = "/api/v1/reports/monthly"
EXPORT_URL = "/api/v1/reports/monthly/export"


def previous_month() -> date:
    """První den minulého měsíce – období, které celé leží v minulosti."""
    first = local_now().date().replace(day=1)
    return (first - timedelta(days=1)).replace(day=1)


def month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def add_appointment(db, doctor_id, patient_id, start_at, *, items=None, visit_status=None, minutes=15,
                    status=AppointmentStatus.PLANNED):
    """Vloží rezervaci (a volitelně záznam návštěvy s výkony) přímo přes repozitáře.

    `items` = [(kód výkonu, počet)]. Body se berou z číselníku jako snapshot.
    """
    end_at = start_at + timedelta(minutes=minutes)
    if visit_status == VisitStatus.CLOSED:
        status = AppointmentStatus.COMPLETED
    appointment = AppointmentRepository(db).create_with_slots(
        AppointmentModel(
            doctor_id=doctor_id, patient_id=patient_id, start_at=start_at, end_at=end_at,
            reason="Kontrola", status=status,
        ),
        slot_starts(start_at, end_at) if status in (AppointmentStatus.PLANNED, AppointmentStatus.COMPLETED) else [],
    )
    if visit_status is not None:
        procedures = {p.code: p for p in ProcedureRepository(db).search(limit=200)}
        repo = VisitRepository(db)
        visit = repo.create(VisitModel(
            appointment_id=appointment.id, doctor_id=doctor_id, patient_id=patient_id, status=visit_status,
        ))
        repo.replace_items(visit, [
            (procedures[code].id, quantity, procedures[code].points) for code, quantity in (items or [])
        ])
        repo.save(visit)
    return appointment


@pytest.fixture
def hruba(doctors_by_username):
    return doctors_by_username["hruba"]


@pytest.fixture
def patients(client, receptionist_token):
    return {
        "vzp": create_patient(client, receptionist_token, insurance_number="9001011234",
                              last_name="Vzpová", insurance_company_code="111"),
        "vzp2": create_patient(client, receptionist_token, insurance_number="9002021234",
                               last_name="Další", phone_number="+420777000222", insurance_company_code="111"),
        "ozp": create_patient(client, receptionist_token, insurance_number="9103031234",
                              last_name="Ozpový", phone_number="+420777000333", insurance_company_code="207"),
    }


@pytest.fixture
def month_data(db_session, hruba, patients):
    """Minulý měsíc u Hrubé: 2× VZP a 1× OZP uzavřeno, koncept, nezapsaná, zrušená, nedostavení."""
    first = previous_month()
    at = lambda day, hh, mm=0: datetime.combine(first + timedelta(days=day), datetime.min.time()).replace(hour=hh, minute=mm)
    d = hruba["id"]
    add_appointment(db_session, d, patients["vzp"]["id"], at(1, 8), visit_status=VisitStatus.CLOSED,
                    items=[("01021", 1), ("09215", 3)])                     # 520 + 3×16 = 568
    add_appointment(db_session, d, patients["vzp2"]["id"], at(2, 9), visit_status=VisitStatus.CLOSED,
                    items=[("01025", 1)])                                   # 70
    add_appointment(db_session, d, patients["ozp"]["id"], at(3, 10), visit_status=VisitStatus.CLOSED,
                    items=[("01023", 1), ("09543", 2)])                     # 130 + 2×30 = 190
    add_appointment(db_session, d, patients["vzp"]["id"], at(4, 8), visit_status=VisitStatus.DRAFT,
                    items=[("01021", 1)])                                   # koncept – nezapočítá se
    add_appointment(db_session, d, patients["ozp"]["id"], at(5, 8))         # nezapsaná
    add_appointment(db_session, d, patients["vzp2"]["id"], at(6, 8), status=AppointmentStatus.CANCELLED_BY_PATIENT)
    add_appointment(db_session, d, patients["vzp2"]["id"], at(7, 8), status=AppointmentStatus.NO_SHOW)
    return first


def get_report(client, token, doctor_id, month, **params):
    return client.get(URL, params={"doctor_id": doctor_id, "month": month, **params}, headers=auth(token))


# --- Součty a členění -----------------------------------------------------------------------

def test_report_sums_closed_visits_grouped_by_insurance(client, receptionist_token, hruba, month_data):
    response = get_report(client, receptionist_token, hruba["id"], month_key(month_data))
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["total_points"] == 568 + 70 + 190
    assert data["visit_count"] == 3
    assert data["patient_count"] == 3
    assert data["item_count"] == 1 + 3 + 1 + 1 + 2
    assert [(s["code"], s["visit_count"], s["total_points"]) for s in data["sections"]] == [
        ("111", 2, 638), ("207", 1, 190),
    ]
    injection = data["sections"][0]["visits"][0]["items"][1]
    assert injection == {"code": "09215", "name": injection["name"], "quantity": 3,
                         "points_per_unit": 16, "total_points": 48}
    summary = {s["code"]: (s["quantity"], s["total_points"]) for s in data["procedure_summary"]}
    assert summary == {"01021": (1, 520), "01023": (1, 130), "01025": (1, 70),
                       "09215": (3, 48), "09543": (2, 60)}
    assert data["doctor"]["icp"] == "52999101"
    assert data["practice"]["icz"]
    assert data["period_complete"] is True


def test_report_warns_about_unfinished_visits_only(client, receptionist_token, hruba, month_data):
    data = get_report(client, receptionist_token, hruba["id"], month_key(month_data)).json()
    states = sorted(u["state"] for u in data["unfinished"])
    # Koncept a nezapsaná rezervace; zrušená a nedostavení se do upozornění nepočítají
    assert states == ["DRAFT", "TO_RECORD"]


def test_report_insurance_filter(client, receptionist_token, hruba, month_data):
    data = get_report(client, receptionist_token, hruba["id"], month_key(month_data), insurance_code="207").json()
    assert [s["code"] for s in data["sections"]] == ["207"]
    assert data["total_points"] == 190
    assert data["insurance_label"].startswith("207")
    assert [u["state"] for u in data["unfinished"]] == ["TO_RECORD"]


def test_report_uses_points_snapshot(client, admin_token, receptionist_token, hruba, month_data):
    procedure = next(p for p in client.get("/api/v1/procedures", headers=auth(admin_token)).json()
                     if p["code"] == "01021")
    response = client.put(f"/api/v1/procedures/{procedure['id']}", json={"points": 999},
                          headers=auth(admin_token))
    assert response.status_code == 200, response.text
    data = get_report(client, receptionist_token, hruba["id"], month_key(month_data)).json()
    assert data["total_points"] == 568 + 70 + 190


def test_report_month_boundaries(client, db_session, receptionist_token, hruba, patients):
    first = previous_month()
    next_first = local_now().date().replace(day=1)
    last_slot = datetime.combine(next_first, datetime.min.time()) - timedelta(minutes=15)
    d, p = hruba["id"], patients["vzp"]["id"]
    add_appointment(db_session, d, p, datetime.combine(first, datetime.min.time()),
                    visit_status=VisitStatus.CLOSED, items=[("01030", 1)])          # 1. den 00:00 – ano
    add_appointment(db_session, d, p, last_slot, visit_status=VisitStatus.CLOSED,
                    items=[("02230", 1)])                                            # poslední den 23:45 – ano
    add_appointment(db_session, d, p, datetime.combine(next_first, datetime.min.time()),
                    visit_status=VisitStatus.CLOSED, items=[("09127", 1)])          # další měsíc – ne
    add_appointment(db_session, d, p, datetime.combine(first, datetime.min.time()) - timedelta(minutes=15),
                    visit_status=VisitStatus.CLOSED, items=[("09511", 1)])          # předchozí měsíc – ne

    data = get_report(client, receptionist_token, d, month_key(first)).json()
    codes = sorted(i["code"] for s in data["sections"] for v in s["visits"] for i in v["items"])
    assert codes == ["01030", "02230"]


def test_report_excludes_other_doctor(client, db_session, receptionist_token, doctors_by_username, patients):
    first = previous_month()
    maly = doctors_by_username["maly"]
    add_appointment(db_session, maly["id"], patients["vzp"]["id"],
                    datetime.combine(first + timedelta(days=2), datetime.min.time()).replace(hour=9),
                    visit_status=VisitStatus.CLOSED, items=[("01021", 1)])
    hruba_data = get_report(client, receptionist_token, doctors_by_username["hruba"]["id"], month_key(first)).json()
    maly_data = get_report(client, receptionist_token, maly["id"], month_key(first)).json()
    assert hruba_data["total_points"] == 0 and hruba_data["sections"] == []
    assert maly_data["total_points"] == 520


def test_current_month_is_not_complete(client, db_session, receptionist_token, hruba, patients):
    today = local_now().date()
    future = datetime.combine(today + timedelta(days=40), datetime.min.time()).replace(hour=9)
    add_appointment(db_session, hruba["id"], patients["vzp"]["id"], future)  # budoucí – není „nezapsaná“
    data = get_report(client, receptionist_token, hruba["id"], month_key(today)).json()
    assert data["period_complete"] is False
    assert data["unfinished"] == []


# --- Validace a oprávnění -------------------------------------------------------------------

@pytest.mark.parametrize("month", ["2026-13", "2026/10", "10-2026", "abc", "2026-1"])
def test_invalid_month_format(client, receptionist_token, hruba, month):
    assert get_report(client, receptionist_token, hruba["id"], month).status_code == 400


def test_future_month_rejected(client, receptionist_token, hruba):
    today = local_now().date()
    future = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    response = get_report(client, receptionist_token, hruba["id"], month_key(future))
    assert response.status_code == 400
    assert "nezačal" in response.json()["detail"]


def test_unknown_insurance_code(client, receptionist_token, hruba):
    response = get_report(client, receptionist_token, hruba["id"], month_key(previous_month()), insurance_code="999")
    assert response.status_code == 400


def test_unknown_doctor(client, receptionist_token):
    assert get_report(client, receptionist_token, 9999, month_key(previous_month())).status_code == 404


def test_permissions(client, admin_token, receptionist_token, doctor_token, doctor2_token, hruba):
    month = month_key(previous_month())
    assert get_report(client, admin_token, hruba["id"], month).status_code == 200
    assert get_report(client, receptionist_token, hruba["id"], month).status_code == 200
    assert get_report(client, doctor_token, hruba["id"], month).status_code == 200      # vlastní výkaz
    assert get_report(client, doctor2_token, hruba["id"], month).status_code == 403     # cizí lékař
    assert client.get(URL, params={"doctor_id": hruba["id"], "month": month}).status_code == 401


def test_report_has_no_clinical_notes(client, receptionist_token, hruba, month_data):
    response = get_report(client, receptionist_token, hruba["id"], month_key(month_data))
    assert "clinical_note" not in response.text


# --- Exporty ---------------------------------------------------------------------------------

def export(client, token, doctor_id, month, fmt, **params):
    return client.get(EXPORT_URL, params={"doctor_id": doctor_id, "month": month, "format": fmt, **params},
                      headers=auth(token))


def test_export_csv(client, receptionist_token, hruba, month_data):
    response = export(client, receptionist_token, hruba["id"], month_key(month_data), "csv")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    disposition = response.headers["content-disposition"]
    assert f'filename="vykaz_hruba_{month_key(month_data)}.csv"' in disposition
    assert response.content.startswith(b"\xef\xbb\xbf")  # BOM pro Excel

    lines = response.content.decode("utf-8-sig").splitlines()
    assert lines[0].split(";")[:3] == ["Pojišťovna", "Datum", "Příjmení"]
    detail_rows = [line.split(";") for line in lines[1:] if line and line[:3].isdigit()]
    assert len(detail_rows) == 5  # pět položek výkonů
    assert ["207", "Ozpový"] == [detail_rows[-1][0], detail_rows[-1][2]]
    total = next(line.split(";") for line in lines if line.startswith("Celkem;"))
    assert total[-1] == str(568 + 70 + 190)
    assert any(line.startswith("Neuzavřeno;") for line in lines)


def test_export_pdf(client, receptionist_token, hruba, month_data):
    response = export(client, receptionist_token, hruba["id"], month_key(month_data), "pdf", insurance_code="111")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert f'vykaz_hruba_{month_key(month_data)}_111.pdf' in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000


def test_export_pdf_empty_month(client, receptionist_token, hruba):
    response = export(client, receptionist_token, hruba["id"], month_key(previous_month()), "pdf")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_export_invalid_format(client, receptionist_token, hruba):
    assert export(client, receptionist_token, hruba["id"], month_key(previous_month()), "xlsx").status_code == 422


def test_export_respects_permissions(client, doctor2_token, hruba):
    assert export(client, doctor2_token, hruba["id"], month_key(previous_month()), "csv").status_code == 403
