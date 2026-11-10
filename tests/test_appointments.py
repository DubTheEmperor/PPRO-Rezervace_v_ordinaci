"""Testy kritických obchodních pravidel rezervací: zákaz překryvu a ordinační hodiny.

Výchozí hodiny MUDr. Hrubé: Po 8–12 a 13–16, St 8–12, Čt 12–18 (v úterý neordinuje).
"""
from datetime import datetime, timedelta
import pytest
from sqlalchemy.exc import IntegrityError
from src.infrastructure.models.appointment_model import AppointmentModel, AppointmentSlotModel
from tests.helpers import auth, next_week_monday, next_week_day, create_patient, book


@pytest.fixture
def hruba_id(doctors_by_username):
    return doctors_by_username["hruba"]["id"]


@pytest.fixture
def patient(client, receptionist_token):
    return create_patient(client, receptionist_token)


@pytest.fixture
def patient2(client, receptionist_token):
    return create_patient(client, receptionist_token, insurance_number="9102021234", last_name="Druhý")


def test_receptionist_creates_appointment(client, receptionist_token, hruba_id, patient):
    response = book(client, receptionist_token, hruba_id, patient["id"], next_week_monday(), "08:00", "08:45")
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "PLANNED"
    assert data["reason"] == "Preventivní prohlídka"


def test_admin_can_create_appointment(client, admin_token, hruba_id, patient):
    response = book(client, admin_token, hruba_id, patient["id"], next_week_monday(), "10:00", "10:15")
    assert response.status_code == 201


def test_doctor_cannot_create_appointment(client, doctor_token, hruba_id, patient):
    response = book(client, doctor_token, hruba_id, patient["id"], next_week_monday(), "08:00", "08:15")
    assert response.status_code == 403


# --- Zákaz překryvu ----------------------------------------------------------------------

def test_exact_collision_rejected(client, receptionist_token, hruba_id, patient, patient2):
    monday = next_week_monday()
    assert book(client, receptionist_token, hruba_id, patient["id"], monday, "09:00", "09:30").status_code == 201
    response = book(client, receptionist_token, hruba_id, patient2["id"], monday, "09:00", "09:30")
    assert response.status_code == 409


def test_partial_overlap_rejected(client, receptionist_token, hruba_id, patient, patient2):
    monday = next_week_monday()
    assert book(client, receptionist_token, hruba_id, patient["id"], monday, "09:00", "09:30").status_code == 201
    assert book(client, receptionist_token, hruba_id, patient2["id"], monday, "09:15", "09:45").status_code == 409
    assert book(client, receptionist_token, hruba_id, patient2["id"], monday, "08:45", "09:15").status_code == 409
    assert book(client, receptionist_token, hruba_id, patient2["id"], monday, "08:30", "10:00").status_code == 409


def test_adjacent_appointments_allowed(client, receptionist_token, hruba_id, patient, patient2):
    monday = next_week_monday()
    assert book(client, receptionist_token, hruba_id, patient["id"], monday, "09:00", "09:30").status_code == 201
    assert book(client, receptionist_token, hruba_id, patient2["id"], monday, "09:30", "09:45").status_code == 201
    assert book(client, receptionist_token, hruba_id, patient2["id"], monday, "08:45", "09:00").status_code == 201


def test_same_time_at_different_doctor_allowed(
    client, receptionist_token, doctors_by_username, patient, patient2
):
    hruba = doctors_by_username["hruba"]["id"]
    vesela = doctors_by_username["vesela"]["id"]
    monday = next_week_monday()  # Veselá Po 13–18, Hrubá Po 13–16
    assert book(client, receptionist_token, hruba, patient["id"], monday, "13:00", "13:30").status_code == 201
    assert book(client, receptionist_token, vesela, patient2["id"], monday, "13:00", "13:30").status_code == 201


def test_db_unique_slot_constraint_blocks_duplicate(db_session, doctors_by_username, client, receptionist_token):
    """DB pojistka: dva sloty téhož lékaře se stejným začátkem nelze uložit ani mimo servis."""
    hruba = doctors_by_username["hruba"]["id"]
    patient = create_patient(client, receptionist_token)
    start = datetime.combine(next_week_monday(), datetime.min.time()).replace(hour=10)

    def make_appointment():
        appt = AppointmentModel(
            doctor_id=hruba, patient_id=patient["id"], start_at=start,
            end_at=start + timedelta(minutes=15), reason="Test pojistky",
        )
        appt.slots.append(AppointmentSlotModel(doctor_id=hruba, slot_start=start))
        return appt

    db_session.add(make_appointment())
    db_session.commit()
    db_session.add(make_appointment())
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- Ordinační hodiny a validace -----------------------------------------------------------

def test_outside_office_hours_rejected(client, receptionist_token, hruba_id, patient):
    monday = next_week_monday()
    assert book(client, receptionist_token, hruba_id, patient["id"], monday, "07:45", "08:15").status_code == 400
    assert book(client, receptionist_token, hruba_id, patient["id"], monday, "16:00", "16:15").status_code == 400
    # Přes polední pauzu (12–13)
    assert book(client, receptionist_token, hruba_id, patient["id"], monday, "11:45", "12:15").status_code == 400


def test_non_working_day_rejected(client, receptionist_token, hruba_id, patient):
    response = book(client, receptionist_token, hruba_id, patient["id"], next_week_day(1), "09:00", "09:15")
    assert response.status_code == 400
    assert "mimo ordinační hodiny" in response.json()["detail"]


def test_misaligned_time_rejected(client, receptionist_token, hruba_id, patient):
    response = book(client, receptionist_token, hruba_id, patient["id"], next_week_monday(), "09:10", "09:25")
    assert response.status_code == 400


def test_past_appointment_rejected(client, receptionist_token, hruba_id, patient):
    # Pondělí před 2 týdny v 9:00 – Hrubá v pondělí ordinuje, ale termín je v minulosti
    past_monday = next_week_monday() - timedelta(days=14)
    response = book(client, receptionist_token, hruba_id, patient["id"], past_monday, "09:00", "09:15")
    assert response.status_code == 400
    assert "minulosti" in response.json()["detail"]


def test_missing_reason_rejected(client, receptionist_token, hruba_id, patient):
    response = book(
        client, receptionist_token, hruba_id, patient["id"], next_week_monday(), "09:00", "09:15", reason="   "
    )
    assert response.status_code == 422


def test_too_long_appointment_rejected(client, receptionist_token, doctors_by_username, patient):
    # Veselá Po 13–18 (5 h) – 4 h 15 min přesahuje limit 4 h
    vesela = doctors_by_username["vesela"]["id"]
    monday = next_week_monday()
    assert book(client, receptionist_token, vesela, patient["id"], monday, "13:00", "17:15").status_code == 400
    assert book(client, receptionist_token, vesela, patient["id"], monday, "13:00", "17:00").status_code == 201


def test_inactive_patient_rejected(client, receptionist_token, hruba_id, patient):
    client.delete(f"/api/v1/patients/{patient['id']}", headers=auth(receptionist_token))
    response = book(client, receptionist_token, hruba_id, patient["id"], next_week_monday(), "09:00", "09:15")
    assert response.status_code == 400


# --- Detail a přehled rezervací pacienta -----------------------------------------------------

def test_appointment_detail(client, receptionist_token, doctor_token, hruba_id, patient):
    created = book(client, receptionist_token, hruba_id, patient["id"], next_week_monday(), "10:00", "10:30").json()
    response = client.get(f"/api/v1/appointments/{created['id']}", headers=auth(doctor_token))
    assert response.status_code == 200
    data = response.json()
    assert data["patient"]["last_name"] == "Testovací"
    assert data["doctor"]["full_name"] == "MUDr. Jana Hrubá"
    assert data["created_by_name"] == "Věra Nováková (Recepce)"


def test_patient_upcoming_appointments(client, receptionist_token, hruba_id, patient):
    monday = next_week_monday()
    book(client, receptionist_token, hruba_id, patient["id"], monday, "08:00", "08:15")
    book(client, receptionist_token, hruba_id, patient["id"], next_week_day(2), "09:00", "09:30")

    response = client.get(f"/api/v1/patients/{patient['id']}/appointments", headers=auth(receptionist_token))
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["items"][0]["doctor"]["full_name"] == "MUDr. Jana Hrubá"

    listing = client.get("/api/v1/patients", headers=auth(receptionist_token)).json()
    item = next(p for p in listing["items"] if p["id"] == patient["id"])
    assert item["upcoming_appointments_count"] == 2
