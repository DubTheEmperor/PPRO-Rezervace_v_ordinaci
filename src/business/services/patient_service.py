from typing import Optional, List, Tuple, Dict
from sqlalchemy.orm import Session
from src.business.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from src.business import reliability
from src.business.scheduling import local_now
from src.infrastructure.models.appointment_model import AppointmentStatus
from src.infrastructure.models.patient_model import PatientModel
from src.infrastructure.models.user_model import UserModel, UserRole
from src.infrastructure.repositories.patient_repository import PatientRepository
from src.infrastructure.repositories.appointment_repository import AppointmentRepository
from src.business.dto.patient_dto import PatientCreate, PatientUpdate


class PatientService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PatientRepository(db)

    def get_patient_by_id(self, patient_id: int) -> PatientModel:
        patient = self.repo.get_by_id(patient_id)
        if not patient:
            raise NotFoundError(f"Pacient s ID {patient_id} nebyl nalezen.")
        return patient

    def get_patients(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[PatientModel], int]:
        return self.repo.get_all(
            skip=skip, limit=limit, search=search, is_active=is_active
        )

    def get_upcoming_appointment_counts(self, patient_ids: List[int]) -> Dict[int, int]:
        """Počet nadcházejících aktivních rezervací pro každého z pacientů (jeden dotaz)."""
        return AppointmentRepository(self.db).count_upcoming_by_patient_ids(
            patient_ids, local_now()
        )

    def get_reliability(self, patient_ids: List[int]) -> Dict[int, reliability.Reliability]:
        """Spolehlivost pacientů za posuvné okno (jeden dotaz; bez událostí = zelená)."""
        since = reliability.window_start(local_now())
        events = AppointmentRepository(self.db).list_reliability_events(
            patient_ids, since, (AppointmentStatus.CANCELLED_BY_PATIENT, AppointmentStatus.NO_SHOW)
        )
        grouped: Dict[int, list] = {pid: [] for pid in patient_ids}
        for patient_id, status, start_at, cancelled_at in events:
            grouped.setdefault(patient_id, []).append((status, start_at, cancelled_at))
        return {pid: reliability.evaluate(items) for pid, items in grouped.items()}

    def create_patient(self, patient_data: PatientCreate) -> PatientModel:
        # Kontrola unikátnosti čísla pojištěnce
        existing = self.repo.get_by_insurance_number(patient_data.insurance_number)
        if existing:
            raise BusinessRuleError(
                f"Pacient s číslem pojištěnce '{patient_data.insurance_number}' již v evidenci existuje "
                f"({existing.first_name} {existing.last_name}, ID: {existing.id})."
            )

        new_patient = PatientModel(
            first_name=patient_data.first_name.strip(),
            last_name=patient_data.last_name.strip(),
            birth_year=patient_data.birth_year,
            phone_number=patient_data.phone_number.strip(),
            insurance_number=patient_data.insurance_number.strip(),
            insurance_company_code=patient_data.insurance_company_code.strip(),
            notes=patient_data.notes.strip() if patient_data.notes else None,
            is_active=patient_data.is_active,
        )
        return self.repo.create(new_patient)

    def update_patient(self, patient_id: int, patient_data: PatientUpdate) -> PatientModel:
        patient = self.get_patient_by_id(patient_id)

        # Kontrola unikátnosti čísla pojištěnce při změně
        if patient_data.insurance_number and patient_data.insurance_number != patient.insurance_number:
            existing = self.repo.get_by_insurance_number(patient_data.insurance_number)
            if existing and existing.id != patient_id:
                raise BusinessRuleError(f"Číslo pojištěnce '{patient_data.insurance_number}' je již přiřazeno jinému pacientovi.")
            patient.insurance_number = patient_data.insurance_number

        if patient_data.first_name is not None:
            patient.first_name = patient_data.first_name.strip()

        if patient_data.last_name is not None:
            patient.last_name = patient_data.last_name.strip()

        if patient_data.birth_year is not None:
            patient.birth_year = patient_data.birth_year

        if patient_data.phone_number is not None:
            patient.phone_number = patient_data.phone_number.strip()

        if patient_data.insurance_company_code is not None:
            patient.insurance_company_code = patient_data.insurance_company_code.strip()

        if patient_data.notes is not None:
            patient.notes = patient_data.notes.strip() if patient_data.notes.strip() else None

        if patient_data.is_active is not None:
            patient.is_active = patient_data.is_active

        return self.repo.update(patient)

    def deactivate_patient(self, patient_id: int) -> PatientModel:
        """Měkké smazání (deaktivace) pacienta pro zachování auditovatelnosti a historie."""
        patient = self.get_patient_by_id(patient_id)
        patient.is_active = False
        return self.repo.update(patient)

    def delete_patient_permanent(self, patient_id: int, current_user: UserModel) -> None:
        """Trvalé fyzické smazání pacienta (pouze administrátor pro čištění chybných záznamů)."""
        if current_user.role != UserRole.ADMIN:
            raise PermissionDeniedError("Trvalé fyzické smazání pacienta může provést pouze administrátor.")
        patient = self.get_patient_by_id(patient_id)
        if AppointmentRepository(self.db).list_for_patient(patient_id):
            raise BusinessRuleError(
                "Pacienta s historií rezervací nelze trvale smazat (auditovatelnost). Použijte archivaci."
            )
        self.repo.delete(patient)
