from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from src.business.domain import AppointmentStatus
from src.presentation.schemas.doctor_schemas import DoctorSummary
from src.presentation.schemas.patient_schemas import PatientResponse


class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    start_at: datetime
    end_at: datetime
    reason: str
    status: AppointmentStatus
    created_at: datetime
    cancelled_at: Optional[datetime] = None
    rescheduled_to_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class RescheduledToInfo(BaseModel):
    """Nový termín, na který byla rezervace přeobjednána."""
    id: int
    start_at: datetime
    end_at: datetime
    doctor_name: str


class AppointmentDetailResponse(AppointmentResponse):
    patient: PatientResponse
    doctor: DoctorSummary
    created_by_name: Optional[str] = None
    cancelled_by_name: Optional[str] = None
    has_visit: bool = False
    rescheduled_to_term: Optional[RescheduledToInfo] = None


class PatientAppointmentItem(BaseModel):
    id: int
    start_at: datetime
    end_at: datetime
    reason: str
    status: AppointmentStatus
    doctor: DoctorSummary

    model_config = ConfigDict(from_attributes=True)


class PatientAppointmentListResponse(BaseModel):
    items: List[PatientAppointmentItem]
    total: int


class RescheduleQueueItem(BaseModel):
    """Termín, který kvůli nemoci lékaře čeká na obvolání pacienta a přeobjednání."""
    id: int
    start_at: datetime
    end_at: datetime
    reason: str
    status: AppointmentStatus
    doctor: DoctorSummary
    patient: PatientResponse

    model_config = ConfigDict(from_attributes=True)


class RescheduleQueueResponse(BaseModel):
    items: List[RescheduleQueueItem]
    total: int


class RescheduleQueueCount(BaseModel):
    count: int
