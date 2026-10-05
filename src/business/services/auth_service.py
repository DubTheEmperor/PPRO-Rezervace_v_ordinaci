from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.infrastructure.models.user_model import UserModel
from src.infrastructure.repositories.user_repository import UserRepository
from src.business.security import verify_password, create_access_token


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def authenticate_user(self, username: str, password: str) -> UserModel:
        user = self.repo.get_by_username(username.strip())
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nesprávné uživatelské jméno nebo heslo.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nesprávné uživatelské jméno nebo heslo.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tento uživatelský účet je deaktivován.",
            )

        return user

    def create_user_token(self, user: UserModel) -> str:
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value,
        }
        return create_access_token(data=token_data)
