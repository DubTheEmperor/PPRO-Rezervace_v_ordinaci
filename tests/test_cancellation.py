"""FP5 – zrušení rezervace, nedostavení a ukazatel spolehlivosti pacienta."""
from datetime import timedelta, timezone
import pytest
from src.business.scheduling import LOCAL_TZ, local_now
from src.infrastructure.models.appointment_model import AppointmentModel, AppointmentStatus
from tests.helpers import auth, book, create_patient, make_past_appointment, next_week_monday


@pytest.fixture
def hruba_id(doctors_by_username):
    return doctors_by_username["hruba"]["id"]


@pytest.fixture
def patient(client, receptionist_token):
    return create_patient(client, receptionist_token)


@pytest.fixture
def patient2(client, receptionist_token):
    return create_patient(client, receptionist_token, insurance_number="8501011234", last_name="Druhý")


@pytest.fixture
def future_appt(client, receptionist_token, hruba_id, patient):
    response = book(client, receptionist_token, hruba_id, patient["id"], next_week_monday(), "09:00", "09:30")
    assert response.status_code == 201, response.text
    return response.json()


def cancel(client, token, appointment_id, cancelled_by="PATIENT", note=None):
    return client.post(
        f"/api/v1/appointments/{appointment_id}/cancel",
        json={"cancelled_by": cancelled_by, "note": note},
        headers=auth(token),
    )


def no_show(client, token, appointment_id):
    return client.post(f"/api/v1/appointments/{appointment_id}/no-show", headers=auth(token))


def reliability_of(client, token, patient_id):
    response = client.get(f"/api/v1/patients/{patient_id}", headers=auth(token))
    assert response.status_code == 200
    return response.json()["reliability"]


def insert_event(db_session, doctor_id, patient_id, status, days_ago, cancel_hours_before=None):
    """Historická událost (zrušení / nedostavení) vložená přímo do DB."""
    start = (local_now() - timedelta(days=days_ago)).replace(hour=9, minute=0, second=0)
    cancelled_at = None
    if cancel_hours_before is not None:
        cancelled_at = (start - timedelta(hours=cancel_hours_before)).replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc)
    db_session.add(AppointmentModel(
        doctor_id=doctor_id, patient_id=patient_id, start_at=start, end_at=start + timedelta(minutes=15),
        reason="Historický termín", status=status, cancelled_at=cancelled_at,
    ))
    db_session.commit()


# --- Zrušení -----------------------------------------------------------------------------------

def test_receptionist_cancels_and_slot_is_released(client, receptionist_token, hruba_id, patient, patient2, future_appt):
    response = cancel(client, receptionist_token, future_appt["id"], note="Pacient je nemocný")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "CANCELLED_BY_PATIENT"
    assert body["cancelled_at"] is not None
    assert body["cancellation_note"] == "Pacient je nemocný"

    # Uvolněný slot lze ihned znovu zarezervovat jiným pacientem
    rebook = book(client, receptionist_token, hruba_id, patient2["id"], next_week_monday(), "09:00", "09:30")
    assert rebook.status_code == 201, rebook.text

    # Zrušená rezervace zůstává v historii a v detailu je vidět, kdo ji zrušil
    detail = client.get(f"/api/v1/appointments/{future_appt['id']}", headers=auth(receptionist_token)).json()
    assert detail["status"] == "CANCELLED_BY_PATIENT"
    assert detail["cancelled_by_name"]
    upcoming = client.get(f"/api/v1/patients/{patient['id']}/appointments", headers=auth(receptionist_token)).json()
    assert upcoming["total"] == 0


def test_cancelled_appointment_not_in_calendar(client, receptionist_token, hruba_id, future_appt):
    cancel(client, receptionist_token, future_appt["id"])
    monday = next_week_monday()
    calendar = client.get(
        f"/api/v1/doctors/{hruba_id}/calendar", params={"week_start": monday.isoformat()},
        headers=auth(receptionist_token),
    )
    assert calendar.status_code == 200, calendar.text
    assert future_appt["id"] not in [a["id"] for a in calendar.json()["appointments"]]


def test_admin_can_cancel_by_office(client, admin_token, future_appt):
    response = cancel(client, admin_token, future_appt["id"], cancelled_by="OFFICE")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED_BY_OFFICE"


def test_doctor_cannot_cancel(client, doctor_token, future_appt):
    assert cancel(client, doctor_token, future_appt["id"]).status_code == 403


def test_cannot_cancel_twice(client, receptionist_token, future_appt):
    cancel(client, receptionist_token, future_appt["id"])
    assert cancel(client, receptionist_token, future_appt["id"]).status_code == 409


def test_cannot_cancel_past_appointment(client, receptionist_token, db_session, hruba_id, patient):
    past = make_past_appointment(db_session, hruba_id, patient["id"])
    response = cancel(client, receptionist_token, past.id)
    assert response.status_code == 400
    assert "Nedostavil se" in response.json()["detail"]


def test_cancel_unknown_appointment(client, receptionist_token):
    assert cancel(client, receptionist_token, 99999).status_code == 404


def test_invalid_cancelled_by_rejected(client, receptionist_token, future_appt):
    assert cancel(client, receptionist_token, future_appt["id"], cancelled_by="NOBODY").status_code == 422


# --- Nedostavení -------------------------------------------------------------------------------

def test_mark_no_show_for_past_appointment(client, receptionist_token, doctor_token, db_session, hruba_id, patient):
    past = make_past_appointment(db_session, hruba_id, patient["id"])
    response = no_show(client, receptionist_token, past.id)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "NO_SHOW"
    # Po nedostavení nelze k termínu zapsat návštěvu
    visit = client.post(f"/api/v1/appointments/{past.id}/visit", headers=auth(doctor_token))
    assert visit.status_code == 400


def test_owner_doctor_can_mark_no_show_other_doctor_cannot(
    client, doctor_token, doctor2_token, db_session, hruba_id, patient
):
    past = make_past_appointment(db_session, hruba_id, patient["id"])
    assert no_show(client, doctor2_token, past.id).status_code == 403
    assert no_show(client, doctor_token, past.id).status_code == 200


def test_cannot_mark_no_show_for_future(client, receptionist_token, future_appt):
    assert no_show(client, receptionist_token, future_appt["id"]).status_code == 400


def test_cannot_mark_no_show_with_visit(client, receptionist_token, doctor_token, db_session, hruba_id, patient):
    past = make_past_appointment(db_session, hruba_id, patient["id"])
    assert client.post(f"/api/v1/appointments/{past.id}/visit", headers=auth(doctor_token)).status_code in (200, 201)
    assert no_show(client, receptionist_token, past.id).status_code == 409


# --- Spolehlivost ------------------------------------------------------------------------------

def test_new_patient_is_green(client, receptionist_token, patient):
    rel = reliability_of(client, receptionist_token, patient["id"])
    assert rel == {"level": "GREEN", "score": 0, "cancelled": 0, "no_show": 0, "late": 0, "window_months": 12}


def test_reliability_counts_patient_cancellations_and_no_shows(
    client, receptionist_token, db_session, hruba_id, patient, future_appt
):
    cancel(client, receptionist_token, future_appt["id"])
    past = make_past_appointment(db_session, hruba_id, patient["id"])
    no_show(client, receptionist_token, past.id)
    rel = reliability_of(client, receptionist_token, patient["id"])
    assert (rel["cancelled"], rel["no_show"], rel["score"], rel["level"]) == (1, 1, 2, "YELLOW")


def test_office_cancellation_not_counted(client, receptionist_token, future_appt, patient):
    cancel(client, receptionist_token, future_appt["id"], cancelled_by="OFFICE")
    assert reliability_of(client, receptionist_token, patient["id"])["score"] == 0


def test_events_outside_window_not_counted(client, receptionist_token, db_session, hruba_id, patient):
    for days_ago in (30, 60, 90):
        insert_event(db_session, hruba_id, patient["id"], AppointmentStatus.NO_SHOW, days_ago)
    insert_event(db_session, hruba_id, patient["id"], AppointmentStatus.NO_SHOW, 400)  # mimo 12 měsíců
    insert_event(db_session, hruba_id, patient["id"], AppointmentStatus.CANCELLED_BY_PATIENT, 10,
                 cancel_hours_before=3)  # zrušeno 3 h předem = pozdě
    rel = reliability_of(client, receptionist_token, patient["id"])
    assert (rel["no_show"], rel["cancelled"], rel["late"], rel["level"]) == (3, 1, 1, "RED")


def test_reliability_in_patient_list_and_appointment_detail(
    client, receptionist_token, db_session, hruba_id, patient, future_appt
):
    insert_event(db_session, hruba_id, patient["id"], AppointmentStatus.NO_SHOW, 20)
    insert_event(db_session, hruba_id, patient["id"], AppointmentStatus.NO_SHOW, 40)
    listing = client.get("/api/v1/patients", params={"search": patient["last_name"]}, headers=auth(receptionist_token))
    item = next(p for p in listing.json()["items"] if p["id"] == patient["id"])
    assert item["reliability"]["level"] == "YELLOW"
    detail = client.get(f"/api/v1/appointments/{future_appt['id']}", headers=auth(receptionist_token)).json()
    assert detail["patient"]["reliability"]["no_show"] == 2
