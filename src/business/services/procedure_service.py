from typing import Optional, List
from sqlalchemy.orm import Session
from src.business.dto.visit_dto import ProcedureCreate, ProcedureUpdate
from src.business.exceptions import BusinessRuleError, NotFoundError
from src.infrastructure.models.procedure_model import ProcedureModel
from src.infrastructure.repositories.procedure_repository import ProcedureRepository


class ProcedureService:
    """Centrální číselník zdravotních výkonů."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ProcedureRepository(db)

    def search(self, text: Optional[str] = None, is_active: Optional[bool] = True, limit: int = 50) -> List[ProcedureModel]:
        return self.repo.search(text=text, is_active=is_active, limit=limit)

    def get_procedure(self, procedure_id: int) -> ProcedureModel:
        procedure = self.repo.get_by_id(procedure_id)
        if not procedure:
            raise NotFoundError(f"Výkon s ID {procedure_id} nebyl nalezen.")
        return procedure

    def create_procedure(self, data: ProcedureCreate) -> ProcedureModel:
        if self.repo.get_by_code(data.code):
            raise BusinessRuleError(f"Výkon s kódem '{data.code}' již v číselníku existuje.")
        return self.repo.create(ProcedureModel(
            code=data.code, name=data.name, points=data.points, is_active=data.is_active,
        ))

    def update_procedure(self, procedure_id: int, data: ProcedureUpdate) -> ProcedureModel:
        """Změna bodů se netýká již zapsaných návštěv – ty drží snapshot bodů."""
        procedure = self.get_procedure(procedure_id)
        if data.name is not None:
            procedure.name = data.name.strip()
        if data.points is not None:
            procedure.points = data.points
        if data.is_active is not None:
            procedure.is_active = data.is_active
        return self.repo.update(procedure)
