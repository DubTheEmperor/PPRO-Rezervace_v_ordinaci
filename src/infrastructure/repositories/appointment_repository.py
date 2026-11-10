from datetime import datetime
from typing import Optional, List, Dict, Iterable, Sequence
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from src.infrastructure.models.appointment_model import (
    AppointmentModel,
    AppointmentSlotModel,
    AppointmentStatus,
)

ACTIVE_STATUSES = (AppointmentStatus.PLANNED,)


class AppointmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, appointment_id: int) -> Optional[AppointmentModel]:
        return (
            self.db.query(AppointmentModel)
            .options(
                joinedload(AppointmentModel.patient),
                joinedload(AppointmentModel.doctor),
                joinedload(AppointmentModel.created_by),
            )
            .filter(AppointmentModel.id == appointment_id)
            .first()
        )

    def create_with_slots(
        self, appointment: AppointmentModel, slot_starts: Sequence[datetime]
    ) -> AppointmentModel:
        """Uloží rezervaci včetně obsazených slotů v jedné transakci.

        Při kolizi slotu vyhodí databáze IntegrityError (UNIQUE doctor_id + slot_start);
        transakce se odvolá a výjimka se propaguje do servisní vrstvy.
        """
        try:
            for slot_start in slot_starts:
                appointment.slots.append(
                    AppointmentSlotModel(doctor_id=appointment.doctor_id, slot_start=slot_start)
                )
            self.db.add(appointment)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(appointment)
        return appointment

    def find_taken_slots(
        self, doctor_id: int, slot_starts: Iterable[datetime]
    ) -> List[AppointmentSlotModel]:
        starts = list(slot_starts)
        if not starts:
            return []
        return (
            self.db.query(AppointmentSlotModel)
            .filter(
                AppointmentSlotModel.doctor_id == doctor_id,
                AppointmentSlotModel.slot_start.in_(starts),
            )
            .all()
        )

    def list_for_doctor_range(
        self,
        doctor_id: int,
        date_from: datetime,
        date_to: datetime,
        statuses: Sequence[AppointmentStatus] = ACTIVE_STATUSES,
    ) -> List[AppointmentModel]:
        return (
            self.db.query(AppointmentModel)
            .options(joinedload(AppointmentModel.patient))
            .filter(
                AppointmentModel.doctor_id == doctor_id,
                AppointmentModel.start_at < date_to,
                AppointmentModel.end_at > date_from,
                AppointmentModel.status.in_(statuses),
            )
            .order_by(AppointmentModel.start_at.asc())
            .all()
        )

    def list_future_for_doctor(self, doctor_id: int, now: datetime) -> List[AppointmentModel]:
        return (
            self.db.query(AppointmentModel)
            .filter(
                AppointmentModel.doctor_id == doctor_id,
                AppointmentModel.start_at >= now,
                AppointmentModel.status.in_(ACTIVE_STATUSES),
            )
            .all()
        )

    def list_for_patient(
        self, patient_id: int, now: Optional[datetime] = None
    ) -> List[AppointmentModel]:
        """Rezervace pacienta; při zadaném `now` jen nadcházející aktivní."""
        query = (
            self.db.query(AppointmentModel)
            .options(joinedload(AppointmentModel.doctor))
            .filter(AppointmentModel.patient_id == patient_id)
        )
        if now is not None:
            query = query.filter(
                AppointmentModel.end_at > now,
                AppointmentModel.status.in_(ACTIVE_STATUSES),
            )
        return query.order_by(AppointmentModel.start_at.asc()).all()

    def count_upcoming_by_patient_ids(
        self, patient_ids: Iterable[int], now: datetime
    ) -> Dict[int, int]:
        ids = list(patient_ids)
        if not ids:
            return {}
        rows = (
            self.db.query(AppointmentModel.patient_id, func.count(AppointmentModel.id))
            .filter(
                AppointmentModel.patient_id.in_(ids),
                AppointmentModel.end_at > now,
                AppointmentModel.status.in_(ACTIVE_STATUSES),
            )
            .group_by(AppointmentModel.patient_id)
            .all()
        )
        return {patient_id: count for patient_id, count in rows}
