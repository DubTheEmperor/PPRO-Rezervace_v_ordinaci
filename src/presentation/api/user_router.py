from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.infrastructure.database import get_db
from src.infrastructure.models.user_model import UserModel, UserRole
from src.presentation.schemas.user_schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
)
from src.business.services.user_service import UserService
from src.presentation.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/users", tags=["Správa uživatelů"])


@router.get(
    "",
    response_model=UserListResponse,
    summary="Seznam uživatelů",
    description="Vrátí stránkovaný seznam uživatelů s možností filtrace podle role, stavu a fulltextového vyhledávání.",
)
def list_users(
    skip: int = Query(0, ge=0, description="Počet přeskočených záznamů"),
    limit: int = Query(50, ge=1, le=100, description="Maximální počet záznamů"),
    search: Optional[str] = Query(None, description="Hledat podle jména, uživatelského jména nebo e-mailu"),
    role: Optional[UserRole] = Query(None, description="Filtrovat podle role"),
    is_active: Optional[bool] = Query(None, description="Filtrovat podle stavu aktivity"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    user_service = UserService(db)
    users, total = user_service.get_users(
        skip=skip, limit=limit, search=search, role=role, is_active=is_active
    )
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Detail uživatele podle ID",
)
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    return UserResponse.model_validate(user)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Vytvoření nového uživatele",
    description="Pouze pro uživatele s rolí ADMIN.",
)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN)),
):
    user_service = UserService(db)
    new_user = user_service.create_user(user_data)
    return UserResponse.model_validate(new_user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Úprava uživatele",
    description="Pouze pro uživatele s rolí ADMIN.",
)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN)),
):
    user_service = UserService(db)
    updated_user = user_service.update_user(user_id, user_data)
    return UserResponse.model_validate(updated_user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Smazání uživatele",
    description="Pouze pro uživatele s rolí ADMIN. Nelze smazat posledního aktivního administrátora.",
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(UserRole.ADMIN)),
):
    user_service = UserService(db)
    user_service.delete_user(user_id)
    return None
