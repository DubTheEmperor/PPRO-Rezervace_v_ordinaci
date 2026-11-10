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


def last_week_monday() -> date:
    return next_week_monday() - timedelta(days=14)


def make_past_appointment(db_session, doctor_id: int, patient_id: int, start: str = "09:00", end: str = "09:30"):
    """Vloží proběhlou rezervaci (minulé pondělí) přímo přes repozitář.

    Servis rezervace v minulosti správně zakazuje, testy návštěv je ale potřebují.
    """
    from datetime import datetime
    from src.business.scheduling import slot_starts
    from src.infrastructure.models.appointment_model import AppointmentModel, AppointmentStatus
    from src.infrastructure.repositories.appointment_repository import AppointmentRepository

    day = last_week_monday()
    start_at = datetime.fromisoformat(f"{day}T{start}")
    end_at = datetime.fromisoformat(f"{day}T{end}")
    return AppointmentRepository(db_session).create_with_slots(
        AppointmentModel(
            doctor_id=doctor_id, patient_id=patient_id, start_at=start_at, end_at=end_at,
            reason="Proběhlá kontrola", status=AppointmentStatus.PLANNED,
        ),
        slot_starts(start_at, end_at),
    )
