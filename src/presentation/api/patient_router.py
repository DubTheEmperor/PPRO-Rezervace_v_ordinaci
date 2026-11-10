from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.business.domain import get_db, User, UserRole
from src.business.dto import PatientCreate, PatientUpdate
from src.presentation.schemas.patient_schemas import PatientResponse, PatientListResponse
from src.presentation.schemas.appointment_schemas import (
    PatientAppointmentItem,
    PatientAppointmentListResponse,
)
from src.business.services.patient_service import PatientService
from src.business.services.appointment_service import AppointmentService
from src.presentation.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/patients", tags=["Evidence pacientů"])


@router.get(
    "",
    response_model=PatientListResponse,
    summary="Seznam pacientů",
    description="Vrátí stránkovaný seznam pacientů s možností rychlého vyhledávání podle příjmení, jména, telefonu nebo rodného čísla.",
)
def list_patients(
    skip: int = Query(0, ge=0, description="Počet přeskočených záznamů"),
    limit: int = Query(50, ge=1, le=100, description="Maximální počet záznamů"),
    search: Optional[str] = Query(None, description="Hledat podle příjmení, jména, telefonu nebo čísla pojištěnce"),
    is_active: Optional[bool] = Query(None, description="Filtrovat podle stavu aktivity"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient_service = PatientService(db)
    patients, total = patient_service.get_patients(
        skip=skip, limit=limit, search=search, is_active=is_active
    )
    counts = patient_service.get_upcoming_appointment_counts([p.id for p in patients])
    items = []
    for p in patients:
        item = PatientResponse.model_validate(p)
        item.upcoming_appointments_count = counts.get(p.id, 0)
        items.append(item)
    return PatientListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Detail pacienta podle ID",
)
def get_patient_detail(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient_service = PatientService(db)
    patient = patient_service.get_patient_by_id(patient_id)
    return PatientResponse.model_validate(patient)


@router.get(
    "/{patient_id}/appointments",
    response_model=PatientAppointmentListResponse,
    summary="Rezervace pacienta",
    description="Vrátí rezervace pacienta; ve výchozím stavu pouze nadcházející aktivní termíny.",
)
def list_patient_appointments(
    patient_id: int,
    upcoming: bool = Query(True, description="Pouze nadcházející aktivní rezervace"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointments = AppointmentService(db).list_patient_appointments(patient_id, upcoming_only=upcoming)
    return PatientAppointmentListResponse(
        items=[PatientAppointmentItem.model_validate(a) for a in appointments],
        total=len(appointments),
    )


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Zaevidování nového pacienta",
    description="Přístupné pro recepční, lékaře i administrátory.",
)
def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.RECEPTIONIST, UserRole.DOCTOR, UserRole.ADMIN)
    ),
):
    patient_service = PatientService(db)
    new_patient = patient_service.create_patient(patient_data)
    return PatientResponse.model_validate(new_patient)


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Aktualizace údajů pacienta",
)
def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.RECEPTIONIST, UserRole.DOCTOR, UserRole.ADMIN)
    ),
):
    patient_service = PatientService(db)
    updated = patient_service.update_patient(patient_id, patient_data)
    return PatientResponse.model_validate(updated)


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deaktivace nebo smazání pacienta",
    description="Standardně provede měkkou deaktivaci (is_active=False) z důvodu zachování zdravotní historie. Trvalé smazání vyžaduje roli ADMIN.",
)
def delete_patient(
    patient_id: int,
    permanent: bool = Query(False, description="Při true provede trvalé smazání (pouze ADMIN)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient_service = PatientService(db)
    if permanent:
        patient_service.delete_patient_permanent(patient_id, current_user)
    else:
        patient_service.deactivate_patient(patient_id)
    return None
