from datetime import datetime, timezone
from typing import List
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.business.exceptions import BusinessRuleError, ConflictError, NotFoundError, PermissionDeniedError
from src.business import scheduling
from src.business.services.doctor_service import blocks_by_weekday
from src.infrastructure.models.appointment_model import AppointmentModel, AppointmentStatus
from src.infrastructure.models.user_model import UserModel, UserRole
from src.infrastructure.repositories.appointment_repository import AppointmentRepository
from src.infrastructure.repositories.doctor_repository import DoctorRepository
from src.infrastructure.repositories.patient_repository import PatientRepository
from src.business.dto.appointment_dto import AppointmentCancel, AppointmentCreate


class AppointmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AppointmentRepository(db)
        self.doctor_repo = DoctorRepository(db)
        self.patient_repo = PatientRepository(db)

    def get_appointment(self, appointment_id: int) -> AppointmentModel:
        appointment = self.repo.get_by_id(appointment_id)
        if not appointment:
            raise NotFoundError(f"Rezervace s ID {appointment_id} nebyla nalezena.")
        return appointment

    def list_patient_appointments(self, patient_id: int, upcoming_only: bool = True) -> List[AppointmentModel]:
        if not self.patient_repo.get_by_id(patient_id):
            raise NotFoundError(f"Pacient s ID {patient_id} nebyl nalezen.")
        now = scheduling.local_now() if upcoming_only else None
        return self.repo.list_for_patient(patient_id, now=now)

    def create_appointment(self, data: AppointmentCreate, current_user: UserModel) -> AppointmentModel:
        """Založí rezervaci a vynutí obchodní pravidla (ordinační hodiny, zákaz překryvu)."""
        doctor = self.doctor_repo.get_by_id(data.doctor_id)
        if not doctor or not doctor.is_active:
            raise BusinessRuleError("Zvolený lékař neexistuje nebo není aktivní.")

        patient = self.patient_repo.get_by_id(data.patient_id)
        if not patient or not patient.is_active:
            raise BusinessRuleError("Zvolený pacient neexistuje nebo je archivován.")

        start, end = data.start_at, data.end_at
        if not (scheduling.is_aligned(start) and scheduling.is_aligned(end)):
            raise BusinessRuleError(
                f"Začátek i konec termínu musí ležet na hranici {scheduling.SLOT_MINUTES}minutového slotu."
            )
        if end <= start:
            raise BusinessRuleError("Konec termínu musí být po jeho začátku.")
        if start.date() != end.date():
            raise BusinessRuleError("Termín musí začínat i končit ve stejný den.")
        if scheduling.slot_count(start, end) > scheduling.MAX_SLOTS_PER_APPOINTMENT:
            max_minutes = scheduling.MAX_SLOTS_PER_APPOINTMENT * scheduling.SLOT_MINUTES
            raise BusinessRuleError(f"Termín může trvat nejvýše {max_minutes} minut.")
        if start < scheduling.local_now():
            raise BusinessRuleError("Nelze rezervovat termín v minulosti.")

        day_blocks = blocks_by_weekday(doctor)[start.weekday()]
        if not scheduling.fits_office_hours(day_blocks, start, end):
            raise BusinessRuleError(
                f"Termín {start:%d. %m. %Y %H:%M}–{end:%H:%M} je mimo ordinační hodiny lékaře "
                f"{doctor.full_name}."
            )

        slots = scheduling.slot_starts(start, end)
        if self.repo.find_taken_slots(doctor.id, slots):
            raise ConflictError("Zvolený termín se překrývá s jinou rezervací u tohoto lékaře.")

        appointment = AppointmentModel(
            doctor_id=doctor.id,
            patient_id=patient.id,
            start_at=start,
            end_at=end,
            reason=data.reason,
            status=AppointmentStatus.PLANNED,
            created_by_user_id=current_user.id,
        )
        try:
            return self.repo.create_with_slots(appointment, slots)
        except IntegrityError:
            # Souběžná rezervace stejného slotu – zachytila ji DB pojistka UNIQUE(doctor_id, slot_start)
            raise ConflictError("Termín byl mezitím obsazen jinou rezervací. Vyberte prosím jiný čas.")

    # --- Zrušení a nedostavení (FP5) ----------------------------------------------------------

    @staticmethod
    def can_cancel(user: UserModel) -> bool:
        """Termíny na základě telefonátu ruší recepce nebo administrátor."""
        return user.role in (UserRole.RECEPTIONIST, UserRole.ADMIN)

    @staticmethod
    def can_mark_no_show(appointment: AppointmentModel, user: UserModel) -> bool:
        """Nedostavení označí recepce, administrátor nebo lékař, jemuž termín patří."""
        if user.role in (UserRole.RECEPTIONIST, UserRole.ADMIN):
            return True
        return user.role == UserRole.DOCTOR and appointment.doctor.user_id == user.id

    def cancel_appointment(
        self, appointment_id: int, data: AppointmentCancel, current_user: UserModel
    ) -> AppointmentModel:
        """Zruší naplánovaný termín: slot se uvolní, rezervace zůstává v historii pacienta."""
        if not self.can_cancel(current_user):
            raise PermissionDeniedError("Rezervaci může zrušit pouze recepce nebo administrátor.")
        appointment = self.get_appointment(appointment_id)
        if appointment.status != AppointmentStatus.PLANNED:
            raise ConflictError("Rezervaci nelze zrušit – není ve stavu naplánovaná.")
        if appointment.start_at <= scheduling.local_now():
            raise BusinessRuleError(
                "Termín už začal nebo proběhl – zrušit jej nelze. Pokud pacient nepřišel, "
                "označte jej jako „Nedostavil se“."
            )
        appointment.status = (
            AppointmentStatus.CANCELLED_BY_PATIENT
            if data.cancelled_by == "PATIENT"
            else AppointmentStatus.CANCELLED_BY_OFFICE
        )
        appointment.cancelled_at = datetime.now(timezone.utc)
        appointment.cancelled_by_user_id = current_user.id
        appointment.cancellation_note = data.note
        return self.repo.save_releasing_slots(appointment)

    def mark_no_show(self, appointment_id: int, current_user: UserModel) -> AppointmentModel:
        """Označí proběhlý termín, na který pacient nepřišel (bez záznamu návštěvy)."""
        appointment = self.get_appointment(appointment_id)
        if not self.can_mark_no_show(appointment, current_user):
            raise PermissionDeniedError(
                "Nedostavení může označit recepce, administrátor nebo lékař, jemuž termín patří."
            )
        if appointment.status != AppointmentStatus.PLANNED:
            raise ConflictError("Termín nelze označit jako nedostavení – není ve stavu naplánovaná.")
        if appointment.start_at > scheduling.local_now():
            raise BusinessRuleError("Termín ještě nezačal – nedostavení lze označit až po jeho začátku.")
        if appointment.visit is not None:
            raise ConflictError("K termínu už existuje záznam návštěvy – pacient se dostavil.")
        appointment.status = AppointmentStatus.NO_SHOW
        appointment.cancelled_at = datetime.now(timezone.utc)
        appointment.cancelled_by_user_id = current_user.id
        return self.repo.save_releasing_slots(appointment)
