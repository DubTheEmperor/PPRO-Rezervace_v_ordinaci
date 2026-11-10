from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from src.infrastructure.database import get_db
from src.infrastructure.models.user_model import UserModel, UserRole
from src.presentation.schemas.appointment_schemas import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentDetailResponse,
)
from src.business.services.appointment_service import AppointmentService
from src.presentation.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/appointments", tags=["Rezervace termínů"])


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Rezervace termínu u lékaře",
    description=(
        "Zakládá recepce nebo administrátor. Termín musí ležet v ordinačních hodinách lékaře, "
        "být zarovnaný na 15 min a nesmí se překrývat s jinou aktivní rezervací (409)."
    ),
)
def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.RECEPTIONIST, UserRole.ADMIN)),
):
    appointment = AppointmentService(db).create_appointment(data, current_user)
    return AppointmentResponse.model_validate(appointment)


@router.get(
    "/{appointment_id}",
    response_model=AppointmentDetailResponse,
    summary="Detail rezervace",
)
def get_appointment_detail(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    appointment = AppointmentService(db).get_appointment(appointment_id)
    response = AppointmentDetailResponse.model_validate(appointment, from_attributes=True)
    response.created_by_name = appointment.created_by.full_name if appointment.created_by else None
    return response
