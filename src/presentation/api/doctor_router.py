from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.infrastructure.database import get_db
from src.infrastructure.models.user_model import UserModel, UserRole
from src.presentation.schemas.doctor_schemas import (
    DoctorCreate,
    DoctorUpdate,
    DoctorResponse,
    OfficeHoursUpdate,
    WeekCalendarResponse,
)
from src.business.services.doctor_service import DoctorService
from src.presentation.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/doctors", tags=["Lékaři a ordinační hodiny"])


@router.get(
    "",
    response_model=List[DoctorResponse],
    summary="Seznam lékařů",
    description="Vrátí lékaře ordinace včetně jejich týdenních ordinačních hodin.",
)
def list_doctors(
    is_active: Optional[bool] = Query(None, description="Filtrovat podle stavu aktivity"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    doctors = DoctorService(db).list_doctors(is_active=is_active)
    return [DoctorResponse.model_validate(d) for d in doctors]


@router.get("/{doctor_id}", response_model=DoctorResponse, summary="Detail lékaře")
def get_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    return DoctorResponse.model_validate(DoctorService(db).get_doctor(doctor_id))


@router.post(
    "",
    response_model=DoctorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Založení lékaře",
    description="Pouze pro uživatele s rolí ADMIN.",
)
def create_doctor(
    data: DoctorCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN)),
):
    return DoctorResponse.model_validate(DoctorService(db).create_doctor(data))


@router.put(
    "/{doctor_id}",
    response_model=DoctorResponse,
    summary="Úprava údajů lékaře",
    description="Pouze pro uživatele s rolí ADMIN.",
)
def update_doctor(
    doctor_id: int,
    data: DoctorUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN)),
):
    return DoctorResponse.model_validate(DoctorService(db).update_doctor(doctor_id, data))


@router.put(
    "/{doctor_id}/office-hours",
    response_model=DoctorResponse,
    summary="Nastavení týdenních ordinačních hodin",
    description=(
        "Nahradí celý týdenní rozvrh lékaře. Smí administrátor nebo lékař, kterému profil patří. "
        "Změna, která by vyřadila již naplánované rezervace, je odmítnuta (409)."
    ),
)
def replace_office_hours(
    doctor_id: int,
    data: OfficeHoursUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    doctor = DoctorService(db).replace_office_hours(doctor_id, data, current_user)
    return DoctorResponse.model_validate(doctor)


@router.get(
    "/{doctor_id}/calendar",
    response_model=WeekCalendarResponse,
    summary="Týdenní kalendář lékaře",
    description="Ordinační bloky a aktivní rezervace lékaře pro týden začínající zadaným pondělím.",
)
def get_week_calendar(
    doctor_id: int,
    week_start: date = Query(..., description="Pondělí zobrazovaného týdne (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    return DoctorService(db).get_week_calendar(doctor_id, week_start)
