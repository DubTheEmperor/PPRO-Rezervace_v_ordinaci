from typing import Callable
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from src.business.domain import get_db, User, UserRole
from src.business.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error=True
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Vytáhne Bearer token z požadavku; ověření a načtení uživatele řeší byznys vrstva."""
    return AuthService(db).get_user_from_token(token)


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Závislost pro kontrolu oprávnění uživatele podle role."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        return AuthService.ensure_role(current_user, allowed_roles)

    return role_checker
