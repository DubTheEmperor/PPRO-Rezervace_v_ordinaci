import logging
from sqlalchemy.orm import Session
from src.config import settings
from src.infrastructure.models.user_model import UserModel, UserRole
from src.infrastructure.models.patient_model import PatientModel
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.repositories.patient_repository import PatientRepository
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


def seed_initial_patients(db: Session) -> None:
    """Založí výchozí syntetické pacienty pro demonstraci a testování."""
    repo = PatientRepository(db)

    synthetic_patients = [
        {
            "first_name": "Eva",
            "last_name": "Krátká",
            "birth_year": 1978,
            "phone_number": "+420777111222",
            "insurance_number": "7854121234",
            "insurance_company_code": "111",
            "notes": "Pacientka často volá a omlouvá termíny na poslední chvíli.",
        },
        {
            "first_name": "Jan",
            "last_name": "Dvořák",
            "birth_year": 1985,
            "phone_number": "+420602333444",
            "insurance_number": "8501015678",
            "insurance_company_code": "205",
            "notes": "Alergie na penicilin.",
        },
        {
            "first_name": "Marie",
            "last_name": "Černá",
            "birth_year": 1962,
            "phone_number": "+420721555666",
            "insurance_number": "6258092345",
            "insurance_company_code": "211",
            "notes": "Pravidelné kontroly krevního tlaku každé 3 měsíce.",
        },
        {
            "first_name": "Petr",
            "last_name": "Svoboda",
            "birth_year": 1994,
            "phone_number": "+420732888999",
            "insurance_number": "9411203456",
            "insurance_company_code": "207",
            "notes": "Aktivní běžec, rehabilitace kolene.",
        },
    ]

    for p_data in synthetic_patients:
        existing = repo.get_by_insurance_number(p_data["insurance_number"])
        if not existing:
            patient = PatientModel(
                first_name=p_data["first_name"],
                last_name=p_data["last_name"],
                birth_year=p_data["birth_year"],
                phone_number=p_data["phone_number"],
                insurance_number=p_data["insurance_number"],
                insurance_company_code=p_data["insurance_company_code"],
                notes=p_data["notes"],
                is_active=True,
            )
            repo.create(patient)
            logger.info(f"Seed: vytvořen syntetický pacient '{p_data['first_name']} {p_data['last_name']}'")
