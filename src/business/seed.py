"""Inicializační (demo) data – syntetické účty, pacienti, lékaři a rezervace.

Seed patří do byznys vrstvy: používá byznys pravidla (hashování hesel,
rozpad termínu na sloty) a přes repozitáře zapisuje do datové vrstvy.
"""
import logging
from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.config import settings
from src.infrastructure.models.user_model import UserModel, UserRole
from src.infrastructure.models.patient_model import PatientModel
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.models.doctor_model import DoctorModel
from src.infrastructure.models.appointment_model import AppointmentModel, AppointmentStatus
from src.infrastructure.models.procedure_model import ProcedureModel
from src.infrastructure.models.visit_model import VisitModel, VisitStatus
from src.infrastructure.repositories.patient_repository import PatientRepository
from src.infrastructure.repositories.doctor_repository import DoctorRepository
from src.infrastructure.repositories.appointment_repository import AppointmentRepository
from src.infrastructure.repositories.procedure_repository import ProcedureRepository
from src.infrastructure.repositories.visit_repository import VisitRepository
from src.business.security import hash_password
from src.business.scheduling import LOCAL_TZ, local_now, slot_starts

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
        },
        {
            "first_name": "Jan",
            "last_name": "Dvořák",
            "birth_year": 1985,
            "phone_number": "+420602333444",
            "insurance_number": "8501015678",
            "insurance_company_code": "205",
        },
        {
            "first_name": "Marie",
            "last_name": "Černá",
            "birth_year": 1962,
            "phone_number": "+420721555666",
            "insurance_number": "6258092345",
            "insurance_company_code": "211",
        },
        {
            "first_name": "Petr",
            "last_name": "Svoboda",
            "birth_year": 1994,
            "phone_number": "+420732888999",
            "insurance_number": "9411203456",
            "insurance_company_code": "207",
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
                is_active=True,
            )
            repo.create(patient)
            logger.info(f"Seed: vytvořen syntetický pacient '{p_data['first_name']} {p_data['last_name']}'")


def _t(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


# Syntetické jiné pracoviště (stejná hodnota je v migraci 009 pro doplnění existující databáze)
DEMO_AWAY_LOCATION = "Poliklinika Jih"

# Výchozí týdenní ordinační hodiny (0 = pondělí … 6 = neděle)
DEFAULT_DOCTORS = [
    {
        "username": "hruba",
        "full_name": "MUDr. Jana Hrubá",
        "specialization": "Praktický lékař pro dospělé",
        "color": "#0284c7",
        "icp": "52999101",
        "specialty_code": "001",
        "hours": [(0, "08:00", "12:00"), (0, "13:00", "16:00"), (2, "08:00", "12:00"), (3, "12:00", "18:00")],
    },
    {
        "username": "maly",
        "full_name": "MUDr. Tomáš Malý",
        "specialization": "Interna",
        "color": "#059669",
        "icp": "52999102",
        "specialty_code": "101",
        "hours": [(1, "07:30", "12:00"), (3, "07:30", "12:00"), (4, "08:00", "12:00")],
        # Úterní odpoledne ordinuje na jiné adrese – v kalendáři vidět, objednat nelze
        "away": [(1, "13:00", "17:00", DEMO_AWAY_LOCATION)],
    },
    {
        "username": "vesela",
        "full_name": "MUDr. Lucie Veselá",
        "specialization": "Praktický lékař, preventivní péče",
        "color": "#9333ea",
        "icp": "52999103",
        "specialty_code": "001",
        "hours": [(0, "13:00", "18:00"), (2, "13:00", "18:00"), (4, "08:00", "11:00")],
    },
]


def seed_doctors(db: Session) -> None:
    """Založí profily lékařů navázané na demo účty a jejich výchozí ordinační hodiny."""
    user_repo = UserRepository(db)
    doctor_repo = DoctorRepository(db)

    for d in DEFAULT_DOCTORS:
        user = user_repo.get_by_username(d["username"])
        if user is None:
            continue
        existing = doctor_repo.get_by_user_id(user.id)
        if existing:
            # Doplnění identifikátorů pro výkazy (FP7) u lékařů založených dřívějším seedem
            if existing.icp is None and existing.specialty_code is None:
                existing.icp = d["icp"]
                existing.specialty_code = d["specialty_code"]
                doctor_repo.update(existing)
            continue
        doctor = doctor_repo.create(DoctorModel(
            user_id=user.id,
            full_name=d["full_name"],
            specialization=d["specialization"],
            color=d["color"],
            icp=d["icp"],
            specialty_code=d["specialty_code"],
            is_active=True,
        ))
        doctor_repo.replace_office_hours(doctor, [
            *((day, _t(start), _t(end), "OFFICE", None) for day, start, end in d["hours"]),
            *((day, _t(start), _t(end), "ELSEWHERE", loc) for day, start, end, loc in d.get("away", [])),
        ])
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


# Ilustrativní číselník výkonů – kódy a názvy pro demo, bodové hodnoty jsou syntetické
DEFAULT_PROCEDURES = [
    ("01021", "Komplexní vyšetření praktickým lékařem", 520),
    ("01022", "Opakované komplexní vyšetření", 260),
    ("01023", "Cílené vyšetření praktickým lékařem", 130),
    ("01025", "Kontrolní vyšetření praktickým lékařem", 70),
    ("01030", "Telefonická konzultace", 35),
    ("02230", "Měření krevního tlaku a pulzu", 20),
    ("09127", "Elektrokardiogram (EKG)", 110),
    ("09215", "Injekce i.m., s.c., i.d.", 16),
    ("09219", "Injekce i.v. u dospělého", 22),
    ("09511", "Převaz rány", 45),
    ("09543", "Odběr venózní krve", 30),
    ("09547", "Výplach zevního zvukovodu", 40),
]


def seed_procedures(db: Session) -> None:
    """Naplní číselník výkonů, pokud v něm daný kód ještě není."""
    repo = ProcedureRepository(db)
    for code, name, points in DEFAULT_PROCEDURES:
        if repo.get_by_code(code) is None:
            repo.create(ProcedureModel(code=code, name=name, points=points, is_active=True))
    logger.info("Seed: číselník výkonů připraven")


def seed_demo_visits(db: Session) -> None:
    """Dvě rezervace z minulého týdne: jedna s uzavřenou návštěvou, druhá čeká na zápis výkonů.

    Seed zakládá rezervace v minulosti přímo přes repozitář (servis to správně zakazuje).
    """
    if db.query(VisitModel).first() is not None:
        return

    user_repo = UserRepository(db)
    hruba_user = user_repo.get_by_username("hruba")
    receptionist = user_repo.get_by_username("vera")
    doctor = DoctorRepository(db).get_by_user_id(hruba_user.id) if hruba_user else None
    patient_repo = PatientRepository(db)
    closed_patient = patient_repo.get_by_insurance_number("6258092345")   # Černá
    pending_patient = patient_repo.get_by_insurance_number("9411203456")  # Svoboda
    procedures = {p.code: p for p in ProcedureRepository(db).search(is_active=True, limit=200)}
    if not (doctor and closed_patient and pending_patient and procedures):
        return

    today = local_now().date()
    last_monday = today - timedelta(days=today.weekday() + 7)  # Hrubá ordinuje v pondělí 8–12
    appointment_repo = AppointmentRepository(db)

    def past_appointment(patient, start, end, reason, status):
        start_at = datetime.combine(last_monday, _t(start))
        end_at = datetime.combine(last_monday, _t(end))
        return appointment_repo.create_with_slots(
            AppointmentModel(
                doctor_id=doctor.id, patient_id=patient.id, start_at=start_at, end_at=end_at,
                reason=reason, status=status,
                created_by_user_id=receptionist.id if receptionist else None,
            ),
            slot_starts(start_at, end_at),
        )

    closed_appt = past_appointment(
        closed_patient, "09:00", "09:30", "Pravidelná kontrola krevního tlaku.", AppointmentStatus.COMPLETED
    )
    past_appointment(pending_patient, "10:00", "10:15", "Kontrola kolene po rehabilitaci.", AppointmentStatus.PLANNED)

    visit = VisitModel(
        appointment_id=closed_appt.id, doctor_id=doctor.id, patient_id=closed_patient.id,
        status=VisitStatus.CLOSED, clinical_note="TK 135/85, bez obtíží. Pokračovat v medikaci.",
        created_by_user_id=hruba_user.id, updated_by_user_id=hruba_user.id,
        closed_by_user_id=hruba_user.id, closed_at=datetime.now(timezone.utc),
    )
    visit_repo = VisitRepository(db)
    visit_repo.create(visit)
    visit_repo.replace_items(visit, [
        (procedures[code].id, quantity, procedures[code].points)
        for code, quantity in (("01025", 1), ("02230", 1), ("09543", 1))
    ])
    visit_repo.save(visit)
    logger.info("Seed: vytvořeny demo návštěvy z minulého týdne")


def seed_demo_cancellations(db: Session) -> None:
    """Historická zrušení a nedostavení (FP5), aby demo ukázalo všechny barvy spolehlivosti.

    Krátká: 3× zrušeno (1× pozdě) + 2× nedostavila se → červená; Dvořák: 1 + 1 → žlutá;
    ostatní pacienti zůstávají zelení. Zrušené termíny neobsazují sloty.
    """
    if db.query(AppointmentModel).filter(
        AppointmentModel.status.in_((AppointmentStatus.CANCELLED_BY_PATIENT, AppointmentStatus.NO_SHOW))
    ).first() is not None:
        return

    user_repo = UserRepository(db)
    hruba_user = user_repo.get_by_username("hruba")
    receptionist = user_repo.get_by_username("vera")
    doctor = DoctorRepository(db).get_by_user_id(hruba_user.id) if hruba_user else None
    patient_repo = PatientRepository(db)
    if doctor is None:
        return

    today = local_now().date()
    this_monday = today - timedelta(days=today.weekday())
    demo = [
        # (RČ pacienta, před kolika týdny, stav, kolik hodin předem zrušeno)
        ("7854121234", 3, AppointmentStatus.CANCELLED_BY_PATIENT, 2),
        ("7854121234", 7, AppointmentStatus.NO_SHOW, None),
        ("7854121234", 12, AppointmentStatus.CANCELLED_BY_PATIENT, 72),
        ("7854121234", 20, AppointmentStatus.NO_SHOW, None),
        ("7854121234", 30, AppointmentStatus.CANCELLED_BY_PATIENT, 48),
        ("8501015678", 5, AppointmentStatus.CANCELLED_BY_PATIENT, 96),
        ("8501015678", 16, AppointmentStatus.NO_SHOW, None),
    ]
    for insurance_number, weeks_ago, status, hours_before in demo:
        patient = patient_repo.get_by_insurance_number(insurance_number)
        if patient is None:
            continue
        start_at = datetime.combine(this_monday - timedelta(weeks=weeks_ago), _t("10:30"))
        if hours_before is not None:
            event_local = start_at - timedelta(hours=hours_before)
        else:
            event_local = start_at + timedelta(hours=1)
        db.add(AppointmentModel(
            doctor_id=doctor.id, patient_id=patient.id,
            start_at=start_at, end_at=start_at + timedelta(minutes=15),
            reason="Kontrolní vyšetření.", status=status,
            created_by_user_id=receptionist.id if receptionist else None,
            cancelled_by_user_id=receptionist.id if receptionist else None,
            cancelled_at=event_local.replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc),
        ))
    db.commit()
    logger.info("Seed: vytvořena demo zrušení a nedostavení")


# Demo podklady pro měsíční výkaz (FP7) – minulý kalendářní měsíc.
# (lékař, den v týdnu, kolikátý v měsíci, začátek, konec, RČ pacienta, výkony [(kód, počet)])
# Prázdný seznam výkonů = proběhlý termín bez záznamu (výkaz na něj upozorní).
DEMO_REPORT_VISITS = [
    ("hruba", 2, 0, "08:00", "08:30", "7854121234", [("01021", 1), ("02230", 1), ("09543", 1)]),
    ("hruba", 2, 0, "09:00", "09:15", "8501015678", [("01023", 1), ("09215", 3)]),
    ("hruba", 2, 1, "08:30", "09:00", "6258092345", [("01025", 1), ("09127", 1)]),
    ("hruba", 2, 1, "10:00", "10:15", "9411203456", [("01023", 1), ("09511", 2)]),
    ("hruba", 2, 2, "08:00", "08:15", "7854121234", [("01030", 1)]),
    ("hruba", 2, 2, "11:00", "11:15", "8501015678", []),
    ("maly", 1, 0, "08:00", "08:45", "6258092345", [("01021", 1), ("09543", 1), ("09127", 1)]),
    ("maly", 1, 1, "09:00", "09:15", "9411203456", [("01025", 1), ("02230", 1)]),
]
# Důvod návštěvy demo podkladů – zároveň značka, že seed už proběhl (jen jednou na databázi)
DEMO_REPORT_REASON = "Pravidelná kontrola zdravotního stavu."


def _nth_weekday(year: int, month: int, weekday: int, index: int):
    day = date(year, month, 1)
    day += timedelta(days=(weekday - day.weekday()) % 7)
    day += timedelta(weeks=index)
    return day if day.month == month else None


def seed_demo_report_visits(db: Session) -> None:
    """Uzavřené návštěvy v minulém měsíci (různé pojišťovny, opakovaný výkon) a jedna nezapsaná,
    aby měsíční výkaz v demu nebyl prázdný a ukázal i upozornění na neúplnost."""
    if db.query(AppointmentModel).filter(AppointmentModel.reason == DEMO_REPORT_REASON).first() is not None:
        return
    user_repo = UserRepository(db)
    doctor_repo = DoctorRepository(db)
    patient_repo = PatientRepository(db)
    appointment_repo = AppointmentRepository(db)
    visit_repo = VisitRepository(db)
    procedures = {p.code: p for p in ProcedureRepository(db).search(is_active=True, limit=200)}
    receptionist = user_repo.get_by_username("vera")

    first_of_month = local_now().date().replace(day=1)
    previous = first_of_month - timedelta(days=1)
    created = 0

    for username, weekday, index, start, end, insurance_number, items in DEMO_REPORT_VISITS:
        user = user_repo.get_by_username(username)
        doctor = doctor_repo.get_by_user_id(user.id) if user else None
        patient = patient_repo.get_by_insurance_number(insurance_number)
        day = _nth_weekday(previous.year, previous.month, weekday, index)
        if doctor is None or patient is None or day is None:
            continue
        if any(code not in procedures for code, _ in items):
            continue
        start_at = datetime.combine(day, _t(start))
        end_at = datetime.combine(day, _t(end))
        # Idempotence: termín v daném čase už existuje (dřívější seed nebo ruční rezervace)
        if appointment_repo.list_taken_slot_starts(doctor.id, start_at, end_at):
            continue
        try:
            appointment = appointment_repo.create_with_slots(
                AppointmentModel(
                    doctor_id=doctor.id, patient_id=patient.id, start_at=start_at, end_at=end_at,
                    reason=DEMO_REPORT_REASON,
                    status=AppointmentStatus.COMPLETED if items else AppointmentStatus.PLANNED,
                    created_by_user_id=receptionist.id if receptionist else None,
                ),
                slot_starts(start_at, end_at),
            )
        except IntegrityError:
            continue
        created += 1
        if not items:
            continue
        closed_at = end_at.replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc)
        visit = VisitModel(
            appointment_id=appointment.id, doctor_id=doctor.id, patient_id=patient.id,
            status=VisitStatus.CLOSED, clinical_note="Bez komplikací.",
            created_by_user_id=user.id, updated_by_user_id=user.id,
            closed_by_user_id=user.id, closed_at=closed_at,
        )
        visit_repo.create(visit)
        visit_repo.replace_items(visit, [
            (procedures[code].id, quantity, procedures[code].points) for code, quantity in items
        ])
        visit_repo.save(visit)

    if created:
        logger.info(f"Seed: vytvořeny demo podklady pro výkaz za {previous.month:02d}/{previous.year}")


# Demo nemoc (otevřený bod 5): MUDr. Veselá je příští středu a čtvrtek nemocná,
# její středeční termíny tak hned čekají ve frontě K přeobjednání.
# (RČ pacienta, začátek, konec, důvod)
DEMO_SICK_APPOINTMENTS = [
    ("9411203456", "14:00", "14:30", "Bolest kolene po běhu."),
    ("6258092345", "16:00", "16:15", "Kontrola po očkování."),
]


def seed_demo_sickness(db: Session) -> None:
    """Jednou na databázi: demo nemoc MUDr. Veselé (dny st–čt příštího týdne)."""
    from src.business.dto.doctor_dto import SickDaysChange
    from src.business.services.doctor_service import DoctorService

    doctor_repo = DoctorRepository(db)
    if doctor_repo.has_any_sick_day():
        return
    user_repo = UserRepository(db)
    vesela = user_repo.get_by_username("vesela")
    admin = db.query(UserModel).filter(UserModel.role == UserRole.ADMIN).first()
    receptionist = user_repo.get_by_username("vera")
    doctor = doctor_repo.get_by_user_id(vesela.id) if vesela else None
    if doctor is None or admin is None:
        return

    today = local_now().date()
    wednesday = today + timedelta(days=7 - today.weekday() + 2)
    appointment_repo = AppointmentRepository(db)
    patient_repo = PatientRepository(db)
    for insurance_number, start, end, reason in DEMO_SICK_APPOINTMENTS:
        patient = patient_repo.get_by_insurance_number(insurance_number)
        start_at = datetime.combine(wednesday, _t(start))
        end_at = datetime.combine(wednesday, _t(end))
        slots = slot_starts(start_at, end_at)
        if patient is None or appointment_repo.find_taken_slots(doctor.id, slots):
            continue
        appointment_repo.create_with_slots(
            AppointmentModel(
                doctor_id=doctor.id, patient_id=patient.id, start_at=start_at, end_at=end_at,
                reason=reason, status=AppointmentStatus.PLANNED,
                created_by_user_id=receptionist.id if receptionist else None,
            ),
            slots,
        )
    DoctorService(db).set_sick_days(
        doctor.id, SickDaysChange(date_from=wednesday, date_to=wednesday + timedelta(days=1)), admin
    )
    logger.info("Seed: vytvořena demo nemoc MUDr. Veselé")
