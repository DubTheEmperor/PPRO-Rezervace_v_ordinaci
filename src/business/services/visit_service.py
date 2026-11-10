"""Záznam o uskutečněné návštěvě (FP4).

Životní cyklus: koncept (DRAFT) → uzavřeno (CLOSED). Uzavřená návštěva je neměnná
a návštěvu nelze nikdy smazat (auditovatelnost zdravotní historie).
"""
from datetime import datetime, time, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from src.business import scheduling
from src.business.dto.visit_dto import VisitUpdate
from src.business.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from src.infrastructure.models.appointment_model import AppointmentModel, AppointmentStatus
from src.infrastructure.models.doctor_model import DoctorModel
from src.infrastructure.models.user_model import UserModel, UserRole
from src.infrastructure.models.visit_model import VisitModel, VisitStatus
from src.infrastructure.repositories.appointment_repository import AppointmentRepository
from src.infrastructure.repositories.doctor_repository import DoctorRepository
from src.infrastructure.repositories.patient_repository import PatientRepository
from src.infrastructure.repositories.procedure_repository import ProcedureRepository
from src.infrastructure.repositories.visit_repository import VisitRepository

# Stavy položky pracovní fronty „Ordinace dnes“
AGENDA_WAITING = "WAITING"      # termín ještě nezačal
AGENDA_TO_RECORD = "TO_RECORD"  # termín začal, záznam zatím neexistuje
AGENDA_DRAFT = "DRAFT"          # rozpracovaný koncept
AGENDA_CLOSED = "CLOSED"        # uzavřená návštěva


class VisitService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = VisitRepository(db)
        self.appointment_repo = AppointmentRepository(db)
        self.doctor_repo = DoctorRepository(db)
        self.patient_repo = PatientRepository(db)
        self.procedure_repo = ProcedureRepository(db)

    # --- Oprávnění ---------------------------------------------------------------------------

    @staticmethod
    def can_record(doctor: DoctorModel, user: UserModel) -> bool:
        """Výkony zapisuje administrátor nebo lékař, kterému návštěva patří."""
        return user.role == UserRole.ADMIN or (
            user.role == UserRole.DOCTOR and doctor.user_id == user.id
        )

    def _ensure_can_record(self, doctor: DoctorModel, user: UserModel) -> None:
        if not self.can_record(doctor, user):
            raise PermissionDeniedError(
                "Výkony může zapisovat pouze lékař, kterému návštěva patří, nebo administrátor."
            )

    # --- Čtení -------------------------------------------------------------------------------

    def get_visit(self, visit_id: int) -> VisitModel:
        visit = self.repo.get_by_id(visit_id)
        if not visit:
            raise NotFoundError(f"Záznam návštěvy s ID {visit_id} nebyl nalezen.")
        return visit

    def _ensure_queue_access(self, doctor: DoctorModel, user: UserModel) -> None:
        """Frontu návštěv vidí admin (libovolného lékaře) a lékař (jen svou); recepce ne."""
        if user.role == UserRole.ADMIN:
            return
        if user.role == UserRole.DOCTOR and doctor.user_id == user.id:
            return
        raise PermissionDeniedError("Frontu návštěv vidí pouze daný lékař nebo administrátor.")

    @staticmethod
    def _today_bounds(now: datetime) -> tuple:
        day_start = datetime.combine(now.date(), time(0, 0))
        return day_start, day_start + timedelta(days=1)

    @staticmethod
    def _agenda_state(appointment: AppointmentModel, now: datetime) -> str:
        visit = appointment.visit
        if visit is not None and visit.status == VisitStatus.CLOSED:
            return AGENDA_CLOSED
        if visit is not None:
            return AGENDA_DRAFT
        if appointment.start_at > now:
            return AGENDA_WAITING
        return AGENDA_TO_RECORD

    def get_visit_queue(
        self,
        doctor_id: int,
        queue_filter: str,
        user: UserModel,
        before: Optional[datetime] = None,
        limit: int = 50,
    ) -> dict:
        """Fronta návštěv lékaře od nejnovější do minulosti, filtrovaná podle stavu zápisu."""
        if queue_filter not in AppointmentRepository.QUEUE_FILTERS:
            raise BusinessRuleError(f"Neznámý filtr fronty '{queue_filter}'.")
        doctor = self.doctor_repo.get_by_id(doctor_id)
        if not doctor:
            raise NotFoundError(f"Lékař s ID {doctor_id} nebyl nalezen.")
        self._ensure_queue_access(doctor, user)

        now = scheduling.local_now()
        day_start, day_end = self._today_bounds(now)
        appointments, has_more = self.appointment_repo.list_visit_queue(
            doctor.id, queue_filter, now, day_start, day_end, before=before, limit=limit
        )
        return {
            "doctor": doctor,
            "now": now,
            "filter": queue_filter,
            "can_record": self.can_record(doctor, user),
            "counts": self.appointment_repo.count_visit_queue(doctor.id, now, day_start, day_end),
            "has_more": has_more,
            "items": [
                {
                    "appointment_id": a.id,
                    "start_at": a.start_at,
                    "end_at": a.end_at,
                    "reason": a.reason,
                    "patient": a.patient,
                    "state": self._agenda_state(a, now),
                    "visit_id": a.visit.id if a.visit else None,
                }
                for a in appointments
            ],
        }

    def get_pending_count(self, user: UserModel) -> int:
        """Počet návštěv „K vyřízení“: lékař – vlastní, admin – všech lékařů."""
        now = scheduling.local_now()
        day_start, day_end = self._today_bounds(now)
        if user.role == UserRole.ADMIN:
            doctor_id = None
        elif user.role == UserRole.DOCTOR:
            doctor = self.doctor_repo.get_by_user_id(user.id)
            if doctor is None:
                return 0
            doctor_id = doctor.id
        else:
            raise PermissionDeniedError("Frontu návštěv vidí pouze lékaři a administrátor.")
        return self.appointment_repo.count_visit_queue(doctor_id, now, day_start, day_end)["pending"]

    @staticmethod
    def can_view_clinical_notes(user: UserModel) -> bool:
        """Klinické poznámky vidí lékaři a administrátor, recepce ne (nejmenší oprávnění)."""
        return user.role in (UserRole.DOCTOR, UserRole.ADMIN)

    def get_visit_for_user(self, visit_id: int, user: UserModel) -> VisitModel:
        """Detail záznamu návštěvy – lékaři (kontinuita péče) a administrátor; recepce ne."""
        if not self.can_view_clinical_notes(user):
            raise PermissionDeniedError("Záznam návštěvy mohou zobrazit pouze lékaři a administrátor.")
        return self.get_visit(visit_id)

    def get_patient_history(self, patient_id: int) -> List[AppointmentModel]:
        if not self.patient_repo.get_by_id(patient_id):
            raise NotFoundError(f"Pacient s ID {patient_id} nebyl nalezen.")
        return self.appointment_repo.list_history_for_patient(patient_id)

    # --- Zápis -------------------------------------------------------------------------------

    def open_visit(self, appointment_id: int, user: UserModel) -> VisitModel:
        """Založí koncept záznamu k proběhlé rezervaci, případně vrátí existující záznam."""
        appointment = self.appointment_repo.get_by_id(appointment_id)
        if not appointment:
            raise NotFoundError(f"Rezervace s ID {appointment_id} nebyla nalezena.")
        self._ensure_can_record(appointment.doctor, user)

        existing = self.repo.get_by_appointment_id(appointment.id)
        if existing:
            return existing

        if appointment.status != AppointmentStatus.PLANNED:
            raise BusinessRuleError("K této rezervaci nelze zapsat návštěvu (rezervace není aktivní).")
        # Kauzální integrita: výkony nelze zapisovat k návštěvě, která ještě neproběhla
        if appointment.start_at > scheduling.local_now():
            raise BusinessRuleError("Návštěva ještě neproběhla – výkony nelze zapisovat předem.")

        visit = VisitModel(
            appointment_id=appointment.id,
            doctor_id=appointment.doctor_id,
            patient_id=appointment.patient_id,
            status=VisitStatus.DRAFT,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        self.repo.create(visit)
        return self.get_visit(visit.id)

    def _get_editable(self, visit_id: int, user: UserModel) -> VisitModel:
        visit = self.get_visit(visit_id)
        self._ensure_can_record(visit.doctor, user)
        if visit.status == VisitStatus.CLOSED:
            raise ConflictError("Návštěva je uzavřená – záznam již nelze měnit.")
        return visit

    def update_draft(self, visit_id: int, data: VisitUpdate, user: UserModel) -> VisitModel:
        visit = self._get_editable(visit_id, user)

        procedure_ids = [item.procedure_id for item in data.items]
        if len(procedure_ids) != len(set(procedure_ids)):
            raise BusinessRuleError("Každý výkon uveďte jen jednou – opakování vyjádřete počtem.")

        procedures = {p.id: p for p in self.procedure_repo.get_by_ids(procedure_ids)}
        missing = [pid for pid in procedure_ids if pid not in procedures]
        if missing:
            raise BusinessRuleError(f"Výkon s ID {missing[0]} v číselníku neexistuje.")

        # Snapshot bodů: již zapsané položky si drží původní body, nové berou aktuální číselník
        existing_points = {item.procedure_id: item.points_per_unit for item in visit.items}
        rows = []
        for item in data.items:
            procedure = procedures[item.procedure_id]
            if item.procedure_id in existing_points:
                points = existing_points[item.procedure_id]
            elif not procedure.is_active:
                raise BusinessRuleError(f"Výkon {procedure.code} již není v číselníku aktivní.")
            else:
                points = procedure.points
            rows.append((procedure.id, item.quantity, points))

        self.repo.replace_items(visit, rows)
        note = (data.clinical_note or "").strip()
        visit.clinical_note = note or None
        visit.updated_by_user_id = user.id
        self.repo.save(visit)
        return self.get_visit(visit.id)

    def close_visit(self, visit_id: int, user: UserModel) -> VisitModel:
        visit = self._get_editable(visit_id, user)
        if not visit.items:
            raise BusinessRuleError("Návštěvu nelze uzavřít bez zapsaného výkonu.")
        visit.status = VisitStatus.CLOSED
        visit.closed_by_user_id = user.id
        visit.closed_at = datetime.now(timezone.utc)
        visit.updated_by_user_id = user.id
        visit.appointment.status = AppointmentStatus.COMPLETED
        self.repo.save(visit)
        return self.get_visit(visit.id)
