"""Odpovědní modely měsíčního výkazu pro pojišťovny (FP7)."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class _FromAttributes(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ReportItemResponse(_FromAttributes):
    code: str
    name: str
    quantity: int
    points_per_unit: int
    total_points: int


class ReportVisitResponse(_FromAttributes):
    visit_id: int
    start_at: datetime
    patient_id: int
    patient_name: str
    patient_birth_year: int
    insurance_number: str
    insurance_code: str
    items: List[ReportItemResponse]
    item_count: int
    total_points: int


class InsuranceSectionResponse(_FromAttributes):
    code: str
    name: str
    short_name: str
    visits: List[ReportVisitResponse]
    visit_count: int
    patient_count: int
    item_count: int
    total_points: int


class ProcedureSummaryResponse(_FromAttributes):
    code: str
    name: str
    quantity: int
    total_points: int


class UnfinishedVisitResponse(_FromAttributes):
    appointment_id: int
    start_at: datetime
    patient_name: str
    state: str


class PracticeInfoResponse(_FromAttributes):
    name: str
    address: str
    icz: str


class ReportDoctorResponse(_FromAttributes):
    id: int
    full_name: str
    specialization: Optional[str]
    icp: Optional[str]
    specialty_code: Optional[str]


class MonthlyReportResponse(_FromAttributes):
    practice: PracticeInfoResponse
    doctor: ReportDoctorResponse
    year: int
    month: int
    month_key: str
    period_label: str
    period_start: datetime
    period_end: datetime
    period_complete: bool
    insurance_code: Optional[str]
    insurance_label: str
    generated_at: datetime
    generated_by: str
    sections: List[InsuranceSectionResponse]
    procedure_summary: List[ProcedureSummaryResponse]
    unfinished: List[UnfinishedVisitResponse]
    visit_count: int
    patient_count: int
    item_count: int
    total_points: int
