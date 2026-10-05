from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.infrastructure.database import get_db
from src.infrastructure.models.user_model import UserModel
from src.presentation.schemas.auth_schemas import LoginRequest, TokenResponse
from src.presentation.schemas.user_schemas import UserResponse
from src.business.services.auth_service import AuthService
from src.presentation.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Autentizace"])


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Přihlášení uživatele (OAuth2 kompatibilní pro Swagger)",
    description="Vrací JWT Bearer token na základě jména a hesla předaných ve formuláři.",
)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    access_token = auth_service.create_user_token(user)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Přihlášení uživatele (JSON)",
    description="Vrací JWT Bearer token na základě JSON payloadu.",
)
def login_json(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(login_data.username, login_data.password)
    access_token = auth_service.create_user_token(user)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Profil přihlášeného uživatele",
    description="Vrátí detail právě přihlášeného uživatele na základě předaného Bearer tokenu.",
)
def get_current_user_profile(
    current_user: UserModel = Depends(get_current_user)
):
    return UserResponse.model_validate(current_user)
