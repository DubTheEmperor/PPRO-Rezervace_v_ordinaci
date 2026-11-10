from datetime import date, datetime, time
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from src.infrastructure.models.appointment_model import AppointmentStatus

COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class OfficeHoursBlock(BaseModel):
    weekday: int = Field(..., ge=0, le=6, description="Den v týdnu (0 = pondělí … 6 = neděle)")
    start_time: time = Field(..., description="Začátek bloku (HH:MM, zarovnáno na 15 min)")
    end_time: time = Field(..., description="Konec bloku (HH:MM, zarovnáno na 15 min)")

    model_config = ConfigDict(from_attributes=True)


class OfficeHoursUpdate(BaseModel):
    blocks: List[OfficeHoursBlock] = Field(default_factory=list, description="Kompletní týdenní rozvrh")


class DoctorCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Celé jméno včetně titulu")
    specialization: Optional[str] = Field(None, max_length=100)
    color: str = Field("#0284c7", pattern=COLOR_PATTERN, description="Barva lékaře v kalendáři")
    user_id: Optional[int] = Field(None, description="Propojený uživatelský účet s rolí DOCTOR")
    is_active: bool = True


class DoctorUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    specialization: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, pattern=COLOR_PATTERN)
    user_id: Optional[int] = None
    is_active: Optional[bool] = None


class DoctorSummary(BaseModel):
    id: int
    full_name: str
    specialization: Optional[str]
    color: str

    model_config = ConfigDict(from_attributes=True)


class DoctorResponse(DoctorSummary):
    user_id: Optional[int]
    is_active: bool
    office_hours: List[OfficeHoursBlock]


class CalendarBlock(BaseModel):
    start_time: time
    end_time: time


class CalendarDay(BaseModel):
    date: date
    weekday: int
    blocks: List[CalendarBlock]


class CalendarAppointment(BaseModel):
    id: int
    start_at: datetime
    end_at: datetime
    patient_id: int
    patient_name: str
    reason: str
    status: AppointmentStatus


class WeekCalendarResponse(BaseModel):
    doctor: DoctorSummary
    week_start: date
    now: datetime = Field(..., description="Aktuální lokální čas ordinace (pro zešednutí minulosti)")
    days: List[CalendarDay]
    appointments: List[CalendarAppointment]
