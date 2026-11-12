"""Blok ordinačních hodin „Jiné pracoviště“ – lékař v tu dobu ordinuje jinde, objednat nelze."""
from datetime import datetime
import pytest
from pydantic import ValidationError
from src.business import scheduling
from src.business.dto import OfficeHoursBlock
from tests.helpers import auth, book, create_patient, next_week_day, next_week_monday

AWAY_TUESDAY = {"weekday": 1, "start_time": "13:00", "end_time": "17:00",
                "kind": "ELSEWHERE", "location": "Poliklinika Jih"}


def hours_url(doctor_id):
    return f"/api/v1/doctors/{doctor_id}/office-hours"


def calendar(client, token, doctor_id, week_start):
    response = client.get(f"/api/v1/doctors/{doctor_id}/calendar",
                          params={"week_start": week_start.isoformat()}, headers=auth(token))
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def maly(doctors_by_username):
    return doctors_by_username["maly"]


@pytest.fixture
def patient(client, receptionist_token):
    return create_patient(client, receptionist_token)


# --- Seed a uložení ----------------------------------------------------------------------------

def test_seed_maly_works_elsewhere_on_tuesday_afternoon(maly):
    away = [b for b in maly["office_hours"] if b["kind"] == "ELSEWHERE"]
    assert away == [{"weekday": 1, "start_time": "13:00:00", "end_time": "17:00:00",
                     "kind": "ELSEWHERE", "location": "Poliklinika Jih"}]
    office = [b for b in maly["office_hours"] if b["kind"] == "OFFICE"]
    assert all(b["location"] is None for b in office)


def test_save_elsewhere_block(client, doctor2_token, maly):
    body = {"blocks": [
        {"weekday": 1, "start_time": "07:30", "end_time": "12:00"},
        {**AWAY_TUESDAY, "location": "  Nemocnice Sever  "},
    ]}
    response = client.put(hours_url(maly["id"]), json=body, headers=auth(doctor2_token))
    assert response.status_code == 200, response.text
    blocks = response.json()["office_hours"]
    assert [(b["kind"], b["location"]) for b in blocks] == [("OFFICE", None), ("ELSEWHERE", "Nemocnice Sever")]


def test_elsewhere_requires_location(client, admin_token, maly):
    for location in (None, "", "   "):
        body = {"blocks": [{**AWAY_TUESDAY, "location": location}]}
        response = client.put(hours_url(maly["id"]), json=body, headers=auth(admin_token))
        assert response.status_code == 422
        assert "kde lékař" in response.text


def test_elsewhere_cannot_overlap_office_block(client, admin_token, maly):
    body = {"blocks": [
        {"weekday": 1, "start_time": "07:30", "end_time": "14:00"},
        AWAY_TUESDAY,
    ]}
    assert client.put(hours_url(maly["id"]), json=body, headers=auth(admin_token)).status_code == 400


def test_switching_block_with_planned_appointment_to_elsewhere_rejected(
    client, admin_token, receptionist_token, maly, patient
):
    assert book(client, receptionist_token, maly["id"], patient["id"],
                next_week_day(1), "08:00", "08:30").status_code == 201
    body = {"blocks": [{"weekday": 1, "start_time": "07:30", "end_time": "12:00",
                        "kind": "ELSEWHERE", "location": "Poliklinika Jih"}]}
    response = client.put(hours_url(maly["id"]), json=body, headers=auth(admin_token))
    assert response.status_code == 409


# --- Kalendář, volno a rezervace ---------------------------------------------------------------

def test_calendar_shows_away_block_without_free_slots(client, receptionist_token, maly):
    tuesday = calendar(client, receptionist_token, maly["id"], next_week_monday())["days"][1]
    assert tuesday["away_blocks"] == [
        {"start_time": "13:00:00", "end_time": "17:00:00", "location": "Poliklinika Jih"}
    ]
    assert [(b["start_time"], b["end_time"]) for b in tuesday["blocks"]] == [("07:30:00", "12:00:00")]
    assert all(f["end_at"][11:16] <= "12:00" for f in tuesday["free_intervals"])


def test_booking_into_elsewhere_block_rejected(client, receptionist_token, maly, patient):
    response = book(client, receptionist_token, maly["id"], patient["id"], next_week_day(1), "14:00", "14:30")
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "jiném pracovišti" in detail and "Poliklinika Jih" in detail
    # Dopolední ordinace téhož dne zůstává rezervovatelná
    ok = book(client, receptionist_token, maly["id"], patient["id"], next_week_day(1), "11:30", "12:00")
    assert ok.status_code == 201, ok.text


def test_next_free_slot_skips_elsewhere(client, admin_token, receptionist_token, maly, monkeypatch):
    monday = next_week_monday()
    now = datetime.combine(monday, datetime.min.time()).replace(hour=7)
    monkeypatch.setattr(scheduling, "local_now", lambda: now)
    body = {"blocks": [
        {"weekday": 0, "start_time": "08:00", "end_time": "12:00", "kind": "ELSEWHERE", "location": "Poliklinika Jih"},
        {"weekday": 2, "start_time": "08:00", "end_time": "12:00"},
    ]}
    assert client.put(hours_url(maly["id"]), json=body, headers=auth(admin_token)).status_code == 200
    response = client.get(f"/api/v1/doctors/{maly['id']}/next-free-slot", headers=auth(receptionist_token))
    assert response.json()["start_at"] == f"{next_week_day(2).isoformat()}T08:00:00"


# --- DTO ---------------------------------------------------------------------------------------

def test_office_hours_block_dto():
    office = OfficeHoursBlock(weekday=0, start_time="08:00", end_time="12:00", location="ignorováno")
    assert office.kind == "OFFICE" and office.location is None
    away = OfficeHoursBlock(**AWAY_TUESDAY)
    assert away.location == "Poliklinika Jih"
    with pytest.raises(ValidationError):
        OfficeHoursBlock(weekday=1, start_time="13:00", end_time="17:00", kind="ELSEWHERE")
    with pytest.raises(ValidationError):
        OfficeHoursBlock(weekday=1, start_time="13:00", end_time="17:00", kind="JINDE", location="X")
    with pytest.raises(ValidationError):
        OfficeHoursBlock(**{**AWAY_TUESDAY, "location": "x" * 101})
