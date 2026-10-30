from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.infrastructure.models.patient_model import PatientModel


class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, patient_id: int) -> Optional[PatientModel]:
        return self.db.query(PatientModel).filter(PatientModel.id == patient_id).first()

    def get_by_insurance_number(self, insurance_number: str) -> Optional[PatientModel]:
        return self.db.query(PatientModel).filter(
            PatientModel.insurance_number == insurance_number
        ).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[PatientModel], int]:
        query = self.db.query(PatientModel)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    PatientModel.last_name.ilike(search_pattern),
                    PatientModel.first_name.ilike(search_pattern),
                    PatientModel.phone_number.ilike(search_pattern),
                    PatientModel.insurance_number.ilike(search_pattern),
                )
            )

        if is_active is not None:
            query = query.filter(PatientModel.is_active == is_active)

        total = query.count()
        patients = (
            query.order_by(PatientModel.last_name.asc(), PatientModel.first_name.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return patients, total

    def find_potential_duplicates(
        self, first_name: str, last_name: str, birth_year: int
    ) -> List[PatientModel]:
        """Vyhledá pacienty se stejným jménem, příjmením a rokem narození pro kontrolu duplicit."""
        return (
            self.db.query(PatientModel)
            .filter(
                PatientModel.first_name.ilike(first_name.strip()),
                PatientModel.last_name.ilike(last_name.strip()),
                PatientModel.birth_year == birth_year,
            )
            .all()
        )

    def create(self, patient: PatientModel) -> PatientModel:
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def update(self, patient: PatientModel) -> PatientModel:
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def delete(self, patient: PatientModel) -> None:
        self.db.delete(patient)
        self.db.commit()
