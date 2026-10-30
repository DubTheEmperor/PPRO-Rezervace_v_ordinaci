from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.infrastructure.models.patient_model import PatientModel
from src.infrastructure.repositories.patient_repository import PatientRepository
from src.presentation.schemas.patient_schemas import PatientCreate, PatientUpdate


class PatientService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PatientRepository(db)

    def get_patient_by_id(self, patient_id: int) -> PatientModel:
        patient = self.repo.get_by_id(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pacient s ID {patient_id} nebyl nalezen."
            )
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

    def create_patient(self, patient_data: PatientCreate) -> PatientModel:
        # Kontrola unikátnosti čísla pojištěnce
        existing = self.repo.get_by_insurance_number(patient_data.insurance_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Pacient s číslem pojištěnce '{patient_data.insurance_number}' již v evidenci existuje "
                    f"({existing.first_name} {existing.last_name}, ID: {existing.id})."
                ),
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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Číslo pojištěnce '{patient_data.insurance_number}' je již přiřazeno jinému pacientovi."
                )
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

    def delete_patient_permanent(self, patient_id: int) -> None:
        """Trvalé fyzické smazání pacienta (pouze administrátor pro čištění chybných záznamů)."""
        patient = self.get_patient_by_id(patient_id)
        self.repo.delete(patient)
