from datetime import datetime
from typing import Optional, List, Dict, Iterable, Sequence, Tuple
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, contains_eager, joinedload
from src.infrastructure.models.appointment_model import (
    AppointmentModel,
    AppointmentSlotModel,
    AppointmentStatus,
)
from src.infrastructure.models.visit_model import VisitModel, VisitProcedureModel, VisitStatus

ACTIVE_STATUSES = (AppointmentStatus.PLANNED,)
# Stavy, které v kalendáři obsazují termín (proběhlá návštěva slot neuvolňuje)
OCCUPYING_STATUSES = (AppointmentStatus.PLANNED, AppointmentStatus.COMPLETED)


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

    def save_releasing_slots(self, appointment: AppointmentModel) -> AppointmentModel:
        """Uloží změnu stavu a v téže transakci smaže obsazené sloty (termín se uvolní).

        Samotná rezervace zůstává v databázi (historie pacienta, statistika spolehlivosti).
        """
        try:
            appointment.slots.clear()
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(appointment)
        return appointment

    def list_reliability_events(
        self,
        patient_ids: Iterable[int],
        since: datetime,
        statuses: Sequence[AppointmentStatus],
    ) -> List[Tuple[int, AppointmentStatus, datetime, Optional[datetime]]]:
        """(patient_id, status, start_at, cancelled_at) rezervací v daných stavech od `since`."""
        ids = list(patient_ids)
        if not ids:
            return []
        rows = (
            self.db.query(
                AppointmentModel.patient_id,
                AppointmentModel.status,
                AppointmentModel.start_at,
                AppointmentModel.cancelled_at,
            )
            .filter(
                AppointmentModel.patient_id.in_(ids),
                AppointmentModel.status.in_(statuses),
                AppointmentModel.start_at >= since,
            )
            .all()
        )
        return [tuple(r) for r in rows]

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
        statuses: Sequence[AppointmentStatus] = OCCUPYING_STATUSES,
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

    # --- Fronta návštěv lékaře (FP4) ----------------------------------------------------------

    QUEUE_FILTERS = ("pending", "today", "draft", "closed", "all")

    @staticmethod
    def _queue_conditions(now: datetime, day_start: datetime, day_end: datetime) -> Dict[str, object]:
        """SQL podmínky jednotlivých filtrů fronty (nad outer joinem appointments ⟕ visits)."""
        to_record = and_(
            AppointmentModel.status == AppointmentStatus.PLANNED,
            AppointmentModel.start_at <= now,
            VisitModel.id.is_(None),
        )
        draft = VisitModel.status == VisitStatus.DRAFT
        return {
            "pending": or_(to_record, draft),
            "today": and_(AppointmentModel.start_at >= day_start, AppointmentModel.start_at < day_end),
            "draft": draft,
            "closed": VisitModel.status == VisitStatus.CLOSED,
            # Vše od dnešního dne do minulosti – budoucí dny řeší kalendář rezervací
            "all": AppointmentModel.start_at < day_end,
        }

    def _queue_base(self, doctor_id: Optional[int]):
        query = (
            self.db.query(AppointmentModel)
            .outerjoin(VisitModel, VisitModel.appointment_id == AppointmentModel.id)
            .filter(AppointmentModel.status.in_(OCCUPYING_STATUSES))
        )
        if doctor_id is not None:
            query = query.filter(AppointmentModel.doctor_id == doctor_id)
        return query

    def list_visit_queue(
        self,
        doctor_id: int,
        queue_filter: str,
        now: datetime,
        day_start: datetime,
        day_end: datetime,
        before: Optional[datetime] = None,
        limit: int = 50,
    ) -> Tuple[List[AppointmentModel], bool]:
        """Položky fronty od nejnovější do minulosti; vrací (položky, has_more)."""
        condition = self._queue_conditions(now, day_start, day_end)[queue_filter]
        query = (
            self._queue_base(doctor_id)
            .filter(condition)
            .options(joinedload(AppointmentModel.patient), contains_eager(AppointmentModel.visit))
        )
        if before is not None:
            query = query.filter(AppointmentModel.start_at < before)
        rows = query.order_by(AppointmentModel.start_at.desc()).limit(limit + 1).all()
        return rows[:limit], len(rows) > limit

    def count_visit_queue(
        self, doctor_id: Optional[int], now: datetime, day_start: datetime, day_end: datetime
    ) -> Dict[str, int]:
        """Počty položek pro všechny filtry jedním dotazem (doctor_id=None = všichni lékaři)."""
        conditions = self._queue_conditions(now, day_start, day_end)
        columns = [
            func.coalesce(func.sum(case((conditions[name], 1), else_=0)), 0).label(name)
            for name in self.QUEUE_FILTERS
        ]
        query = (
            self.db.query(*columns)
            .select_from(AppointmentModel)
            .outerjoin(VisitModel, VisitModel.appointment_id == AppointmentModel.id)
            .filter(AppointmentModel.status.in_(OCCUPYING_STATUSES))
        )
        if doctor_id is not None:
            query = query.filter(AppointmentModel.doctor_id == doctor_id)
        row = query.one()
        return {name: int(getattr(row, name)) for name in self.QUEUE_FILTERS}

    def list_history_for_patient(self, patient_id: int) -> List[AppointmentModel]:
        """Všechny rezervace pacienta (nejnovější první) včetně návštěv a vykázaných výkonů."""
        return (
            self.db.query(AppointmentModel)
            .options(
                joinedload(AppointmentModel.doctor),
                joinedload(AppointmentModel.visit)
                .selectinload(VisitModel.items)
                .joinedload(VisitProcedureModel.procedure),
            )
            .filter(AppointmentModel.patient_id == patient_id)
            .order_by(AppointmentModel.start_at.desc())
            .all()
        )
