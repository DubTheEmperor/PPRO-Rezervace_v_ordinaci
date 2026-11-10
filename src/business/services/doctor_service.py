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

    # --- Týdenní kalendář -----------------------------------------------------------------

    def get_week_calendar(self, doctor_id: int, week_start: date) -> dict:
        if week_start.weekday() != 0:
            raise BusinessRuleError("Parametr week_start musí být pondělí.")
        doctor = self.get_doctor(doctor_id)
        by_day = blocks_by_weekday(doctor)

        days = []
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            days.append({
                "date": day,
                "weekday": offset,
                "blocks": [{"start_time": s, "end_time": e} for s, e in sorted(by_day[offset])],
            })

        range_from = datetime.combine(week_start, time(0, 0))
        range_to = range_from + timedelta(days=7)
        appointments = self.appointment_repo.list_for_doctor_range(doctor.id, range_from, range_to)

        return {
            "doctor": doctor,
            "week_start": week_start,
            "now": scheduling.local_now(),
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
