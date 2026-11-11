"""Vstupní DTO pro rezervace termínů."""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator
from src.business.scheduling import LOCAL_TZ


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


class AppointmentCancel(BaseModel):
    cancelled_by: Literal["PATIENT", "OFFICE"] = Field(
        "PATIENT", description="Kdo termín ruší: pacient (počítá se do spolehlivosti) nebo ordinace"
    )
    note: Optional[str] = Field(None, max_length=300, description="Volitelná krátká poznámka ke zrušení")

    @field_validator("note")
    @classmethod
    def strip_note(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        return stripped or None
