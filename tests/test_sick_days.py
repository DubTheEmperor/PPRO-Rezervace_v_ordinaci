"""Otevřený bod 5 – nemoc lékaře, fronta K přeobjednání a přeobjednání ke kolegovi."""
from datetime import date, datetime, timedelta
import pytest
from src.business import scheduling, sick_days
from src.business.seed import seed_demo_sickness, seed_initial_patients
from src.infrastructure.models.appointment_model import AppointmentModel, AppointmentStatus
from src.infrastructure.models.doctor_sick_day_model import DoctorSickDayModel
from tests.helpers import auth, book, create_patient, dt, next_week_monday

MONDAY = next_week_monday()
TUESDAY = MONDAY + timedelta(days=1)
WEDNESDAY = MONDAY + timedelta(days=2)


@pytest.fixture
def fixed_now(monkeypatch):
    """„Teď“ = pondělí příštího týdne 7:00 (Hrubá ordinuje v pondělí od 8:00)."""
    now = datetime.combine(MONDAY, datetime.min.time()).replace(hour=7)
    monkeypatch.setattr(scheduling, "local_now", lambda: now)
    return now


@pytest.fixture
def hruba_id(doctors_by_username):
    return doctors_by_username["hruba"]["id"]


@pytest.fixture
def maly_id(doctors_by_username):
    return doctors_by_username["maly"]["id"]


@pytest.fixture
def patient(client, receptionist_token):
    return create_patient(client, receptionist_token)


def set_sick(client, token, doctor_id, date_from, date_to=None, sick=True):
    return client.put(
        f"/api/v1/doctors/{doctor_id}/sick-days",
        json={"date_from": date_from.isoformat(), "date_to": (date_to or date_from).isoformat(), "sick": sick},
        headers=auth(token),
    )


def status_of(client, token, appointment_id):
    response = client.get(f"/api/v1/appointments/{appointment_id}", headers=auth(token))
    assert response.status_code == 200
    return response.json()


def queue(client, token, **params):
    return client.get("/api/v1/appointments/reschedule-queue", params=params, headers=auth(token))


def booked(client, token, doctor_id, patient_id, day, start, end):
    response = book(client, token, doctor_id, patient_id, day, start, end)
    assert response.status_code == 201, response.text
    return response.json()


# --- Označení a odznačení nemoci -----------------------------------------------------------------

def test_doctor_marks_own_sickness_and_planned_go_to_queue(
    client, fixed_now, doctor_token, receptionist_token, hruba_id, patient
):
    monday = booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    wednesday = booked(client, receptionist_token, hruba_id, patient["id"], WEDNESDAY, "09:00", "09:15")

    response = set_sick(client, doctor_token, hruba_id, MONDAY)
    assert response.status_code == 200, response.text
    assert response.json()["moved_to_queue"] == 1
    assert response.json()["days_changed"] == 1

    assert status_of(client, receptionist_token, monday["id"])["status"] == "TO_RESCHEDULE"
    assert status_of(client, receptionist_token, wednesday["id"])["status"] == "PLANNED"


def test_sick_day_keeps_slots_and_blocks_booking(
    client, fixed_now, admin_token, receptionist_token, hruba_id, patient
):
    booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    assert set_sick(client, admin_token, hruba_id, MONDAY).status_code == 200

    response = book(client, receptionist_token, hruba_id, patient["id"], MONDAY, "10:00", "10:15")
    assert response.status_code == 400
    assert "nemocn" in response.json()["detail"]


def test_sick_day_has_no_free_slots_and_is_flagged_in_calendar(
    client, fixed_now, doctor_token, receptionist_token, hruba_id
):
    assert set_sick(client, doctor_token, hruba_id, MONDAY).status_code == 200

    calendar = client.get(
        f"/api/v1/doctors/{hruba_id}/calendar", params={"week_start": MONDAY.isoformat()},
        headers=auth(receptionist_token),
    ).json()
    monday = calendar["days"][0]
    assert monday["sick"] is True
    assert monday["free_intervals"] == []
    assert calendar["days"][2]["sick"] is False
    assert calendar["days"][2]["free_intervals"]

    nxt = client.get(f"/api/v1/doctors/{hruba_id}/next-free-slot", headers=auth(receptionist_token)).json()
    assert nxt["start_at"] == dt(WEDNESDAY, "08:00")


def test_sick_appointment_is_visible_in_calendar(
    client, fixed_now, doctor_token, receptionist_token, hruba_id, patient
):
    appointment = booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    set_sick(client, doctor_token, hruba_id, MONDAY)
    calendar = client.get(
        f"/api/v1/doctors/{hruba_id}/calendar", params={"week_start": MONDAY.isoformat()},
        headers=auth(receptionist_token),
    ).json()
    items = {a["id"]: a["status"] for a in calendar["appointments"]}
    assert items[appointment["id"]] == "TO_RESCHEDULE"


def test_unmarking_restores_appointments(
    client, fixed_now, doctor_token, receptionist_token, hruba_id, patient
):
    monday = booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    wednesday = booked(client, receptionist_token, hruba_id, patient["id"], WEDNESDAY, "09:00", "09:15")
    assert set_sick(client, doctor_token, hruba_id, MONDAY, WEDNESDAY).json()["moved_to_queue"] == 2

    response = set_sick(client, doctor_token, hruba_id, WEDNESDAY, sick=False)
    assert response.status_code == 200
    assert response.json()["restored"] == 1
    assert response.json()["days_changed"] == 1

    assert status_of(client, receptionist_token, wednesday["id"])["status"] == "PLANNED"
    assert status_of(client, receptionist_token, monday["id"])["status"] == "TO_RESCHEDULE"
    # Středa je znovu rezervovatelná
    assert book(client, receptionist_token, hruba_id, patient["id"], WEDNESDAY, "10:00", "10:15").status_code == 201


def test_already_started_appointment_is_not_moved(
    client, fixed_now, monkeypatch, doctor_token, receptionist_token, hruba_id, patient
):
    started = booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    later = booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "11:00", "11:15")
    monkeypatch.setattr(scheduling, "local_now", lambda: fixed_now.replace(hour=9))

    assert set_sick(client, doctor_token, hruba_id, MONDAY).json()["moved_to_queue"] == 1
    assert status_of(client, receptionist_token, started["id"])["status"] == "PLANNED"
    assert status_of(client, receptionist_token, later["id"])["status"] == "TO_RESCHEDULE"


def test_marking_twice_is_idempotent(client, fixed_now, doctor_token, hruba_id):
    assert set_sick(client, doctor_token, hruba_id, MONDAY, TUESDAY).json()["days_changed"] == 2
    again = set_sick(client, doctor_token, hruba_id, MONDAY, WEDNESDAY).json()
    assert again["days_changed"] == 1
    days = client.get(
        f"/api/v1/doctors/{hruba_id}/sick-days",
        params={"date_from": MONDAY.isoformat(), "date_to": (MONDAY + timedelta(days=6)).isoformat()},
        headers=auth(doctor_token),
    ).json()
    assert days["days"] == [MONDAY.isoformat(), TUESDAY.isoformat(), WEDNESDAY.isoformat()]
    assert days["next_period"] == {"date_from": MONDAY.isoformat(), "date_to": WEDNESDAY.isoformat()}
    assert days["can_edit"] is True


def test_sick_days_permissions(
    client, fixed_now, admin_token, receptionist_token, doctor_token, doctor2_token, hruba_id
):
    assert set_sick(client, receptionist_token, hruba_id, MONDAY).status_code == 403
    assert set_sick(client, doctor2_token, hruba_id, MONDAY).status_code == 403
    assert set_sick(client, admin_token, hruba_id, MONDAY).status_code == 200
    assert set_sick(client, doctor_token, hruba_id, MONDAY, sick=False).status_code == 200

    view = client.get(
        f"/api/v1/doctors/{hruba_id}/sick-days",
        params={"date_from": MONDAY.isoformat(), "date_to": MONDAY.isoformat()},
        headers=auth(receptionist_token),
    )
    assert view.status_code == 200
    assert view.json()["can_edit"] is False


def test_past_days_cannot_be_changed(client, fixed_now, doctor_token, hruba_id):
    response = set_sick(client, doctor_token, hruba_id, MONDAY - timedelta(days=1), MONDAY)
    assert response.status_code == 400
    assert "zpětně" in response.json()["detail"]


def test_invalid_range(client, fixed_now, doctor_token, hruba_id):
    assert set_sick(client, doctor_token, hruba_id, TUESDAY, MONDAY).status_code == 400
    too_long = set_sick(client, doctor_token, hruba_id, MONDAY, MONDAY + timedelta(days=sick_days.MAX_RANGE_DAYS))
    assert too_long.status_code == 400


def test_preview_counts_affected(client, fixed_now, doctor_token, receptionist_token, hruba_id, patient):
    other = create_patient(client, receptionist_token, insurance_number="8001011234", last_name="Druhý")
    booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "09:00", "09:15")
    booked(client, receptionist_token, hruba_id, other["id"], WEDNESDAY, "09:00", "09:15")

    response = client.get(
        f"/api/v1/doctors/{hruba_id}/sick-days/preview",
        params={"date_from": MONDAY.isoformat(), "date_to": WEDNESDAY.isoformat(), "sick": True},
        headers=auth(doctor_token),
    )
    assert response.status_code == 200
    assert response.json() | {} == {
        "doctor_id": hruba_id, "date_from": MONDAY.isoformat(), "date_to": WEDNESDAY.isoformat(),
        "sick": True, "days_changed": 3, "appointments": 3, "patients": 2,
    }
    # Náhled nic neuložil
    assert queue(client, receptionist_token).json()["total"] == 0


# --- Fronta K přeobjednání a přeobjednání --------------------------------------------------------

def test_queue_lists_items_with_phone_and_count(
    client, fixed_now, doctor_token, receptionist_token, hruba_id, patient
):
    appointment = booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    set_sick(client, doctor_token, hruba_id, MONDAY)

    body = queue(client, receptionist_token).json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == appointment["id"]
    assert item["patient"]["phone_number"] == patient["phone_number"]
    assert item["doctor"]["id"] == hruba_id
    count = client.get("/api/v1/appointments/reschedule-queue/count", headers=auth(receptionist_token))
    assert count.json() == {"count": 1}
    assert queue(client, receptionist_token, doctor_id=hruba_id + 1000).json()["total"] == 0


def test_queue_is_not_for_doctors(client, fixed_now, doctor_token):
    assert queue(client, doctor_token).status_code == 403
    assert client.get("/api/v1/appointments/reschedule-queue/count", headers=auth(doctor_token)).status_code == 403


def reschedule(client, token, appointment_id, doctor_id, day, start, end):
    return client.post(
        f"/api/v1/appointments/{appointment_id}/reschedule",
        json={"doctor_id": doctor_id, "start_at": dt(day, start), "end_at": dt(day, end)},
        headers=auth(token),
    )


def test_reschedule_to_colleague(
    client, fixed_now, doctor_token, receptionist_token, hruba_id, maly_id, patient
):
    old = booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    set_sick(client, doctor_token, hruba_id, MONDAY)

    response = reschedule(client, receptionist_token, old["id"], maly_id, TUESDAY, "08:00", "08:30")
    assert response.status_code == 201, response.text
    new = response.json()
    assert new["doctor_id"] == maly_id
    assert new["status"] == "PLANNED"
    assert new["reason"] == old["reason"]

    detail = status_of(client, receptionist_token, old["id"])
    assert detail["status"] == "RESCHEDULED"
    assert detail["rescheduled_to_id"] == new["id"]
    assert detail["rescheduled_to_term"]["doctor_name"] == "MUDr. Tomáš Malý"
    assert detail["cancelled_by_name"]
    assert queue(client, receptionist_token).json()["total"] == 0

    # Původní sloty jsou uvolněné – po zrušení nemoci jde čas znovu rezervovat
    set_sick(client, doctor_token, hruba_id, MONDAY, sick=False)
    assert book(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30").status_code == 201

    # Přeobjednání se do spolehlivosti nepočítá
    patient_detail = client.get(f"/api/v1/patients/{patient['id']}", headers=auth(receptionist_token)).json()
    assert patient_detail["reliability"]["score"] == 0


def test_reschedule_respects_booking_rules(
    client, fixed_now, doctor_token, receptionist_token, hruba_id, maly_id, patient
):
    other = create_patient(client, receptionist_token, insurance_number="8001011234", last_name="Druhý")
    booked(client, receptionist_token, maly_id, other["id"], TUESDAY, "08:00", "08:30")
    old = booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    set_sick(client, doctor_token, hruba_id, MONDAY)

    collision = reschedule(client, receptionist_token, old["id"], maly_id, TUESDAY, "08:15", "08:45")
    assert collision.status_code == 409
    outside = reschedule(client, receptionist_token, old["id"], maly_id, MONDAY, "08:00", "08:30")
    assert outside.status_code == 400
    sick_day = reschedule(client, receptionist_token, old["id"], hruba_id, MONDAY, "13:00", "13:30")
    assert sick_day.status_code == 400

    assert status_of(client, receptionist_token, old["id"])["status"] == "TO_RESCHEDULE"
    assert queue(client, receptionist_token).json()["total"] == 1


def test_reschedule_to_same_doctor_later(
    client, fixed_now, doctor_token, receptionist_token, hruba_id, patient
):
    old = booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    set_sick(client, doctor_token, hruba_id, MONDAY)
    response = reschedule(client, receptionist_token, old["id"], hruba_id, WEDNESDAY, "08:00", "08:30")
    assert response.status_code == 201
    assert response.json()["doctor_id"] == hruba_id


def test_reschedule_only_from_queue_and_by_office(
    client, fixed_now, doctor_token, receptionist_token, hruba_id, maly_id, patient
):
    planned = booked(client, receptionist_token, hruba_id, patient["id"], WEDNESDAY, "08:00", "08:30")
    assert reschedule(client, receptionist_token, planned["id"], maly_id, TUESDAY, "08:00", "08:30").status_code == 409

    old = booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    set_sick(client, doctor_token, hruba_id, MONDAY)
    assert reschedule(client, doctor_token, old["id"], maly_id, TUESDAY, "08:00", "08:30").status_code == 403


def test_cancel_from_queue_even_after_original_time(
    client, fixed_now, monkeypatch, doctor_token, receptionist_token, hruba_id, patient
):
    old = booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    set_sick(client, doctor_token, hruba_id, MONDAY)
    monkeypatch.setattr(scheduling, "local_now", lambda: fixed_now.replace(hour=12))

    response = client.post(
        f"/api/v1/appointments/{old['id']}/cancel", json={"cancelled_by": "OFFICE"}, headers=auth(receptionist_token)
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CANCELLED_BY_OFFICE"
    assert queue(client, receptionist_token).json()["total"] == 0


def test_no_show_and_visit_not_possible_while_waiting(
    client, fixed_now, monkeypatch, doctor_token, receptionist_token, hruba_id, patient
):
    old = booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    set_sick(client, doctor_token, hruba_id, MONDAY)
    monkeypatch.setattr(scheduling, "local_now", lambda: fixed_now.replace(hour=12))
    response = client.post(f"/api/v1/appointments/{old['id']}/no-show", headers=auth(receptionist_token))
    assert response.status_code == 409


def test_waiting_appointment_is_listed_as_upcoming_for_patient(
    client, fixed_now, doctor_token, receptionist_token, hruba_id, patient
):
    booked(client, receptionist_token, hruba_id, patient["id"], MONDAY, "08:00", "08:30")
    set_sick(client, doctor_token, hruba_id, MONDAY)
    body = client.get(f"/api/v1/patients/{patient['id']}/appointments", headers=auth(receptionist_token)).json()
    assert [i["status"] for i in body["items"]] == ["TO_RESCHEDULE"]


# --- Seed a čistá logika -------------------------------------------------------------------------

def test_demo_sickness_seed_is_idempotent(db_session):
    seed_initial_patients(db_session)
    seed_demo_sickness(db_session)
    days = db_session.query(DoctorSickDayModel).count()
    waiting = db_session.query(AppointmentModel).filter(
        AppointmentModel.status == AppointmentStatus.TO_RESCHEDULE
    ).count()
    assert days == 2
    assert waiting == 2

    seed_demo_sickness(db_session)
    assert db_session.query(DoctorSickDayModel).count() == days
    assert db_session.query(AppointmentModel).count() == waiting


def test_merge_periods():
    d = date(2026, 11, 16)
    days = [d, d + timedelta(days=1), d + timedelta(days=4), d + timedelta(days=2)]
    assert sick_days.merge_periods(days) == [(d, d + timedelta(days=2)), (d + timedelta(days=4), d + timedelta(days=4))]
    assert sick_days.merge_periods([]) == []


def test_validate_range():
    today = date(2026, 11, 13)
    assert sick_days.validate_range(today, today, today) == []
    assert sick_days.validate_range(today, today - timedelta(days=1), today)
    assert sick_days.validate_range(today - timedelta(days=1), today, today)
    assert sick_days.validate_range(today, today + timedelta(days=sick_days.MAX_RANGE_DAYS), today)
    assert sick_days.days_in_range(today, today + timedelta(days=2)) == [
        today, today + timedelta(days=1), today + timedelta(days=2)
    ]
