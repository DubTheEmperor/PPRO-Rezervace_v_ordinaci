from typing import List
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.business import scheduling
from src.business.services.doctor_service import blocks_by_weekday
from src.infrastructure.models.appointment_model import AppointmentModel, AppointmentStatus
from src.infrastructure.models.user_model import UserModel
from src.infrastructure.repositories.appointment_repository import AppointmentRepository
from src.infrastructure.repositories.doctor_repository import DoctorRepository
from src.infrastructure.repositories.patient_repository import PatientRepository
from src.presentation.schemas.appointment_schemas import AppointmentCreate


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class AppointmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AppointmentRepository(db)
        self.doctor_repo = DoctorRepository(db)
        self.patient_repo = PatientRepository(db)

    def get_appointment(self, appointment_id: int) -> AppointmentModel:
        appointment = self.repo.get_by_id(appointment_id)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rezervace s ID {appointment_id} nebyla nalezena.",
            )
        return appointment

    def list_patient_appointments(self, patient_id: int, upcoming_only: bool = True) -> List[AppointmentModel]:
        if not self.patient_repo.get_by_id(patient_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pacient s ID {patient_id} nebyl nalezen.",
            )
        now = scheduling.local_now() if upcoming_only else None
        return self.repo.list_for_patient(patient_id, now=now)

    def create_appointment(self, data: AppointmentCreate, current_user: UserModel) -> AppointmentModel:
        """Založí rezervaci a vynutí obchodní pravidla (ordinační hodiny, zákaz překryvu)."""
        doctor = self.doctor_repo.get_by_id(data.doctor_id)
        if not doctor or not doctor.is_active:
            raise _bad_request("Zvolený lékař neexistuje nebo není aktivní.")

        patient = self.patient_repo.get_by_id(data.patient_id)
        if not patient or not patient.is_active:
            raise _bad_request("Zvolený pacient neexistuje nebo je archivován.")

        start, end = data.start_at, data.end_at
        if not (scheduling.is_aligned(start) and scheduling.is_aligned(end)):
            raise _bad_request(
                f"Začátek i konec termínu musí ležet na hranici {scheduling.SLOT_MINUTES}minutového slotu."
            )
        if end <= start:
            raise _bad_request("Konec termínu musí být po jeho začátku.")
        if start.date() != end.date():
            raise _bad_request("Termín musí začínat i končit ve stejný den.")
        if scheduling.slot_count(start, end) > scheduling.MAX_SLOTS_PER_APPOINTMENT:
            max_minutes = scheduling.MAX_SLOTS_PER_APPOINTMENT * scheduling.SLOT_MINUTES
            raise _bad_request(f"Termín může trvat nejvýše {max_minutes} minut.")
        if start < scheduling.local_now():
            raise _bad_request("Nelze rezervovat termín v minulosti.")

        day_blocks = blocks_by_weekday(doctor)[start.weekday()]
        if not scheduling.fits_office_hours(day_blocks, start, end):
            raise _bad_request(
                f"Termín {start:%d. %m. %Y %H:%M}–{end:%H:%M} je mimo ordinační hodiny lékaře "
                f"{doctor.full_name}."
            )

        slots = scheduling.slot_starts(start, end)
        if self.repo.find_taken_slots(doctor.id, slots):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Zvolený termín se překrývá s jinou rezervací u tohoto lékaře.",
            )

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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Termín byl mezitím obsazen jinou rezervací. Vyberte prosím jiný čas.",
            )
