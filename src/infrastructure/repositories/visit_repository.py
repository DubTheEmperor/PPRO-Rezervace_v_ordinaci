from typing import Optional, List, Sequence, Tuple
from sqlalchemy.orm import Session, joinedload, selectinload
from src.infrastructure.models.visit_model import VisitModel, VisitProcedureModel


class VisitRepository:
    def __init__(self, db: Session):
        self.db = db

    def _query(self):
        return self.db.query(VisitModel).options(
            selectinload(VisitModel.items).joinedload(VisitProcedureModel.procedure),
            joinedload(VisitModel.closed_by),
        )

    def get_by_id(self, visit_id: int) -> Optional[VisitModel]:
        return self._query().filter(VisitModel.id == visit_id).first()

    def get_by_appointment_id(self, appointment_id: int) -> Optional[VisitModel]:
        return self._query().filter(VisitModel.appointment_id == appointment_id).first()

    def create(self, visit: VisitModel) -> VisitModel:
        self.db.add(visit)
        self.db.commit()
        self.db.refresh(visit)
        return visit

    def save(self, visit: VisitModel) -> VisitModel:
        """Uloží změny návštěvy (případně i navázané rezervace) v jedné transakci."""
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(visit)
        return visit

    def replace_items(
        self, visit: VisitModel, items: Sequence[Tuple[int, int, int]]
    ) -> None:
        """Nahradí položky návštěvy (procedure_id, quantity, points_per_unit) – bez commitu."""
        visit.items.clear()
        self.db.flush()
        for procedure_id, quantity, points_per_unit in items:
            visit.items.append(VisitProcedureModel(
                procedure_id=procedure_id, quantity=quantity, points_per_unit=points_per_unit,
            ))
