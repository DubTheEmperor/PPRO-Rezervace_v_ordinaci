from datetime import date, timedelta
from src.business.scheduling import local_now


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def next_week_monday() -> date:
    """Pondělí příštího týdne – termíny v něm leží vždy v budoucnosti."""
    today = local_now().date()
    return today + timedelta(days=7 - today.weekday())


def next_week_day(weekday: int) -> date:
    return next_week_monday() + timedelta(days=weekday)


def dt(day: date, hhmm: str) -> str:
    return f"{day.isoformat()}T{hhmm}:00"


def create_patient(client, token, insurance_number="9001011234", last_name="Testovací", **extra) -> dict:
    payload = {
        "first_name": "Pavel",
        "last_name": last_name,
        "birth_year": 1990,
        "phone_number": "+420777000111",
        "insurance_number": insurance_number,
        "insurance_company_code": "111",
    }
    payload.update(extra)
    response = client.post("/api/v1/patients", json=payload, headers=auth(token))
    assert response.status_code == 201, response.text
    return response.json()


def book(client, token, doctor_id, patient_id, day, start, end, reason="Preventivní prohlídka"):
    return client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "start_at": dt(day, start),
            "end_at": dt(day, end),
            "reason": reason,
        },
        headers=auth(token),
    )
