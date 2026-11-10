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
