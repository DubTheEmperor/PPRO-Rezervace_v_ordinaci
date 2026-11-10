"""Unit testy byznys vrstvy bez HTTP – servisy vyhazují doménové výjimky."""
from datetime import datetime
import pytest
from src.business.dto import AppointmentCreate, OfficeHoursUpdate, PatientCreate
from src.business.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from src.business.services.appointment_service import AppointmentService
from src.business.services.auth_service import AuthService
from src.business.services.doctor_service import DoctorService
from src.business.services.patient_service import PatientService
from src.infrastructure.repositories.doctor_repository import DoctorRepository
from src.infrastructure.repositories.user_repository import UserRepository
from tests.helpers import next_week_monday, next_week_day


@pytest.fixture
def users(db_session):
    repo = UserRepository(db_session)
    return {name: repo.get_by_username(name) for name in ("admin", "vera", "hruba", "maly")}


@pytest.fixture
def hruba(db_session, users):
    return DoctorRepository(db_session).get_by_user_id(users["hruba"].id)


@pytest.fixture
def patient(db_session):
    return PatientService(db_session).create_patient(PatientCreate(
        first_name="Pavel", last_name="Servisní", birth_year=1990, phone_number="+420777000222",
        insurance_number="9003031234", insurance_company_code="111",
    ))


def booking(doctor_id, patient_id, day, start, end):
    return AppointmentCreate(
        doctor_id=doctor_id, patient_id=patient_id,
        start_at=datetime.fromisoformat(f"{day}T{start}"),
        end_at=datetime.fromisoformat(f"{day}T{end}"),
        reason="Test servisní vrstvy",
    )


def test_overlap_raises_conflict_error(db_session, users, hruba, patient):
    service = AppointmentService(db_session)
    monday = next_week_monday()
    service.create_appointment(booking(hruba.id, patient.id, monday, "09:00", "09:30"), users["vera"])
    with pytest.raises(ConflictError):
        service.create_appointment(booking(hruba.id, patient.id, monday, "09:15", "09:45"), users["vera"])


def test_outside_office_hours_raises_business_rule_error(db_session, users, hruba, patient):
    with pytest.raises(BusinessRuleError, match="mimo ordinační hodiny"):
        AppointmentService(db_session).create_appointment(
            booking(hruba.id, patient.id, next_week_day(1), "09:00", "09:15"), users["vera"]
        )


def test_unknown_patient_appointments_raise_not_found(db_session):
    with pytest.raises(NotFoundError):
        AppointmentService(db_session).list_patient_appointments(99999)


def test_other_doctors_hours_raise_permission_denied(db_session, users, hruba):
    with pytest.raises(PermissionDeniedError):
        DoctorService(db_session).replace_office_hours(hruba.id, OfficeHoursUpdate(blocks=[]), users["maly"])


def test_permanent_delete_requires_admin(db_session, users, patient):
    with pytest.raises(PermissionDeniedError):
        PatientService(db_session).delete_patient_permanent(patient.id, users["vera"])
    PatientService(db_session).delete_patient_permanent(patient.id, users["admin"])
    with pytest.raises(NotFoundError):
        PatientService(db_session).get_patient_by_id(patient.id)


def test_invalid_token_raises_authentication_error(db_session):
    with pytest.raises(AuthenticationError):
        AuthService(db_session).get_user_from_token("neplatny.token.xyz")


def test_valid_token_returns_user(db_session, users):
    service = AuthService(db_session)
    token = service.create_user_token(users["vera"])
    assert service.get_user_from_token(token).username == "vera"


def test_ensure_role(users):
    from src.business.domain import UserRole
    assert AuthService.ensure_role(users["vera"], [UserRole.RECEPTIONIST]) is users["vera"]
    with pytest.raises(PermissionDeniedError):
        AuthService.ensure_role(users["hruba"], [UserRole.RECEPTIONIST, UserRole.ADMIN])
