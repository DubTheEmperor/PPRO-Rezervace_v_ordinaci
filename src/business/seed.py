"""Inicializační (demo) data – syntetické účty, pacienti, lékaři a rezervace.

Seed patří do byznys vrstvy: používá byznys pravidla (hashování hesel,
rozpad termínu na sloty) a přes repozitáře zapisuje do datové vrstvy.
"""
import logging
from datetime import datetime, time, timedelta
from sqlalchemy.orm import Session
from src.config import settings
from src.infrastructure.models.user_model import UserModel, UserRole
from src.infrastructure.models.patient_model import PatientModel
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.models.doctor_model import DoctorModel
from src.infrastructure.models.appointment_model import AppointmentModel, AppointmentStatus
from src.infrastructure.repositories.patient_repository import PatientRepository
from src.infrastructure.repositories.doctor_repository import DoctorRepository
from src.infrastructure.repositories.appointment_repository import AppointmentRepository
from src.business.security import hash_password
from src.business.scheduling import local_now, slot_starts

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
        {
            "username": "maly",
            "email": "tomas.maly@ordinacenavyhlidce.cz",
            "full_name": "MUDr. Tomáš Malý",
            "password": "Maly123!",
            "role": UserRole.DOCTOR,
        },
        {
            "username": "vesela",
            "email": "lucie.vesela@ordinacenavyhlidce.cz",
            "full_name": "MUDr. Lucie Veselá",
            "password": "Vesela123!",
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


def _t(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


# Výchozí týdenní ordinační hodiny (0 = pondělí … 6 = neděle)
DEFAULT_DOCTORS = [
    {
        "username": "hruba",
        "full_name": "MUDr. Jana Hrubá",
        "specialization": "Praktický lékař pro dospělé",
        "color": "#0284c7",
        "hours": [(0, "08:00", "12:00"), (0, "13:00", "16:00"), (2, "08:00", "12:00"), (3, "12:00", "18:00")],
    },
    {
        "username": "maly",
        "full_name": "MUDr. Tomáš Malý",
        "specialization": "Interna",
        # Úterní odpoledne ordinuje na jiné adrese – proto v úterý jen dopoledne
        "color": "#059669",
        "hours": [(1, "07:30", "12:00"), (3, "07:30", "12:00"), (4, "08:00", "12:00")],
    },
    {
        "username": "vesela",
        "full_name": "MUDr. Lucie Veselá",
        "specialization": "Praktický lékař, preventivní péče",
        "color": "#9333ea",
        "hours": [(0, "13:00", "18:00"), (2, "13:00", "18:00"), (4, "08:00", "11:00")],
    },
]


def seed_doctors(db: Session) -> None:
    """Založí profily lékařů navázané na demo účty a jejich výchozí ordinační hodiny."""
    user_repo = UserRepository(db)
    doctor_repo = DoctorRepository(db)

    for d in DEFAULT_DOCTORS:
        user = user_repo.get_by_username(d["username"])
        if user is None or doctor_repo.get_by_user_id(user.id):
            continue
        doctor = doctor_repo.create(DoctorModel(
            user_id=user.id,
            full_name=d["full_name"],
            specialization=d["specialization"],
            color=d["color"],
            is_active=True,
        ))
        doctor_repo.replace_office_hours(
            doctor, [(day, _t(start), _t(end)) for day, start, end in d["hours"]]
        )
        logger.info(f"Seed: vytvořen lékař '{d['full_name']}' s ordinačními hodinami")


def seed_demo_appointments(db: Session) -> None:
    """Pár syntetických rezervací v příštím týdnu, aby byl kalendář v demu hned zaplněný."""
    appointment_repo = AppointmentRepository(db)
    if db.query(AppointmentModel).first() is not None:
        return

    user_repo = UserRepository(db)
    doctor_repo = DoctorRepository(db)
    patient_repo = PatientRepository(db)
    receptionist = user_repo.get_by_username("vera")

    today = local_now().date()
    next_monday = today + timedelta(days=7 - today.weekday())

    demo = [
        # (lékař, RČ pacienta, den od pondělí, začátek, konec, důvod)
        ("hruba", "7854121234", 0, "08:00", "08:30", "Kontrola krevního tlaku a úprava medikace."),
        ("hruba", "8501015678", 0, "09:00", "09:15", "Vystavení receptu."),
        ("maly", "6258092345", 1, "08:00", "08:45", "Preventivní prohlídka, odběr krve."),
        ("vesela", "9411203456", 2, "14:00", "14:30", "Bolest kolene po běhu."),
    ]
    for username, insurance_number, day_offset, start, end, reason in demo:
        user = user_repo.get_by_username(username)
        doctor = doctor_repo.get_by_user_id(user.id) if user else None
        patient = patient_repo.get_by_insurance_number(insurance_number)
        if doctor is None or patient is None:
            continue
        day = next_monday + timedelta(days=day_offset)
        start_at = datetime.combine(day, _t(start))
        end_at = datetime.combine(day, _t(end))
        appointment_repo.create_with_slots(
            AppointmentModel(
                doctor_id=doctor.id,
                patient_id=patient.id,
                start_at=start_at,
                end_at=end_at,
                reason=reason,
                status=AppointmentStatus.PLANNED,
                created_by_user_id=receptionist.id if receptionist else None,
            ),
            slot_starts(start_at, end_at),
        )
    logger.info("Seed: vytvořeny demo rezervace na příští týden")
