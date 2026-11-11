from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.business.domain import get_db, User, UserRole
from src.business.dto import DoctorCreate, DoctorUpdate, OfficeHoursUpdate
from src.presentation.schemas.doctor_schemas import (
    DoctorResponse,
    FreeSlotsResponse,
    NextFreeSlotResponse,
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
    current_user: User = Depends(get_current_user),
):
    doctors = DoctorService(db).list_doctors(is_active=is_active)
    return [DoctorResponse.model_validate(d) for d in doctors]


@router.get("/{doctor_id}", response_model=DoctorResponse, summary="Detail lékaře")
def get_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
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
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    return DoctorService(db).get_week_calendar(doctor_id, week_start)


@router.get(
    "/{doctor_id}/free-slots",
    response_model=FreeSlotsResponse,
    summary="Volné termíny lékaře v týdnu",
    description=(
        "Souvislé volné úseky (15min mřížka) v ordinačních hodinách lékaře pro týden začínající "
        "zadaným pondělím. Obsazené sloty a minulost se vynechávají."
    ),
)
def get_free_slots(
    doctor_id: int,
    week_start: date = Query(..., description="Pondělí týdne (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return DoctorService(db).get_free_slots(doctor_id, week_start)


@router.get(
    "/{doctor_id}/next-free-slot",
    response_model=NextFreeSlotResponse,
    summary="Nejbližší volný termín lékaře",
    description="První volný termín zadané délky od teď (hledá se nejvýše 90 dní dopředu).",
)
def get_next_free_slot(
    doctor_id: int,
    minutes: int = Query(15, description="Požadovaná délka termínu v minutách (násobek 15)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return DoctorService(db).find_next_free_slot(doctor_id, minutes)
