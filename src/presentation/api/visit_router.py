from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.business.domain import get_db, User
from src.business.dto import VisitUpdate
from src.business.services.visit_service import VisitService
from src.presentation.dependencies import get_current_user
from src.presentation.schemas.visit_schemas import (
    DayAgendaResponse,
    VisitResponse,
    visit_to_response,
)

router = APIRouter(tags=["Záznam o návštěvě"])


@router.get(
    "/doctors/{doctor_id}/agenda",
    response_model=DayAgendaResponse,
    summary="Pracovní fronta lékaře pro daný den",
    description="Rezervace dne se stavem zápisu: WAITING, TO_RECORD, DRAFT, CLOSED.",
)
def get_day_agenda(
    doctor_id: int,
    day: date = Query(..., alias="date", description="Den (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return VisitService(db).get_day_agenda(doctor_id, day, current_user)


@router.post(
    "/appointments/{appointment_id}/visit",
    response_model=VisitResponse,
    summary="Otevření záznamu návštěvy",
    description=(
        "Založí koncept záznamu k proběhlé rezervaci, případně vrátí existující záznam. "
        "Výkony nelze zapsat k návštěvě, která ještě neproběhla. Smí lékař návštěvy nebo ADMIN."
    ),
)
def open_visit(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return visit_to_response(VisitService(db).open_visit(appointment_id, current_user))


@router.get("/visits/{visit_id}", response_model=VisitResponse, summary="Detail záznamu návštěvy")
def get_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return visit_to_response(VisitService(db).get_visit(visit_id))


@router.put(
    "/visits/{visit_id}",
    response_model=VisitResponse,
    summary="Uložení konceptu návštěvy",
    description="Nahradí klinickou poznámku a seznam výkonů. Uzavřenou návštěvu nelze měnit (409).",
)
def update_visit(
    visit_id: int,
    data: VisitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return visit_to_response(VisitService(db).update_draft(visit_id, data, current_user))


@router.post(
    "/visits/{visit_id}/close",
    response_model=VisitResponse,
    summary="Uzavření návštěvy",
    description="Zamkne záznam (dále neměnný) a označí rezervaci jako uskutečněnou.",
)
def close_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return visit_to_response(VisitService(db).close_visit(visit_id, current_user))
