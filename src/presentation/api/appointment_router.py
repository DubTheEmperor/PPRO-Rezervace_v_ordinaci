from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.business.domain import get_db, User, UserRole
from src.business.dto import AppointmentCancel, AppointmentCreate, AppointmentReschedule
from src.presentation.schemas.appointment_schemas import (
    AppointmentResponse,
    AppointmentDetailResponse,
    RescheduledToInfo,
    RescheduleQueueCount,
    RescheduleQueueItem,
    RescheduleQueueResponse,
)
from src.presentation.schemas.patient_schemas import ReliabilityResponse
from src.business.services.appointment_service import AppointmentService
from src.business.services.patient_service import PatientService
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
    current_user: User = Depends(require_roles(UserRole.RECEPTIONIST, UserRole.ADMIN)),
):
    appointment = AppointmentService(db).create_appointment(data, current_user)
    return AppointmentResponse.model_validate(appointment)


@router.get(
    "/reschedule-queue",
    response_model=RescheduleQueueResponse,
    summary="Fronta K přeobjednání",
    description=(
        "Termíny, které kvůli nemoci lékaře čekají na obvolání pacienta (nejbližší první). "
        "Vidí recepce a administrátor."
    ),
)
def list_reschedule_queue(
    doctor_id: Optional[int] = Query(None, description="Jen termíny daného lékaře"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = AppointmentService(db).list_reschedule_queue(current_user, doctor_id)
    reliability = PatientService(db).get_reliability(list({a.patient_id for a in items}))
    result = []
    for a in items:
        item = RescheduleQueueItem.model_validate(a)
        item.patient.reliability = ReliabilityResponse.from_domain(reliability[a.patient_id])
        result.append(item)
    return RescheduleQueueResponse(items=result, total=len(result))


@router.get(
    "/reschedule-queue/count",
    response_model=RescheduleQueueCount,
    summary="Počet termínů K přeobjednání",
)
def count_reschedule_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return RescheduleQueueCount(count=AppointmentService(db).count_reschedule_queue(current_user))


@router.get(
    "/{appointment_id}",
    response_model=AppointmentDetailResponse,
    summary="Detail rezervace",
)
def get_appointment_detail(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = AppointmentService(db).get_appointment(appointment_id)
    response = AppointmentDetailResponse.model_validate(appointment, from_attributes=True)
    response.created_by_name = appointment.created_by.full_name if appointment.created_by else None
    response.cancelled_by_name = appointment.cancelled_by.full_name if appointment.cancelled_by else None
    response.has_visit = appointment.visit is not None
    if appointment.rescheduled_to is not None:
        new = appointment.rescheduled_to
        response.rescheduled_to_term = RescheduledToInfo(
            id=new.id, start_at=new.start_at, end_at=new.end_at, doctor_name=new.doctor.full_name
        )
    reliability = PatientService(db).get_reliability([appointment.patient_id])[appointment.patient_id]
    response.patient.reliability = ReliabilityResponse.from_domain(reliability)
    return response


@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentResponse,
    summary="Zrušení rezervace",
    description=(
        "Recepce nebo administrátor zruší naplánovaný termín, který ještě nezačal. Slot se uvolní "
        "pro novou rezervaci, záznam zůstává v historii pacienta. Zrušení pacientem se počítá "
        "do jeho spolehlivosti, zrušení ordinací ne."
    ),
)
def cancel_appointment(
    appointment_id: int,
    data: AppointmentCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = AppointmentService(db).cancel_appointment(appointment_id, data, current_user)
    return AppointmentResponse.model_validate(appointment)


@router.post(
    "/{appointment_id}/no-show",
    response_model=AppointmentResponse,
    summary="Označení nedostavení",
    description="Proběhlý naplánovaný termín bez záznamu návštěvy – pacient nepřišel.",
)
def mark_no_show(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = AppointmentService(db).mark_no_show(appointment_id, current_user)
    return AppointmentResponse.model_validate(appointment)


@router.post(
    "/{appointment_id}/reschedule",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Přeobjednání termínu (nemoc lékaře)",
    description=(
        "Recepce nebo administrátor přesune termín z fronty K přeobjednání na nový čas – i k jinému "
        "lékaři. Vznikne nová rezervace (stejný pacient a důvod, platí všechna pravidla rezervace), "
        "původní přejde do stavu RESCHEDULED s odkazem na novou a uvolní své sloty. Vrací novou rezervaci."
    ),
)
def reschedule_appointment(
    appointment_id: int,
    data: AppointmentReschedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = AppointmentService(db).reschedule_appointment(appointment_id, data, current_user)
    return AppointmentResponse.model_validate(appointment)
