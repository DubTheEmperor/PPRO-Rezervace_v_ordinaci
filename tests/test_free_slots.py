"""FP6 – týdenní přehled volných termínů a nejbližší volný termín (API)."""
from datetime import datetime, timedelta
import pytest
from src.business import scheduling
from src.infrastructure.models.doctor_model import DoctorModel
from tests.helpers import auth, book, create_patient, dt, next_week_monday


@pytest.fixture
def hruba_id(doctors_by_username):
    return doctors_by_username["hruba"]["id"]


@pytest.fixture
def patient(client, receptionist_token):
    return create_patient(client, receptionist_token)


@pytest.fixture
def fixed_now(monkeypatch):
    """„Teď“ = pondělí příštího týdne 7:00 – výsledky nezávisí na skutečném čase běhu testů."""
    now = datetime.combine(next_week_monday(), datetime.min.time()).replace(hour=7)
    monkeypatch.setattr(scheduling, "local_now", lambda: now)
    return now


def free_slots(client, token, doctor_id, week_start):
    return client.get(
        f"/api/v1/doctors/{doctor_id}/free-slots", params={"week_start": week_start.isoformat()},
        headers=auth(token),
    )


def next_free(client, token, doctor_id, minutes=15):
    return client.get(
        f"/api/v1/doctors/{doctor_id}/next-free-slot", params={"minutes": minutes}, headers=auth(token)
    )


def intervals_of(body, day):
    return [(i["start_at"], i["end_at"]) for d in body["days"] if d["date"] == day.isoformat() for i in d["intervals"]]


def test_free_slots_follow_office_hours(client, receptionist_token, hruba_id, fixed_now):
    monday = next_week_monday()
    response = free_slots(client, receptionist_token, hruba_id, monday)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["slot_minutes"] == 15 and len(body["days"]) == 7
    # Hrubá: Po 8–12 a 13–16 (přes pauzu se nespojuje), Út neordinuje
    assert intervals_of(body, monday) == [
        (dt(monday, "08:00"), dt(monday, "12:00")),
        (dt(monday, "13:00"), dt(monday, "16:00")),
    ]
    assert intervals_of(body, monday + timedelta(days=1)) == []


def test_booking_removes_and_cancellation_restores_free_slot(
    client, receptionist_token, hruba_id, patient, fixed_now
):
    monday = next_week_monday()
    appt = book(client, receptionist_token, hruba_id, patient["id"], monday, "09:00", "09:30").json()
    body = free_slots(client, receptionist_token, hruba_id, monday).json()
    assert intervals_of(body, monday)[:2] == [
        (dt(monday, "08:00"), dt(monday, "09:00")),
        (dt(monday, "09:30"), dt(monday, "12:00")),
    ]
    cancel = client.post(
        f"/api/v1/appointments/{appt['id']}/cancel", json={"cancelled_by": "PATIENT"}, headers=auth(receptionist_token)
    )
    assert cancel.status_code == 200
    body = free_slots(client, receptionist_token, hruba_id, monday).json()
    assert intervals_of(body, monday)[0] == (dt(monday, "08:00"), dt(monday, "12:00"))


def test_calendar_contains_same_free_intervals(client, receptionist_token, hruba_id, fixed_now):
    monday = next_week_monday()
    calendar = client.get(
        f"/api/v1/doctors/{hruba_id}/calendar", params={"week_start": monday.isoformat()},
        headers=auth(receptionist_token),
    ).json()
    free = free_slots(client, receptionist_token, hruba_id, monday).json()
    assert [d["free_intervals"] for d in calendar["days"]] == [d["intervals"] for d in free["days"]]


def test_free_slots_requires_monday(client, receptionist_token, hruba_id):
    response = free_slots(client, receptionist_token, hruba_id, next_week_monday() + timedelta(days=1))
    assert response.status_code == 400


def test_next_free_slot_skips_fully_booked_day(client, receptionist_token, hruba_id, patient, fixed_now):
    monday = next_week_monday()
    assert next_free(client, receptionist_token, hruba_id).json()["start_at"] == dt(monday, "08:00")
    assert book(client, receptionist_token, hruba_id, patient["id"], monday, "08:00", "12:00").status_code == 201
    assert book(client, receptionist_token, hruba_id, patient["id"], monday, "13:00", "16:00").status_code == 201
    # Pondělí plné, úterý neordinuje → středa 8:00
    body = next_free(client, receptionist_token, hruba_id).json()
    assert body["start_at"] == dt(monday + timedelta(days=2), "08:00")
    assert body["end_at"] == dt(monday + timedelta(days=2), "08:15")


def test_next_free_slot_with_duration_needs_contiguous_time(
    client, receptionist_token, hruba_id, patient, fixed_now
):
    monday = next_week_monday()
    # Volná zůstane jen mezera 8:15–8:30, pak obsazeno do 12:00
    book(client, receptionist_token, hruba_id, patient["id"], monday, "08:00", "08:15")
    book(client, receptionist_token, hruba_id, patient["id"], monday, "08:30", "12:00")
    assert next_free(client, receptionist_token, hruba_id, 15).json()["start_at"] == dt(monday, "08:15")
    assert next_free(client, receptionist_token, hruba_id, 30).json()["start_at"] == dt(monday, "13:00")


@pytest.mark.parametrize("minutes", [0, 20, 255])
def test_next_free_slot_invalid_duration(client, receptionist_token, hruba_id, minutes):
    assert next_free(client, receptionist_token, hruba_id, minutes).status_code == 400


def test_inactive_doctor_has_no_free_slots(client, receptionist_token, db_session, hruba_id, fixed_now):
    doctor = db_session.get(DoctorModel, hruba_id)
    doctor.is_active = False
    db_session.commit()
    body = free_slots(client, receptionist_token, hruba_id, next_week_monday()).json()
    assert all(d["intervals"] == [] for d in body["days"])
    assert next_free(client, receptionist_token, hruba_id).json()["start_at"] is None
