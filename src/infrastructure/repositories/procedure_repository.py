from typing import Optional, List, Iterable
from sqlalchemy import or_
from sqlalchemy.orm import Session
from src.infrastructure.models.procedure_model import ProcedureModel


class ProcedureRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, procedure_id: int) -> Optional[ProcedureModel]:
        return self.db.query(ProcedureModel).filter(ProcedureModel.id == procedure_id).first()

    def get_by_code(self, code: str) -> Optional[ProcedureModel]:
        return self.db.query(ProcedureModel).filter(ProcedureModel.code == code).first()

    def get_by_ids(self, ids: Iterable[int]) -> List[ProcedureModel]:
        id_list = list(ids)
        if not id_list:
            return []
        return self.db.query(ProcedureModel).filter(ProcedureModel.id.in_(id_list)).all()

    def search(
        self, text: Optional[str] = None, is_active: Optional[bool] = None, limit: int = 50
    ) -> List[ProcedureModel]:
        query = self.db.query(ProcedureModel)
        if text and text.strip():
            pattern = f"%{text.strip()}%"
            query = query.filter(or_(ProcedureModel.code.ilike(pattern), ProcedureModel.name.ilike(pattern)))
        if is_active is not None:
            query = query.filter(ProcedureModel.is_active == is_active)
        return query.order_by(ProcedureModel.code.asc()).limit(limit).all()

    def create(self, procedure: ProcedureModel) -> ProcedureModel:
        self.db.add(procedure)
        self.db.commit()
        self.db.refresh(procedure)
        return procedure

    def update(self, procedure: ProcedureModel) -> ProcedureModel:
        self.db.commit()
        self.db.refresh(procedure)
        return procedure
