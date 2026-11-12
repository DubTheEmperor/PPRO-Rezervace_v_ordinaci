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
    icp: Optional[str] = None
    specialty_code: Optional[str] = None
    is_active: bool
    office_hours: List[OfficeHoursBlock]


class CalendarBlock(BaseModel):
    start_time: time
    end_time: time


class FreeInterval(BaseModel):
    start_at: datetime
    end_at: datetime


class AwayBlock(BaseModel):
    """Čas, kdy lékař pravidelně ordinuje na jiném pracovišti – nelze rezervovat."""
    start_time: time
    end_time: time
    location: str


class CalendarDay(BaseModel):
    date: date
    weekday: int
    blocks: List[CalendarBlock] = Field(..., description="Rezervovatelné bloky ordinačních hodin")
    free_intervals: List[FreeInterval] = Field(default_factory=list, description="Volné termíny dne (FP6)")
    away_blocks: List[AwayBlock] = Field(default_factory=list, description="Jiné pracoviště (nelze rezervovat)")


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
