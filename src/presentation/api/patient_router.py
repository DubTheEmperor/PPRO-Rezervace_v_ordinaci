from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.infrastructure.database import get_db
from src.infrastructure.models.user_model import UserModel, UserRole
from src.presentation.schemas.patient_schemas import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientListResponse,
)
from src.business.services.patient_service import PatientService
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
    current_user: UserModel = Depends(get_current_user),
):
    patient_service = PatientService(db)
    patients, total = patient_service.get_patients(
        skip=skip, limit=limit, search=search, is_active=is_active
    )
    return PatientListResponse(
        items=[PatientResponse.model_validate(p) for p in patients],
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
    current_user: UserModel = Depends(get_current_user),
):
    patient_service = PatientService(db)
    patient = patient_service.get_patient_by_id(patient_id)
    return PatientResponse.model_validate(patient)


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
    current_user: UserModel = Depends(
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
    current_user: UserModel = Depends(
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
    current_user: UserModel = Depends(get_current_user),
):
    patient_service = PatientService(db)
    if permanent:
        if current_user.role != UserRole.ADMIN:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Trvalé fyzické smazání pacienta může provést pouze administrátor."
            )
        patient_service.delete_patient_permanent(patient_id)
    else:
        patient_service.deactivate_patient(patient_id)
    return None
