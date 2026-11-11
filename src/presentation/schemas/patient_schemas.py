from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from src.business import reliability as rel


class ReliabilityResponse(BaseModel):
    """Spolehlivost pacienta za posuvné okno (FP5) – podklad pro barevný ukazatel."""
    level: str = rel.LEVEL_GREEN
    score: int = 0
    cancelled: int = 0
    no_show: int = 0
    late: int = 0
    window_months: int = rel.WINDOW_MONTHS

    @classmethod
    def from_domain(cls, value: rel.Reliability) -> "ReliabilityResponse":
        return cls(
            level=value.level,
            score=value.score,
            cancelled=value.cancelled,
            no_show=value.no_show,
            late=value.late,
            window_months=value.window_months,
        )


class PatientResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    birth_year: int
    phone_number: str
    insurance_number: str
    insurance_company_code: str
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    upcoming_appointments_count: int = 0
    reliability: ReliabilityResponse = Field(default_factory=ReliabilityResponse)

    model_config = ConfigDict(from_attributes=True)


class PatientListResponse(BaseModel):
    items: List[PatientResponse]
    total: int
    skip: int
    limit: int
