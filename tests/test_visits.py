"""FP4 – záznam o uskutečněné návštěvě: kauzalita, oprávnění, M:N výkony, neměnnost."""
import pytest
from tests.helpers import (
    auth, book, create_patient, last_week_monday, make_past_appointment, next_week_monday,
)


@pytest.fixture
def hruba_id(doctors_by_username):
    return doctors_by_username["hruba"]["id"]


@pytest.fixture
def patient(client, receptionist_token):
    return create_patient(client, receptionist_token)


@pytest.fixture
def past_appt(db_session, hruba_id, patient):
    return make_past_appointment(db_session, hruba_id, patient["id"])


@pytest.fixture
def procedures(client, admin_token):
    data = client.get("/api/v1/procedures", params={"limit": 200}, headers=auth(admin_token)).json()
    return {p["code"]: p for p in data}


def open_visit(client, token, appointment_id):
    return client.post(f"/api/v1/appointments/{appointment_id}/visit", headers=auth(token))


def save(client, token, visit_id, items, note=None):
    return client.put(
        f"/api/v1/visits/{visit_id}",
        json={"clinical_note": note, "items": items},
        headers=auth(token),
    )


# --- Kauzální integrita a oprávnění ------------------------------------------------------------

def test_cannot_record_visit_for_future_appointment(client, receptionist_token, doctor_token, hruba_id, patient):
    future = book(client, receptionist_token, hruba_id, patient["id"], next_week_monday(), "09:00", "09:30").json()
    response = open_visit(client, doctor_token, future["id"])
    assert response.status_code == 400
    assert "neproběhla" in response.json()["detail"]


def test_owner_doctor_opens_draft(client, doctor_token, past_appt):
    response = open_visit(client, doctor_token, past_appt.id)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "DRAFT"
    assert data["items"] == [] and data["total_points"] == 0


def test_open_visit_is_idempotent(client, doctor_token, past_appt):
    first = open_visit(client, doctor_token, past_appt.id).json()
    second = open_visit(client, doctor_token, past_appt.id).json()
    assert first["id"] == second["id"]


def test_other_doctor_and_receptionist_cannot_record(client, doctor2_token, receptionist_token, past_appt):
    assert open_visit(client, doctor2_token, past_appt.id).status_code == 403
    assert open_visit(client, receptionist_token, past_appt.id).status_code == 403


def test_admin_can_record(client, admin_token, past_appt):
    assert open_visit(client, admin_token, past_appt.id).status_code == 200


# --- Výkony (M:N s počtem) -----------------------------------------------------------------------

def test_save_items_and_total_points(client, doctor_token, past_appt, procedures):
    visit = open_visit(client, doctor_token, past_appt.id).json()
    exam, injection = procedures["01021"], procedures["09215"]
    response = save(client, doctor_token, visit["id"], [
        {"procedure_id": exam["id"], "quantity": 1},
        {"procedure_id": injection["id"], "quantity": 3},
    ], note="Bez komplikací.")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["clinical_note"] == "Bez komplikací."
    assert [(i["code"], i["quantity"]) for i in data["items"]] == [("01021", 1), ("09215", 3)]
    assert data["total_points"] == exam["points"] + 3 * injection["points"]


def test_duplicate_procedure_rejected(client, doctor_token, past_appt, procedures):
    visit = open_visit(client, doctor_token, past_appt.id).json()
    pid = procedures["09215"]["id"]
    response = save(client, doctor_token, visit["id"], [
        {"procedure_id": pid, "quantity": 1}, {"procedure_id": pid, "quantity": 2},
    ])
    assert response.status_code == 400


def test_invalid_quantity_and_unknown_procedure(client, doctor_token, past_appt, procedures):
    visit = open_visit(client, doctor_token, past_appt.id).json()
    assert save(client, doctor_token, visit["id"], [{"procedure_id": procedures["09215"]["id"], "quantity": 0}]).status_code == 422
    assert save(client, doctor_token, visit["id"], [{"procedure_id": 99999, "quantity": 1}]).status_code == 400


def test_inactive_procedure_rejected(client, admin_token, doctor_token, past_appt, procedures):
    proc = procedures["09547"]
    client.put(f"/api/v1/procedures/{proc['id']}", json={"is_active": False}, headers=auth(admin_token))
    visit = open_visit(client, doctor_token, past_appt.id).json()
    response = save(client, doctor_token, visit["id"], [{"procedure_id": proc["id"], "quantity": 1}])
    assert response.status_code == 400


def test_points_snapshot_not_affected_by_codebook_change(client, admin_token, doctor_token, past_appt, procedures):
    proc = procedures["09127"]
    visit = open_visit(client, doctor_token, past_appt.id).json()
    save(client, doctor_token, visit["id"], [{"procedure_id": proc["id"], "quantity": 2}])
    client.put(f"/api/v1/procedures/{proc['id']}", json={"points": proc["points"] + 500}, headers=auth(admin_token))

    # Uložení konceptu znovu (např. úprava poznámky) zachová původní body položky
    data = save(client, doctor_token, visit["id"], [{"procedure_id": proc["id"], "quantity": 2}], note="x").json()
    assert data["items"][0]["points_per_unit"] == proc["points"]
    assert data["total_points"] == 2 * proc["points"]


# --- Uzavření a neměnnost -------------------------------------------------------------------------

def test_close_requires_items(client, doctor_token, past_appt):
    visit = open_visit(client, doctor_token, past_appt.id).json()
    response = client.post(f"/api/v1/visits/{visit['id']}/close", headers=auth(doctor_token))
    assert response.status_code == 400


def test_close_locks_visit_and_completes_appointment(
    client, doctor_token, receptionist_token, past_appt, procedures, hruba_id
):
    visit = open_visit(client, doctor_token, past_appt.id).json()
    save(client, doctor_token, visit["id"], [{"procedure_id": procedures["01025"]["id"], "quantity": 1}])
    closed = client.post(f"/api/v1/visits/{visit['id']}/close", headers=auth(doctor_token))
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"
    assert closed.json()["closed_by_name"] == "MUDr. Jana Hrubá"

    # Uzavřenou návštěvu nelze měnit ani znovu uzavřít
    assert save(client, doctor_token, visit["id"], []).status_code == 409
    assert client.post(f"/api/v1/visits/{visit['id']}/close", headers=auth(doctor_token)).status_code == 409

    # Rezervace je uskutečněná a v kalendáři zůstává (slot neuvolní)
    detail = client.get(f"/api/v1/appointments/{past_appt.id}", headers=auth(receptionist_token)).json()
    assert detail["status"] == "COMPLETED"
    calendar = client.get(
        f"/api/v1/doctors/{hruba_id}/calendar",
        params={"week_start": last_week_monday().isoformat()},
        headers=auth(receptionist_token),
    ).json()
    assert [a["status"] for a in calendar["appointments"]] == ["COMPLETED"]


def test_visit_cannot_be_deleted(client, admin_token, past_appt):
    visit = open_visit(client, admin_token, past_appt.id).json()
    assert client.delete(f"/api/v1/visits/{visit['id']}", headers=auth(admin_token)).status_code == 405


# --- Fronta návštěv s filtry -------------------------------------------------------------------

def queue(client, token, doctor_id, queue_filter="pending", **params):
    return client.get(
        f"/api/v1/doctors/{doctor_id}/visit-queue",
        params={"filter": queue_filter, **params},
        headers=auth(token),
    )


@pytest.fixture
def three_states(client, db_session, doctor_token, receptionist_token, hruba_id, patient, procedures):
    """Tři proběhlé návštěvy minulého pondělí: uzavřená (8:00), koncept (8:15), k zápisu (8:30)."""
    p2 = create_patient(client, receptionist_token, insurance_number="9104041234", last_name="Druhý")
    p3 = create_patient(client, receptionist_token, insurance_number="9105051234", last_name="Třetí")
    a1 = make_past_appointment(db_session, hruba_id, patient["id"], "08:00", "08:15")
    a2 = make_past_appointment(db_session, hruba_id, p2["id"], "08:15", "08:30")
    a3 = make_past_appointment(db_session, hruba_id, p3["id"], "08:30", "08:45")
    v1 = open_visit(client, doctor_token, a1.id).json()
    save(client, doctor_token, v1["id"], [{"procedure_id": procedures["01025"]["id"], "quantity": 1}])
    client.post(f"/api/v1/visits/{v1['id']}/close", headers=auth(doctor_token))
    open_visit(client, doctor_token, a2.id)
    return a1, a2, a3


def test_pending_queue_finds_old_unrecorded_visits_without_knowing_the_date(
    client, doctor_token, hruba_id, three_states
):
    _, a2, a3 = three_states
    data = queue(client, doctor_token, hruba_id).json()
    # nejnovější nahoře: k zápisu (8:30), koncept (8:15)
    assert [(i["appointment_id"], i["state"]) for i in data["items"]] == [(a3.id, "TO_RECORD"), (a2.id, "DRAFT")]
    assert data["counts"]["pending"] == 2
    assert data["counts"]["draft"] == 1
    assert data["counts"]["closed"] == 1
    assert data["can_record"] is True


def test_queue_filters(client, doctor_token, hruba_id, three_states):
    a1, a2, a3 = three_states
    assert [i["appointment_id"] for i in queue(client, doctor_token, hruba_id, "draft").json()["items"]] == [a2.id]
    assert [i["appointment_id"] for i in queue(client, doctor_token, hruba_id, "closed").json()["items"]] == [a1.id]
    assert [i["appointment_id"] for i in queue(client, doctor_token, hruba_id, "all").json()["items"]] == [a3.id, a2.id, a1.id]
    assert queue(client, doctor_token, hruba_id, "today").json()["items"] == []
    assert queue(client, doctor_token, hruba_id, "nesmysl").status_code == 400


def test_queue_excludes_future_days_but_today_filter_shows_waiting(
    client, db_session, doctor_token, hruba_id, patient, monkeypatch
):
    from datetime import datetime, timedelta
    from src.business import scheduling
    from src.business.scheduling import slot_starts
    from src.infrastructure.models.appointment_model import AppointmentModel
    from src.infrastructure.repositories.appointment_repository import AppointmentRepository

    # „Teď“ je pevně pondělí příštího týdne 10:00 – test nezávisí na skutečném čase
    day = next_week_monday()
    monkeypatch.setattr(scheduling, "local_now", lambda: datetime.combine(day, datetime.min.time()).replace(hour=10))

    repo = AppointmentRepository(db_session)
    created = {}
    for label, start in (("past", datetime.combine(day, datetime.min.time()).replace(hour=9)),
                         ("waiting", datetime.combine(day, datetime.min.time()).replace(hour=11)),
                         ("tomorrow", datetime.combine(day + timedelta(days=1), datetime.min.time()).replace(hour=9))):
        created[label] = repo.create_with_slots(
            AppointmentModel(doctor_id=hruba_id, patient_id=patient["id"], start_at=start,
                             end_at=start + timedelta(minutes=15), reason=label),
            slot_starts(start, start + timedelta(minutes=15)),
        ).id

    today = queue(client, doctor_token, hruba_id, "today").json()
    assert [(i["appointment_id"], i["state"]) for i in today["items"]] == [
        (created["waiting"], "WAITING"), (created["past"], "TO_RECORD"),
    ]
    # „Vše“ nezahrnuje budoucí dny (ty řeší kalendář rezervací)
    assert [i["appointment_id"] for i in queue(client, doctor_token, hruba_id, "all").json()["items"]] == [
        created["waiting"], created["past"],
    ]
    pending = queue(client, doctor_token, hruba_id, "pending").json()
    assert [i["appointment_id"] for i in pending["items"]] == [created["past"]]
    assert pending["counts"]["today"] == 2


def test_queue_pagination(client, db_session, doctor_token, hruba_id, patient):
    for start, end in (("08:00", "08:15"), ("08:15", "08:30"), ("08:30", "08:45")):
        make_past_appointment(db_session, hruba_id, patient["id"], start, end)
    first = queue(client, doctor_token, hruba_id, limit=2).json()
    assert len(first["items"]) == 2 and first["has_more"] is True
    second = queue(client, doctor_token, hruba_id, limit=2, before=first["items"][-1]["start_at"]).json()
    assert len(second["items"]) == 1 and second["has_more"] is False
    assert second["items"][0]["start_at"] < first["items"][-1]["start_at"]


def test_queue_permissions(client, doctor2_token, receptionist_token, admin_token, hruba_id, three_states):
    assert queue(client, receptionist_token, hruba_id).status_code == 403
    assert queue(client, doctor2_token, hruba_id).status_code == 403
    admin_view = queue(client, admin_token, hruba_id)
    assert admin_view.status_code == 200 and admin_view.json()["can_record"] is True


def test_pending_count(client, doctor_token, doctor2_token, admin_token, receptionist_token, three_states):
    def count(token):
        return client.get("/api/v1/visits/pending-count", headers=auth(token))
    assert count(doctor_token).json()["pending"] == 2
    assert count(doctor2_token).json()["pending"] == 0
    assert count(admin_token).json()["pending"] == 2
    assert count(receptionist_token).status_code == 403


def test_receptionist_cannot_read_visit_detail(client, doctor_token, doctor2_token, receptionist_token, past_appt):
    visit = open_visit(client, doctor_token, past_appt.id).json()
    assert client.get(f"/api/v1/visits/{visit['id']}", headers=auth(receptionist_token)).status_code == 403
    # Ostatní lékaři záznam vidí (kontinuita péče), měnit ho ale nemohou
    assert client.get(f"/api/v1/visits/{visit['id']}", headers=auth(doctor2_token)).status_code == 200
    assert save(client, doctor2_token, visit["id"], []).status_code == 403


def test_history_hides_clinical_note_from_receptionist(
    client, doctor_token, doctor2_token, receptionist_token, past_appt, procedures, patient
):
    visit = open_visit(client, doctor_token, past_appt.id).json()
    save(client, doctor_token, visit["id"], [{"procedure_id": procedures["09543"]["id"], "quantity": 1}], note="Citlivý nález")
    client.post(f"/api/v1/visits/{visit['id']}/close", headers=auth(doctor_token))

    reception = client.get(f"/api/v1/patients/{patient['id']}/history", headers=auth(receptionist_token)).json()
    assert reception["items"][0]["visit"]["clinical_note"] is None
    assert reception["items"][0]["visit"]["items"][0]["code"] == "09543"

    colleague = client.get(f"/api/v1/patients/{patient['id']}/history", headers=auth(doctor2_token)).json()
    assert colleague["items"][0]["visit"]["clinical_note"] == "Citlivý nález"


def test_patient_history_contains_procedures_and_points(
    client, doctor_token, receptionist_token, past_appt, procedures, patient, hruba_id
):
    visit = open_visit(client, doctor_token, past_appt.id).json()
    save(client, doctor_token, visit["id"], [{"procedure_id": procedures["09543"]["id"], "quantity": 2}])
    client.post(f"/api/v1/visits/{visit['id']}/close", headers=auth(doctor_token))
    book(client, receptionist_token, hruba_id, patient["id"], next_week_monday(), "09:00", "09:15")

    history = client.get(f"/api/v1/patients/{patient['id']}/history", headers=auth(receptionist_token)).json()
    assert len(history["items"]) == 2
    upcoming, past = history["items"]  # nejnovější první
    assert upcoming["visit"] is None and upcoming["appointment_status"] == "PLANNED"
    assert past["appointment_status"] == "COMPLETED"
    assert past["visit"]["items"][0]["code"] == "09543"
    assert past["visit"]["total_points"] == 2 * procedures["09543"]["points"]


def test_procedure_codebook_admin_only(client, admin_token, doctor_token):
    payload = {"code": "99999", "name": "Testovací výkon", "points": 10}
    assert client.post("/api/v1/procedures", json=payload, headers=auth(doctor_token)).status_code == 403
    assert client.post("/api/v1/procedures", json=payload, headers=auth(admin_token)).status_code == 201
    assert client.post("/api/v1/procedures", json=payload, headers=auth(admin_token)).status_code == 400
    found = client.get("/api/v1/procedures", params={"search": "testovací"}, headers=auth(doctor_token)).json()
    assert [p["code"] for p in found] == ["99999"]
