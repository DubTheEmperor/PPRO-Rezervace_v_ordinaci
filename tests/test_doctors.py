from datetime import timedelta
from tests.helpers import auth, next_week_monday, next_week_day, create_patient, book

NEW_HOURS = {
    "blocks": [
        {"weekday": 0, "start_time": "08:00", "end_time": "12:00"},
        {"weekday": 4, "start_time": "09:00", "end_time": "11:30"},
    ]
}


def test_list_doctors_with_default_office_hours(client, receptionist_token):
    response = client.get("/api/v1/doctors", headers=auth(receptionist_token))
    assert response.status_code == 200
    doctors = response.json()
    assert len(doctors) == 3
    hruba = next(d for d in doctors if d["full_name"] == "MUDr. Jana Hrubá")
    monday_blocks = [b for b in hruba["office_hours"] if b["weekday"] == 0]
    assert [(b["start_time"], b["end_time"]) for b in monday_blocks] == [
        ("08:00:00", "12:00:00"),
        ("13:00:00", "16:00:00"),
    ]


def test_doctor_can_change_own_office_hours(client, doctor2_token, doctors_by_username):
    maly = doctors_by_username["maly"]
    response = client.put(
        f"/api/v1/doctors/{maly['id']}/office-hours", json=NEW_HOURS, headers=auth(doctor2_token)
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["office_hours"]) == 2


def test_doctor_cannot_change_other_doctors_hours(client, doctor2_token, doctors_by_username):
    hruba = doctors_by_username["hruba"]
    response = client.put(
        f"/api/v1/doctors/{hruba['id']}/office-hours", json=NEW_HOURS, headers=auth(doctor2_token)
    )
    assert response.status_code == 403


def test_admin_can_change_any_hours(client, admin_token, doctors_by_username):
    hruba = doctors_by_username["hruba"]
    response = client.put(
        f"/api/v1/doctors/{hruba['id']}/office-hours", json=NEW_HOURS, headers=auth(admin_token)
    )
    assert response.status_code == 200


def test_receptionist_cannot_change_hours(client, receptionist_token, doctors_by_username):
    hruba = doctors_by_username["hruba"]
    response = client.put(
        f"/api/v1/doctors/{hruba['id']}/office-hours", json=NEW_HOURS, headers=auth(receptionist_token)
    )
    assert response.status_code == 403


def test_invalid_office_hours_rejected(client, admin_token, doctors_by_username):
    doctor_id = doctors_by_username["hruba"]["id"]
    overlapping = {"blocks": [
        {"weekday": 0, "start_time": "08:00", "end_time": "12:00"},
        {"weekday": 0, "start_time": "11:00", "end_time": "13:00"},
    ]}
    misaligned = {"blocks": [{"weekday": 0, "start_time": "08:10", "end_time": "12:00"}]}
    bad_weekday = {"blocks": [{"weekday": 7, "start_time": "08:00", "end_time": "12:00"}]}

    url = f"/api/v1/doctors/{doctor_id}/office-hours"
    assert client.put(url, json=overlapping, headers=auth(admin_token)).status_code == 400
    assert client.put(url, json=misaligned, headers=auth(admin_token)).status_code == 400
    assert client.put(url, json=bad_weekday, headers=auth(admin_token)).status_code == 422


def test_hours_change_conflicting_with_planned_appointment_rejected(
    client, admin_token, receptionist_token, doctors_by_username
):
    hruba = doctors_by_username["hruba"]
    patient = create_patient(client, receptionist_token)
    # Rezervace ve čtvrtek odpoledne (Hrubá ordinuje Čt 12–18)
    res = book(client, receptionist_token, hruba["id"], patient["id"], next_week_day(3), "14:00", "14:30")
    assert res.status_code == 201, res.text

    # Nové hodiny čtvrtek vůbec neobsahují
    response = client.put(
        f"/api/v1/doctors/{hruba['id']}/office-hours", json=NEW_HOURS, headers=auth(admin_token)
    )
    assert response.status_code == 409
    assert "1 naplánovaných" in response.json()["detail"]


def test_week_calendar_structure(client, receptionist_token, doctors_by_username):
    hruba = doctors_by_username["hruba"]
    patient = create_patient(client, receptionist_token)
    monday = next_week_monday()
    assert book(client, receptionist_token, hruba["id"], patient["id"], monday, "09:00", "09:45").status_code == 201

    response = client.get(
        f"/api/v1/doctors/{hruba['id']}/calendar",
        params={"week_start": monday.isoformat()},
        headers=auth(receptionist_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["days"]) == 7
    assert data["days"][0]["date"] == monday.isoformat()
    assert len(data["days"][0]["blocks"]) == 2
    assert data["days"][1]["blocks"] == []  # úterý Hrubá neordinuje
    assert len(data["appointments"]) == 1
    assert data["appointments"][0]["patient_name"] == "Testovací Pavel"

    # Následující týden je prázdný
    response = client.get(
        f"/api/v1/doctors/{hruba['id']}/calendar",
        params={"week_start": (monday + timedelta(days=7)).isoformat()},
        headers=auth(receptionist_token),
    )
    assert response.json()["appointments"] == []


def test_week_calendar_requires_monday(client, receptionist_token, doctors_by_username):
    tuesday = next_week_day(1)
    response = client.get(
        f"/api/v1/doctors/{doctors_by_username['hruba']['id']}/calendar",
        params={"week_start": tuesday.isoformat()},
        headers=auth(receptionist_token),
    )
    assert response.status_code == 400


def test_only_admin_can_create_doctor(client, admin_token, receptionist_token):
    payload = {"full_name": "MUDr. Nový Lékař"}
    assert client.post("/api/v1/doctors", json=payload, headers=auth(receptionist_token)).status_code == 403
    response = client.post("/api/v1/doctors", json=payload, headers=auth(admin_token))
    assert response.status_code == 201
    assert response.json()["office_hours"] == []
    # Specializace se neeviduje – lékaři ordinace mají stejné zaměření
    assert "specialization" not in response.json()
    # Bez zvolené barvy dostane první volnou barvu palety (demo lékaři mají první tři)
    assert response.json()["color"] == "#8A6D3B"


def test_doctor_color_must_be_from_palette(client, admin_token, doctors_by_username):
    """Barva lékaře je jen z palety – volná barva (např. Tailwind oranžová) se odmítne."""
    bad = client.post("/api/v1/doctors", json={"full_name": "MUDr. Barevný", "color": "#f59e0b"},
                      headers=auth(admin_token))
    assert bad.status_code == 422

    ok = client.post("/api/v1/doctors", json={"full_name": "MUDr. Barevný", "color": "#4f5b66"},
                     headers=auth(admin_token))
    assert ok.status_code == 201
    assert ok.json()["color"] == "#4F5B66"  # normalizace na velká písmena

    doctor_id = doctors_by_username["hruba"]["id"]
    assert client.put(f"/api/v1/doctors/{doctor_id}", json={"color": "#0284c7"},
                      headers=auth(admin_token)).status_code == 422
    changed = client.put(f"/api/v1/doctors/{doctor_id}", json={"color": "#7A4E8C"}, headers=auth(admin_token))
    assert changed.status_code == 200
    assert changed.json()["color"] == "#7A4E8C"


def test_demo_doctors_use_palette_colors(client, receptionist_token):
    from src.business.doctor_colors import PALETTE
    doctors = client.get("/api/v1/doctors", headers=auth(receptionist_token)).json()
    assert {d["full_name"]: d["color"] for d in doctors} == {
        "MUDr. Jana Hrubá": "#3E5C9A",
        "MUDr. Tomáš Malý": "#5F7F3B",
        "MUDr. Lucie Veselá": "#7A4E8C",
    }
    assert all(d["color"] in PALETTE for d in doctors)


def test_next_free_color():
    from src.business.doctor_colors import PALETTE, next_free_color
    assert next_free_color([]) == PALETTE[0]
    assert next_free_color([PALETTE[0], PALETTE[2]]) == PALETTE[1]
    assert next_free_color([c.lower() for c in PALETTE[:3]]) == PALETTE[3]
    # Všechny obsazené → cyklicky podle počtu lékařů
    assert next_free_color(PALETTE) == PALETTE[0]
    assert next_free_color(PALETTE + [PALETTE[0]]) == PALETTE[1]
