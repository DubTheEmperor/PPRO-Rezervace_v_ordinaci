from datetime import time
from typing import Optional, List, Sequence, Tuple
from sqlalchemy.orm import Session, selectinload
from src.infrastructure.models.doctor_model import DoctorModel
from src.infrastructure.models.office_hours_model import OfficeHoursKind, OfficeHoursModel


class DoctorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, doctor_id: int) -> Optional[DoctorModel]:
        return (
            self.db.query(DoctorModel)
            .options(selectinload(DoctorModel.office_hours))
            .filter(DoctorModel.id == doctor_id)
            .first()
        )

    def get_by_user_id(self, user_id: int) -> Optional[DoctorModel]:
        return self.db.query(DoctorModel).filter(DoctorModel.user_id == user_id).first()

    def get_all(self, is_active: Optional[bool] = None) -> List[DoctorModel]:
        query = self.db.query(DoctorModel).options(selectinload(DoctorModel.office_hours))
        if is_active is not None:
            query = query.filter(DoctorModel.is_active == is_active)
        return query.order_by(DoctorModel.full_name.asc()).all()

    def create(self, doctor: DoctorModel) -> DoctorModel:
        self.db.add(doctor)
        self.db.commit()
        self.db.refresh(doctor)
        return doctor

    def update(self, doctor: DoctorModel) -> DoctorModel:
        self.db.commit()
        self.db.refresh(doctor)
        return doctor

    def replace_office_hours(
        self, doctor: DoctorModel, blocks: Sequence[Tuple]
    ) -> DoctorModel:
        """Nahradí všechny týdenní bloky lékaře v jedné transakci.

        Blok = (weekday, start, end) nebo (weekday, start, end, kind, location).
        """
        doctor.office_hours.clear()
        self.db.flush()
        for block in blocks:
            weekday, start, end = block[:3]
            kind = block[3] if len(block) > 3 else OfficeHoursKind.OFFICE.value
            location = block[4] if len(block) > 4 else None
            doctor.office_hours.append(OfficeHoursModel(
                weekday=weekday, start_time=start, end_time=end,
                kind=OfficeHoursKind(kind).value, location=location,
            ))
        self.db.commit()
        self.db.refresh(doctor)
        return doctor
