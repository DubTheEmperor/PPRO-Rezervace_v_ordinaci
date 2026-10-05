from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.infrastructure.models.user_model import UserModel, UserRole
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.schemas.user_schemas import UserCreate, UserUpdate
from src.business.security import hash_password


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def get_user_by_id(self, user_id: int) -> UserModel:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Uživatel s ID {user_id} nebyl nalezen."
            )
        return user

    def get_users(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[UserModel], int]:
        return self.repo.get_all(
            skip=skip, limit=limit, search=search, role=role, is_active=is_active
        )

    def create_user(self, user_data: UserCreate) -> UserModel:
        # Validace unikátnosti username
        if self.repo.get_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Uživatelské jméno '{user_data.username}' je již obsazeno."
            )

        # Validace unikátnosti emailu
        if self.repo.get_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"E-mail '{user_data.email}' již v systému existuje."
            )

        new_user = UserModel(
            username=user_data.username.strip(),
            email=user_data.email.strip().lower(),
            full_name=user_data.full_name.strip(),
            hashed_password=hash_password(user_data.password),
            role=user_data.role,
            is_active=user_data.is_active,
        )
        return self.repo.create(new_user)

    def update_user(self, user_id: int, user_data: UserUpdate) -> UserModel:
        user = self.get_user_by_id(user_id)

        # Validace emailu při změně
        if user_data.email and user_data.email.lower() != user.email.lower():
            existing = self.repo.get_by_email(user_data.email)
            if existing and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"E-mail '{user_data.email}' je již přiřazen jinému uživateli."
                )
            user.email = user_data.email.strip().lower()

        # Ochrana před deaktivací nebo změnou role posledního aktivního administrátora
        if user.role == UserRole.ADMIN:
            active_admins = self.repo.count_active_admins()
            if active_admins <= 1:
                if user_data.is_active is False:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Nelze deaktivovat posledního aktivního administrátora v systému."
                    )
                if user_data.role and user_data.role != UserRole.ADMIN:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Nelze odebrat roli administrátora poslednímu aktivnímu administrátorovi."
                    )

        if user_data.full_name is not None:
            user.full_name = user_data.full_name.strip()

        if user_data.role is not None:
            user.role = user_data.role

        if user_data.is_active is not None:
            user.is_active = user_data.is_active

        if user_data.password:
            user.hashed_password = hash_password(user_data.password)

        return self.repo.update(user)

    def delete_user(self, user_id: int) -> None:
        user = self.get_user_by_id(user_id)

        # Ochrana před smazáním posledního administrátora
        if user.role == UserRole.ADMIN:
            active_admins = self.repo.count_active_admins()
            if active_admins <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nelze smazat posledního aktivního administrátora v systému."
                )

        self.repo.delete(user)
