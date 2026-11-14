from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.infrastructure.models.user_model import UserModel, UserRole
from src.infrastructure.models.appointment_model import AppointmentModel
from src.infrastructure.models.visit_model import VisitModel
from src.infrastructure.models.doctor_model import DoctorModel
from src.infrastructure.models.doctor_sick_day_model import DoctorSickDayModel


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

    def has_history(self, user_id: int) -> bool:
        """Je účet zapsaný v historii ordinace (kdo co založil / zrušil / uzavřel) nebo propojený s lékařem?"""
        checks = [
            self.db.query(AppointmentModel.id).filter(
                or_(AppointmentModel.created_by_user_id == user_id,
                    AppointmentModel.cancelled_by_user_id == user_id)
            ),
            self.db.query(VisitModel.id).filter(
                or_(VisitModel.created_by_user_id == user_id,
                    VisitModel.updated_by_user_id == user_id,
                    VisitModel.closed_by_user_id == user_id)
            ),
            self.db.query(DoctorSickDayModel.id).filter(DoctorSickDayModel.created_by_user_id == user_id),
            self.db.query(DoctorModel.id).filter(DoctorModel.user_id == user_id),
        ]
        return any(self.db.query(q.exists()).scalar() for q in checks)

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
