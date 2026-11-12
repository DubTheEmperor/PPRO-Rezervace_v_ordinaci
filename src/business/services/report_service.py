"""Měsíční výkaz pro pojišťovny (FP7) – načtení dat, oprávnění a validace vstupů."""
from typing import Optional
from sqlalchemy.orm import Session
from src.business import reports, scheduling
from src.business.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from src.business.insurance import VALID_INSURANCE_CODES
from src.config import settings
from src.infrastructure.models.doctor_model import DoctorModel
from src.infrastructure.models.user_model import UserModel, UserRole
from src.infrastructure.models.visit_model import VisitModel
from src.infrastructure.repositories.appointment_repository import AppointmentRepository
from src.infrastructure.repositories.doctor_repository import DoctorRepository
from src.infrastructure.repositories.visit_repository import VisitRepository


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.doctor_repo = DoctorRepository(db)
        self.visit_repo = VisitRepository(db)
        self.appointment_repo = AppointmentRepository(db)

    # --- Oprávnění ---------------------------------------------------------------------------

    @staticmethod
    def can_view(doctor: DoctorModel, user: UserModel) -> bool:
        """Recepce a administrátor vidí výkaz libovolného lékaře, lékař jen vlastní."""
        if user.role in (UserRole.ADMIN, UserRole.RECEPTIONIST):
            return True
        return user.role == UserRole.DOCTOR and doctor.user_id == user.id

    # --- Převod entit na doménová data výkazu --------------------------------------------------

    @staticmethod
    def _to_report_visit(visit: VisitModel) -> reports.ReportVisit:
        patient = visit.patient
        return reports.ReportVisit(
            visit_id=visit.id,
            start_at=visit.appointment.start_at,
            patient_id=patient.id,
            patient_first_name=patient.first_name,
            patient_last_name=patient.last_name,
            patient_birth_year=patient.birth_year,
            insurance_number=patient.insurance_number,
            insurance_code=patient.insurance_company_code,
            items=tuple(
                reports.ReportItem(
                    code=item.procedure.code,
                    name=item.procedure.name,
                    quantity=item.quantity,
                    points_per_unit=item.points_per_unit,
                )
                for item in sorted(visit.items, key=lambda i: (i.procedure.code, i.id))
            ),
        )

    # --- Výkaz -------------------------------------------------------------------------------

    @staticmethod
    def _normalize_insurance(code: Optional[str]) -> Optional[str]:
        code = (code or "").strip()
        if not code:
            return None
        if code not in VALID_INSURANCE_CODES:
            raise BusinessRuleError(f"Neznámý kód zdravotní pojišťovny '{code}'.")
        return code

    def get_monthly_report(
        self,
        doctor_id: int,
        month: str,
        user: UserModel,
        insurance_code: Optional[str] = None,
    ) -> reports.MonthlyReport:
        doctor = self.doctor_repo.get_by_id(doctor_id)
        if not doctor:
            raise NotFoundError(f"Lékař s ID {doctor_id} nebyl nalezen.")
        if not self.can_view(doctor, user):
            raise PermissionDeniedError("Lékař může zobrazit pouze vlastní výkaz.")

        year, month_number = reports.parse_month(month)
        insurance_code = self._normalize_insurance(insurance_code)
        now = scheduling.local_now()
        reports.ensure_not_future(year, month_number, now.date())
        period_start, period_end = reports.month_bounds(year, month_number)

        visits = self.visit_repo.list_closed_for_report(
            doctor.id, period_start, period_end, insurance_code=insurance_code
        )
        unfinished = self.appointment_repo.list_unfinished_in_period(
            doctor.id, period_start, period_end, now, insurance_code=insurance_code
        )

        return reports.build_monthly_report(
            practice=reports.PracticeInfo(
                name=settings.PRACTICE_NAME, address=settings.PRACTICE_ADDRESS, icz=settings.PRACTICE_ICZ
            ),
            doctor=reports.DoctorInfo(
                id=doctor.id,
                full_name=doctor.full_name,
                specialization=doctor.specialization,
                icp=doctor.icp,
                specialty_code=doctor.specialty_code,
            ),
            year=year,
            month=month_number,
            insurance_code=insurance_code,
            visits=[self._to_report_visit(v) for v in visits],
            unfinished=[
                reports.UnfinishedVisit(
                    appointment_id=a.id,
                    start_at=a.start_at,
                    patient_name=f"{a.patient.last_name} {a.patient.first_name}",
                    state=reports.UNFINISHED_DRAFT if a.visit is not None else reports.UNFINISHED_TO_RECORD,
                )
                for a in unfinished
            ],
            now=now,
            generated_by=user.full_name or user.username,
        )
