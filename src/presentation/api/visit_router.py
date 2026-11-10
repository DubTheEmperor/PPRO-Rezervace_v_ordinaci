from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.business.domain import get_db, User
from src.business.dto import VisitUpdate
from src.business.services.visit_service import VisitService
from src.presentation.dependencies import get_current_user
from src.presentation.schemas.visit_schemas import (
    PendingCountResponse,
    VisitQueueResponse,
    VisitResponse,
    visit_to_response,
)

router = APIRouter(tags=["Záznam o návštěvě"])


@router.get(
    "/doctors/{doctor_id}/visit-queue",
    response_model=VisitQueueResponse,
    summary="Fronta návštěv lékaře",
    description=(
        "Návštěvy od nejnovější do minulosti filtrované podle stavu zápisu: "
        "pending (K zápisu + Rozpracováno), today, draft, closed, all. "
        "Vidí jen daný lékař a administrátor. Stránkování přes kurzor `before`."
    ),
)
def get_visit_queue(
    doctor_id: int,
    queue_filter: str = Query("pending", alias="filter", description="pending | today | draft | closed | all"),
    before: Optional[datetime] = Query(None, description="Vrátit jen položky starší než tento čas"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return VisitService(db).get_visit_queue(doctor_id, queue_filter, current_user, before=before, limit=limit)


@router.get(
    "/visits/pending-count",
    response_model=PendingCountResponse,
    summary="Počet návštěv k vyřízení",
    description="Lékař – vlastní nevyřízené návštěvy, administrátor – součet všech lékařů.",
)
def get_pending_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PendingCountResponse(pending=VisitService(db).get_pending_count(current_user))


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
    return visit_to_response(VisitService(db).get_visit_for_user(visit_id, current_user))


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
