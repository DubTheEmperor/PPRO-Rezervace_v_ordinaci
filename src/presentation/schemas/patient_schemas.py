from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


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

    model_config = ConfigDict(from_attributes=True)


class PatientListResponse(BaseModel):
    items: List[PatientResponse]
    total: int
    skip: int
    limit: int
