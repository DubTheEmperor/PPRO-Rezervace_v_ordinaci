from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator
from src.business.scheduling import LOCAL_TZ
from src.infrastructure.models.appointment_model import AppointmentStatus
from src.presentation.schemas.doctor_schemas import DoctorSummary
from src.presentation.schemas.patient_schemas import PatientResponse


def _to_local_naive(v: datetime) -> datetime:
    """Časy s časovou zónou převede na naivní lokální čas ordinace."""
    if v.tzinfo is not None:
        v = v.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return v


class AppointmentCreate(BaseModel):
    doctor_id: int
    patient_id: int
    start_at: datetime = Field(..., description="Začátek termínu (lokální čas, zarovnáno na 15 min)")
    end_at: datetime = Field(..., description="Konec termínu (lokální čas, zarovnáno na 15 min)")
    reason: str = Field(..., min_length=3, max_length=1000, description="Povinný důvod návštěvy")

    @field_validator("start_at", "end_at")
    @classmethod
    def normalize_tz(cls, v: datetime) -> datetime:
        return _to_local_naive(v)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 3:
            raise ValueError("Důvod návštěvy je povinný (alespoň 3 znaky).")
        return stripped


class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    start_at: datetime
    end_at: datetime
    reason: str
    status: AppointmentStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppointmentDetailResponse(AppointmentResponse):
    patient: PatientResponse
    doctor: DoctorSummary
    created_by_name: Optional[str] = None


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
