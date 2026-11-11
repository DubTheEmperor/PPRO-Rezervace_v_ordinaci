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
    cancellation_note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AppointmentDetailResponse(AppointmentResponse):
    patient: PatientResponse
    doctor: DoctorSummary
    created_by_name: Optional[str] = None
    cancelled_by_name: Optional[str] = None
    has_visit: bool = False


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
