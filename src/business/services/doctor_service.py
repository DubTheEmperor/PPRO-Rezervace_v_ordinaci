from datetime import date, datetime, time, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from src.business.exceptions import BusinessRuleError, ConflictError, NotFoundError, PermissionDeniedError
from src.business import scheduling
from src.infrastructure.models.doctor_model import DoctorModel
from src.infrastructure.models.user_model import UserModel, UserRole
from src.infrastructure.repositories.doctor_repository import DoctorRepository
from src.infrastructure.repositories.appointment_repository import AppointmentRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.business.dto.doctor_dto import (
    DoctorCreate,
    DoctorUpdate,
    OfficeHoursUpdate,
)


def blocks_by_weekday(doctor: DoctorModel) -> Dict[int, List[scheduling.TimeBlock]]:
    result: Dict[int, List[scheduling.TimeBlock]] = {d: [] for d in range(7)}
    for oh in doctor.office_hours:
        result[oh.weekday].append((oh.start_time, oh.end_time))
    return result


class DoctorService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DoctorRepository(db)
        self.appointment_repo = AppointmentRepository(db)
        self.user_repo = UserRepository(db)

    # --- Čtení -----------------------------------------------------------------------------

    def get_doctor(self, doctor_id: int) -> DoctorModel:
        doctor = self.repo.get_by_id(doctor_id)
        if not doctor:
            raise NotFoundError(f"Lékař s ID {doctor_id} nebyl nalezen.")
        return doctor

    def list_doctors(self, is_active: Optional[bool] = None) -> List[DoctorModel]:
        return self.repo.get_all(is_active=is_active)

    # --- Správa lékařů (ADMIN) ------------------------------------------------------------

    def _validate_user_link(self, user_id: int, doctor_id: Optional[int] = None) -> None:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise BusinessRuleError(f"Uživatel s ID {user_id} neexistuje.")
        if user.role != UserRole.DOCTOR:
            raise BusinessRuleError("Propojit lze pouze uživatelský účet s rolí DOCTOR.")
        linked = self.repo.get_by_user_id(user_id)
        if linked and linked.id != doctor_id:
            raise BusinessRuleError(f"Uživatelský účet je již propojen s lékařem '{linked.full_name}'.")

    def create_doctor(self, data: DoctorCreate) -> DoctorModel:
        if data.user_id is not None:
            self._validate_user_link(data.user_id)
        doctor = DoctorModel(
            full_name=data.full_name.strip(),
            specialization=data.specialization.strip() if data.specialization else None,
            color=data.color,
            user_id=data.user_id,
            icp=data.icp,
            specialty_code=data.specialty_code,
            is_active=data.is_active,
        )
        return self.repo.create(doctor)

    def update_doctor(self, doctor_id: int, data: DoctorUpdate) -> DoctorModel:
        doctor = self.get_doctor(doctor_id)
        fields = data.model_fields_set
        if "user_id" in fields:
            if data.user_id is not None:
                self._validate_user_link(data.user_id, doctor_id=doctor.id)
            doctor.user_id = data.user_id
        if data.full_name is not None:
            doctor.full_name = data.full_name.strip()
        if "specialization" in fields:
            doctor.specialization = data.specialization.strip() if data.specialization else None
        if data.color is not None:
            doctor.color = data.color
        if "icp" in fields:
            doctor.icp = data.icp
        if "specialty_code" in fields:
            doctor.specialty_code = data.specialty_code
        if data.is_active is not None:
            doctor.is_active = data.is_active
        return self.repo.update(doctor)

    # --- Ordinační hodiny -----------------------------------------------------------------

    @staticmethod
    def can_manage_hours(doctor: DoctorModel, user: UserModel) -> bool:
        """Ordinační hodiny smí měnit administrátor nebo lékař, kterému profil patří."""
        return user.role == UserRole.ADMIN or (
            user.role == UserRole.DOCTOR and doctor.user_id == user.id
        )

    def replace_office_hours(
        self, doctor_id: int, data: OfficeHoursUpdate, current_user: UserModel
    ) -> DoctorModel:
        doctor = self.get_doctor(doctor_id)
        if not self.can_manage_hours(doctor, current_user):
            raise PermissionDeniedError("Ordinační hodiny může měnit pouze administrátor nebo daný lékař.")

        blocks = [(b.weekday, b.start_time, b.end_time) for b in data.blocks]
        errors = scheduling.validate_blocks(blocks)
        if errors:
            raise BusinessRuleError(" ".join(errors))

        # Změna hodin nesmí „osiřet“ již naplánované budoucí rezervace
        new_by_day: Dict[int, List[scheduling.TimeBlock]] = {d: [] for d in range(7)}
        for weekday, start, end in blocks:
            new_by_day[weekday].append((start, end))
        future = self.appointment_repo.list_future_for_doctor(doctor.id, scheduling.local_now())
        conflicts = [
            a for a in future
            if not scheduling.fits_office_hours(new_by_day[a.start_at.weekday()], a.start_at, a.end_at)
        ]
        if conflicts:
            first = min(conflicts, key=lambda a: a.start_at)
            raise ConflictError(
                f"Nové ordinační hodiny nepokrývají {len(conflicts)} naplánovaných rezervací "
                f"(nejbližší {first.start_at:%d. %m. %Y %H:%M}). Nejprve je přeobjednejte."
            )

        return self.repo.replace_office_hours(doctor, sorted(blocks))

    # --- Volné termíny (FP6) ----------------------------------------------------------------

    def _free_intervals_by_day(
        self, doctor: DoctorModel, first_day: date, day_count: int, now: datetime
    ) -> Dict[date, List[scheduling.Interval]]:
        """Volné intervaly pro souvislý úsek dní (obsazené sloty se načtou jedním dotazem)."""
        days = [first_day + timedelta(days=i) for i in range(day_count)]
        if not doctor.is_active:
            return {day: [] for day in days}
        by_day = blocks_by_weekday(doctor)
        range_from = datetime.combine(first_day, time(0, 0))
        taken = self.appointment_repo.list_taken_slot_starts(
            doctor.id, range_from, range_from + timedelta(days=day_count)
        )
        return {day: scheduling.free_intervals(day, by_day[day.weekday()], taken, now) for day in days}

    @staticmethod
    def _ensure_monday(week_start: date) -> None:
        if week_start.weekday() != 0:
            raise BusinessRuleError("Parametr week_start musí být pondělí.")

    def get_free_slots(self, doctor_id: int, week_start: date) -> dict:
        """Volné termíny lékaře ve zvoleném kalendářním týdnu."""
        self._ensure_monday(week_start)
        doctor = self.get_doctor(doctor_id)
        free = self._free_intervals_by_day(doctor, week_start, 7, scheduling.local_now())
        return {
            "doctor_id": doctor.id,
            "week_start": week_start,
            "slot_minutes": scheduling.SLOT_MINUTES,
            "days": [
                {"date": day, "intervals": [{"start_at": s, "end_at": e} for s, e in intervals]}
                for day, intervals in free.items()
            ],
        }

    def find_next_free_slot(self, doctor_id: int, minutes: int = scheduling.SLOT_MINUTES) -> dict:
        """Nejbližší volný termín dané délky od teď v horizontu NEXT_FREE_HORIZON_DAYS dní."""
        max_minutes = scheduling.MAX_SLOTS_PER_APPOINTMENT * scheduling.SLOT_MINUTES
        if minutes % scheduling.SLOT_MINUTES != 0 or not scheduling.SLOT_MINUTES <= minutes <= max_minutes:
            raise BusinessRuleError(
                f"Délka termínu musí být násobek {scheduling.SLOT_MINUTES} minut "
                f"v rozsahu {scheduling.SLOT_MINUTES}–{max_minutes} minut."
            )
        doctor = self.get_doctor(doctor_id)
        now = scheduling.local_now()
        free = self._free_intervals_by_day(doctor, now.date(), scheduling.NEXT_FREE_HORIZON_DAYS, now)
        found = None
        for intervals in free.values():
            found = scheduling.first_free_start(intervals, minutes)
            if found:
                break
        return {
            "doctor_id": doctor.id,
            "minutes": minutes,
            "start_at": found[0] if found else None,
            "end_at": found[1] if found else None,
            "horizon_days": scheduling.NEXT_FREE_HORIZON_DAYS,
        }

    # --- Týdenní kalendář -----------------------------------------------------------------

    def get_week_calendar(self, doctor_id: int, week_start: date) -> dict:
        self._ensure_monday(week_start)
        doctor = self.get_doctor(doctor_id)
        by_day = blocks_by_weekday(doctor)
        now = scheduling.local_now()
        free = self._free_intervals_by_day(doctor, week_start, 7, now)

        days = []
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            days.append({
                "date": day,
                "weekday": offset,
                "blocks": [{"start_time": s, "end_time": e} for s, e in sorted(by_day[offset])],
                "free_intervals": [{"start_at": s, "end_at": e} for s, e in free[day]],
            })

        range_from = datetime.combine(week_start, time(0, 0))
        range_to = range_from + timedelta(days=7)
        appointments = self.appointment_repo.list_for_doctor_range(doctor.id, range_from, range_to)

        return {
            "doctor": doctor,
            "week_start": week_start,
            "now": now,
            "days": days,
            "appointments": [
                {
                    "id": a.id,
                    "start_at": a.start_at,
                    "end_at": a.end_at,
                    "patient_id": a.patient_id,
                    "patient_name": f"{a.patient.last_name} {a.patient.first_name}",
                    "reason": a.reason,
                    "status": a.status,
                }
                for a in appointments
            ],
        }
