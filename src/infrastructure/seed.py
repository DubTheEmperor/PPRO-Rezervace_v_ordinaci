import logging
from sqlalchemy.orm import Session
from src.config import settings
from src.infrastructure.models.user_model import UserModel, UserRole
from src.infrastructure.repositories.user_repository import UserRepository
from src.business.security import hash_password

logger = logging.getLogger("seed")


def seed_initial_users(db: Session) -> None:
    """Založí výchozí demo uživatele, pokud ještě neexistují."""
    repo = UserRepository(db)

    default_users = [
        {
            "username": settings.FIRST_ADMIN_USERNAME,
            "email": settings.FIRST_ADMIN_EMAIL,
            "full_name": settings.FIRST_ADMIN_FULL_NAME,
            "password": settings.FIRST_ADMIN_PASSWORD,
            "role": UserRole.ADMIN,
        },
        {
            "username": "vera",
            "email": "vera@ordinacenavyhlidce.cz",
            "full_name": "Věra Nováková (Recepce)",
            "password": "Vera123!",
            "role": UserRole.RECEPTIONIST,
        },
        {
            "username": "hruba",
            "email": "jana.hruba@ordinacenavyhlidce.cz",
            "full_name": "MUDr. Jana Hrubá",
            "password": "Hruba123!",
            "role": UserRole.DOCTOR,
        },
    ]

    for user_data in default_users:
        existing = repo.get_by_username(user_data["username"])
        if not existing:
            new_user = UserModel(
                username=user_data["username"],
                email=user_data["email"],
                full_name=user_data["full_name"],
                hashed_password=hash_password(user_data["password"]),
                role=user_data["role"],
                is_active=True,
            )
            repo.create(new_user)
            logger.info(f"Seed: vytvořen uživatel '{user_data['username']}' s rolí {user_data['role']}")
