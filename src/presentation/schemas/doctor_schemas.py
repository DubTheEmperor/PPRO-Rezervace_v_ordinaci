from datetime import date, datetime, time
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from src.business.domain import AppointmentStatus
from src.business.dto.doctor_dto import OfficeHoursBlock


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


class FreeInterval(BaseModel):
    start_at: datetime
    end_at: datetime


class CalendarDay(BaseModel):
    date: date
    weekday: int
    blocks: List[CalendarBlock]
    free_intervals: List[FreeInterval] = Field(default_factory=list, description="Volné termíny dne (FP6)")


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


class FreeSlotsDay(BaseModel):
    date: date
    intervals: List[FreeInterval]


class FreeSlotsResponse(BaseModel):
    """Volné termíny lékaře ve zvoleném týdnu (FP6) – souvislé volné úseky v 15min mřížce."""
    doctor_id: int
    week_start: date
    slot_minutes: int
    days: List[FreeSlotsDay]


class NextFreeSlotResponse(BaseModel):
    doctor_id: int
    minutes: int
    start_at: Optional[datetime] = Field(None, description="Začátek nejbližšího volného termínu, jinak null")
    end_at: Optional[datetime] = None
    horizon_days: int
