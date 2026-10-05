from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.infrastructure.models.user_model import UserModel, UserRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[UserModel]:
        return self.db.query(UserModel).filter(UserModel.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[UserModel]:
        return self.db.query(UserModel).filter(UserModel.username == username).first()

    def get_by_email(self, email: str) -> Optional[UserModel]:
        return self.db.query(UserModel).filter(UserModel.email == email).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[UserModel], int]:
        query = self.db.query(UserModel)

        if search:
            search_filter = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    UserModel.username.ilike(search_filter),
                    UserModel.full_name.ilike(search_filter),
                    UserModel.email.ilike(search_filter),
                )
            )

        if role:
            query = query.filter(UserModel.role == role)

        if is_active is not None:
            query = query.filter(UserModel.is_active == is_active)

        total = query.count()
        users = query.order_by(UserModel.id.asc()).offset(skip).limit(limit).all()
        return users, total

    def count_active_admins(self) -> int:
        return (
            self.db.query(UserModel)
            .filter(UserModel.role == UserRole.ADMIN, UserModel.is_active.is_(True))
            .count()
        )

    def create(self, user: UserModel) -> UserModel:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: UserModel) -> UserModel:
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: UserModel) -> None:
        self.db.delete(user)
        self.db.commit()
