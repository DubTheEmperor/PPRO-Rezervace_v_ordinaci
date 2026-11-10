from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from src.business.domain import AppointmentStatus, VisitStatus
from src.presentation.schemas.doctor_schemas import DoctorSummary
from src.presentation.schemas.patient_schemas import PatientResponse


class ProcedureResponse(BaseModel):
    id: int
    code: str
    name: str
    points: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class VisitItemResponse(BaseModel):
    procedure_id: int
    code: str
    name: str
    quantity: int
    points_per_unit: int
    total_points: int


class VisitResponse(BaseModel):
    id: int
    appointment_id: int
    doctor_id: int
    patient_id: int
    status: VisitStatus
    clinical_note: Optional[str]
    items: List[VisitItemResponse]
    total_points: int
    closed_at: Optional[datetime]
    closed_by_name: Optional[str]
    updated_at: datetime


def visit_to_response(visit, include_clinical_note: bool = True) -> VisitResponse:
    return VisitResponse(
        id=visit.id,
        appointment_id=visit.appointment_id,
        doctor_id=visit.doctor_id,
        patient_id=visit.patient_id,
        status=visit.status,
        clinical_note=visit.clinical_note if include_clinical_note else None,
        items=[
            VisitItemResponse(
                procedure_id=item.procedure_id,
                code=item.procedure.code,
                name=item.procedure.name,
                quantity=item.quantity,
                points_per_unit=item.points_per_unit,
                total_points=item.total_points,
            )
            for item in visit.items
        ],
        total_points=visit.total_points,
        closed_at=visit.closed_at,
        closed_by_name=visit.closed_by.full_name if visit.closed_by else None,
        updated_at=visit.updated_at,
    )


class AgendaItem(BaseModel):
    appointment_id: int
    start_at: datetime
    end_at: datetime
    reason: str
    patient: PatientResponse
    state: str  # WAITING | TO_RECORD | DRAFT | CLOSED
    visit_id: Optional[int]


class QueueCounts(BaseModel):
    pending: int
    today: int
    draft: int
    closed: int
    all: int


class VisitQueueResponse(BaseModel):
    doctor: DoctorSummary
    now: datetime
    filter: str
    can_record: bool
    counts: QueueCounts
    has_more: bool
    items: List[AgendaItem]


class PendingCountResponse(BaseModel):
    pending: int


class PatientHistoryItem(BaseModel):
    appointment_id: int
    start_at: datetime
    end_at: datetime
    reason: str
    appointment_status: AppointmentStatus
    doctor: DoctorSummary
    visit: Optional[VisitResponse]


class PatientHistoryResponse(BaseModel):
    patient_id: int
    items: List[PatientHistoryItem]
