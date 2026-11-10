"""Fasáda byznys vrstvy pro prezentační vrstvu.

Prezentační vrstva importuje výhradně z `src.business` – typy a enumy datové
vrstvy, které potřebuje znát (role, stavy, entita přihlášeného uživatele,
databázová session pro dependency injection), dostává přes tento modul.
Tím je zachován striktně jednosměrný tok závislostí
Prezentace → Byznys → Infrastruktura.
"""
from src.infrastructure.database import get_db
from src.infrastructure.models.user_model import UserModel as User, UserRole
from src.infrastructure.models.appointment_model import AppointmentStatus
from src.infrastructure.models.visit_model import VisitStatus

__all__ = ["get_db", "User", "UserRole", "AppointmentStatus", "VisitStatus"]
