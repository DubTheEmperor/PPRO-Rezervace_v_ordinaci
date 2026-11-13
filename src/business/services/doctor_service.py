from datetime import date, datetime, time, timedelta
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session
from src.business.exceptions import BusinessRuleError, ConflictError, NotFoundError, PermissionDeniedError
from src.business import scheduling, sick_days
from src.infrastructure.models.appointment_model import AppointmentStatus
from src.infrastructure.models.doctor_model import DoctorModel
from src.infrastructure.models.user_model import UserModel, UserRole
from src.infrastructure.repositories.doctor_repository import DoctorRepository
from src.infrastructure.repositories.appointment_repository import AppointmentRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.business.dto.doctor_dto import (
    DoctorCreate,
    DoctorUpdate,
    OfficeHoursUpdate,
    SickDaysChange,
)


def blocks_by_weekday(doctor: DoctorModel) -> Dict[int, List[scheduling.TimeBlock]]:
    """Rezervovatelné bloky (lékař ordinuje v ordinaci) po dnech v týdnu.

    Bloky jiného pracoviště se sem nezahrnují – rezervace, volné termíny i kontrola
    ordinačních hodin s nimi proto automaticky nepočítají.
    """
    result: Dict[int, List[scheduling.TimeBlock]] = {d: [] for d in range(7)}
    for oh in doctor.office_hours:
        if oh.is_bookable:
            result[oh.weekday].append((oh.start_time, oh.end_time))
    return result


def away_blocks_by_weekday(doctor: DoctorModel) -> Dict[int, List[Tuple[time, time, str]]]:
    """Bloky, kdy lékař pravidelně ordinuje na jiném pracovišti: (začátek, konec, místo)."""
    result: Dict[int, List[Tuple[time, time, str]]] = {d: [] for d in range(7)}
    for oh in doctor.office_hours:
        if not oh.is_bookable:
            result[oh.weekday].append((oh.start_time, oh.end_time, oh.location or ""))
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

        blocks = [(b.weekday, b.start_time, b.end_time, b.kind, b.location) for b in data.blocks]
        # Bloky se nesmí překrývat bez ohledu na typ (ordinace × jiné pracoviště)
        errors = scheduling.validate_blocks([b[:3] for b in blocks])
        if errors:
            raise BusinessRuleError(" ".join(errors))

        # Změna hodin nesmí „osiřet“ již naplánované budoucí rezervace – rezervovat
        # lze jen do bloků v ordinaci, takže se porovnává pouze s nimi
        new_by_day: Dict[int, List[scheduling.TimeBlock]] = {d: [] for d in range(7)}
        for weekday, start, end, kind, _location in blocks:
            if kind == "OFFICE":
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
        # V den nemoci lékař neordinuje – žádné volno
        sick = self.repo.list_sick_days(doctor.id, days[0], days[-1])
        return {
            day: [] if day in sick else scheduling.free_intervals(day, by_day[day.weekday()], taken, now)
            for day in days
        }

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
        away_by_day = away_blocks_by_weekday(doctor)
        now = scheduling.local_now()
        free = self._free_intervals_by_day(doctor, week_start, 7, now)
        sick = self.repo.list_sick_days(doctor.id, week_start, week_start + timedelta(days=6))

        days = []
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            days.append({
                "date": day,
                "weekday": offset,
                "sick": day in sick,
                "blocks": [{"start_time": s, "end_time": e} for s, e in sorted(by_day[offset])],
                "free_intervals": [{"start_at": s, "end_at": e} for s, e in free[day]],
                "away_blocks": [
                    {"start_time": s, "end_time": e, "location": loc}
                    for s, e, loc in sorted(away_by_day[offset])
                ],
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

    # --- Nemoc lékaře (otevřený bod 5) ------------------------------------------------------

    def get_sick_days(self, doctor_id: int, date_from: date, date_to: date) -> dict:
        """Nemocné dny v období a nejbližší aktuální či budoucí období nemoci (pro kartu lékaře)."""
        if date_to < date_from:
            raise BusinessRuleError("Konec období nesmí být před jeho začátkem.")
        if (date_to - date_from).days > 366:
            raise BusinessRuleError("Najednou lze načíst nejvýše jeden rok.")
        doctor = self.get_doctor(doctor_id)
        today = scheduling.local_now().date()
        days = self.repo.list_sick_days(doctor.id, date_from, date_to)
        upcoming = self.repo.list_sick_days(
            doctor.id, today, today + timedelta(days=sick_days.MAX_RANGE_DAYS)
        )
        periods = sick_days.merge_periods(upcoming)
        return {
            "doctor_id": doctor.id,
            "date_from": date_from,
            "date_to": date_to,
            "days": sorted(days),
            "next_period": {"date_from": periods[0][0], "date_to": periods[0][1]} if periods else None,
        }

    def _check_sick_change(self, data: SickDaysChange) -> List[date]:
        errors = sick_days.validate_range(data.date_from, data.date_to, scheduling.local_now().date())
        if errors:
            raise BusinessRuleError(" ".join(errors))
        return sick_days.days_in_range(data.date_from, data.date_to)

    def _affected_appointments(self, doctor: DoctorModel, data: SickDaysChange):
        """Rezervace, kterých se změna týká.

        Při označení naplánované termíny, které ještě nezačaly; při odznačení termíny,
        které čekají na přeobjednání.
        """
        range_from = datetime.combine(data.date_from, time(0, 0))
        range_to = datetime.combine(data.date_to + timedelta(days=1), time(0, 0))
        if data.sick:
            now = scheduling.local_now()
            planned = self.appointment_repo.list_for_doctor_days(
                doctor.id, range_from, range_to, (AppointmentStatus.PLANNED,)
            )
            return [a for a in planned if a.start_at > now]
        return self.appointment_repo.list_for_doctor_days(
            doctor.id, range_from, range_to, (AppointmentStatus.TO_RESCHEDULE,)
        )

    def _changed_days(self, doctor: DoctorModel, data: SickDaysChange) -> List[date]:
        days = self._check_sick_change(data)
        current = self.repo.list_sick_days(doctor.id, data.date_from, data.date_to)
        return [d for d in days if (d in current) != data.sick]

    def preview_sick_change(self, doctor_id: int, data: SickDaysChange) -> dict:
        """Náhled dopadu změny nemoci pro potvrzovací dialog (nic neukládá)."""
        doctor = self.get_doctor(doctor_id)
        changed = self._changed_days(doctor, data)
        affected = self._affected_appointments(doctor, data)
        return {
            "doctor_id": doctor.id,
            "date_from": data.date_from,
            "date_to": data.date_to,
            "sick": data.sick,
            "days_changed": len(changed),
            "appointments": len(affected),
            "patients": len({a.patient_id for a in affected}),
        }

    def set_sick_days(self, doctor_id: int, data: SickDaysChange, current_user: UserModel) -> dict:
        """Označí / odznačí dny nemoci lékaře a podle toho přesune dotčené rezervace.

        Označení: naplánované a ještě nezačaté termíny přejdou do stavu K přeobjednání
        (sloty zůstávají obsazené, na původní čas se nikdo jiný neobjedná). Odznačení:
        termíny čekající na přeobjednání se vrátí do stavu Naplánováno. Vše v jedné transakci.
        """
        doctor = self.get_doctor(doctor_id)
        if not self.can_manage_hours(doctor, current_user):
            raise PermissionDeniedError("Nemoc může zadat pouze administrátor nebo daný lékař.")
        changed = self._changed_days(doctor, data)
        affected = self._affected_appointments(doctor, data)

        if data.sick:
            self.repo.add_sick_days(doctor.id, changed, current_user.id)
        else:
            self.repo.remove_sick_days(doctor.id, changed)
        new_status = AppointmentStatus.TO_RESCHEDULE if data.sick else AppointmentStatus.PLANNED
        for appointment in affected:
            appointment.status = new_status
        self.repo.commit()

        return {
            "doctor_id": doctor.id,
            "date_from": data.date_from,
            "date_to": data.date_to,
            "sick": data.sick,
            "days_changed": len(changed),
            "moved_to_queue": len(affected) if data.sick else 0,
            "restored": 0 if data.sick else len(affected),
        }
