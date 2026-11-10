from typing import Iterable
from sqlalchemy.orm import Session
from src.business.exceptions import AccountDisabledError, AuthenticationError, PermissionDeniedError
from src.business.security import verify_password, create_access_token, decode_access_token
from src.infrastructure.models.user_model import UserModel, UserRole
from src.infrastructure.repositories.user_repository import UserRepository

INVALID_CREDENTIALS = "Neplatné nebo vypršené přihlašovací údaje."


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def authenticate_user(self, username: str, password: str) -> UserModel:
        user = self.repo.get_by_username(username.strip())
        if not user:
            raise AuthenticationError("Nesprávné uživatelské jméno nebo heslo.")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Nesprávné uživatelské jméno nebo heslo.")

        if not user.is_active:
            raise AccountDisabledError("Tento uživatelský účet je deaktivován.")

        return user

    def create_user_token(self, user: UserModel) -> str:
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value,
        }
        return create_access_token(data=token_data)

    def get_user_from_token(self, token: str) -> UserModel:
        """Ověří JWT token a vrátí aktivního uživatele, kterému patří."""
        payload = decode_access_token(token)
        if payload is None:
            raise AuthenticationError(INVALID_CREDENTIALS)

        try:
            user_id = int(payload.get("sub"))
        except (TypeError, ValueError):
            raise AuthenticationError(INVALID_CREDENTIALS)

        user = self.repo.get_by_id(user_id)
        if user is None:
            raise AuthenticationError(INVALID_CREDENTIALS)

        if not user.is_active:
            raise AccountDisabledError("Tento uživatelský účet je deaktivován.")

        return user

    @staticmethod
    def ensure_role(user: UserModel, allowed_roles: Iterable[UserRole]) -> UserModel:
        """Ověří, že uživatel má jednu z povolených rolí."""
        allowed = list(allowed_roles)
        if user.role not in allowed:
            raise PermissionDeniedError(
                f"Přístup odepřen: pro tuto akci je vyžadována role {[r.value for r in allowed]}."
            )
        return user
