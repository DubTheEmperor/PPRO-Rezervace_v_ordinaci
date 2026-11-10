from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.business.domain import get_db, User, UserRole
from src.business.dto import ProcedureCreate, ProcedureUpdate
from src.business.services.procedure_service import ProcedureService
from src.presentation.dependencies import get_current_user, require_roles
from src.presentation.schemas.visit_schemas import ProcedureResponse

router = APIRouter(prefix="/procedures", tags=["Číselník výkonů"])


@router.get(
    "",
    response_model=List[ProcedureResponse],
    summary="Vyhledání v číselníku výkonů",
    description="Hledá podle kódu nebo názvu výkonu. Ve výchozím stavu vrací jen aktivní výkony.",
)
def search_procedures(
    search: Optional[str] = Query(None, description="Kód nebo část názvu výkonu"),
    is_active: Optional[bool] = Query(True, description="Filtrovat podle aktivity (prázdné = vše)"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    procedures = ProcedureService(db).search(text=search, is_active=is_active, limit=limit)
    return [ProcedureResponse.model_validate(p) for p in procedures]


@router.post(
    "",
    response_model=ProcedureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Přidání výkonu do číselníku",
    description="Pouze pro uživatele s rolí ADMIN.",
)
def create_procedure(
    data: ProcedureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return ProcedureResponse.model_validate(ProcedureService(db).create_procedure(data))


@router.put(
    "/{procedure_id}",
    response_model=ProcedureResponse,
    summary="Úprava výkonu v číselníku",
    description="Pouze ADMIN. Změna bodů se neprojeví u již zapsaných návštěv (drží snapshot bodů).",
)
def update_procedure(
    procedure_id: int,
    data: ProcedureUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return ProcedureResponse.model_validate(ProcedureService(db).update_procedure(procedure_id, data))
