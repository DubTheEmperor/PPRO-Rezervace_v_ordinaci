"""Čistá doménová logika nemoci lékaře (otevřený bod 5) – bez závislosti na databázi.

Nemoc se zadává po celých dnech. Měnit lze jen dnešek a budoucnost (minulost je
neměnná kvůli auditovatelnosti) a jedna operace smí pokrýt nejvýše MAX_RANGE_DAYS dní.
"""
from datetime import date, timedelta
from typing import Iterable, List, Tuple

MAX_RANGE_DAYS = 92

Period = Tuple[date, date]


def days_in_range(date_from: date, date_to: date) -> List[date]:
    """Všechny dny uzavřeného intervalu [date_from, date_to]."""
    return [date_from + timedelta(days=i) for i in range((date_to - date_from).days + 1)]


def validate_range(date_from: date, date_to: date, today: date) -> List[str]:
    """Validace rozsahu změny nemoci. Vrací seznam chybových hlášek."""
    errors: List[str] = []
    if date_to < date_from:
        errors.append("Konec období nemoci nesmí být před jeho začátkem.")
        return errors
    if date_from < today:
        errors.append("Nemoc nelze měnit zpětně – minulé dny jsou uzavřené.")
    if (date_to - date_from).days + 1 > MAX_RANGE_DAYS:
        errors.append(f"Najednou lze označit nejvýše {MAX_RANGE_DAYS} dní.")
    return errors


def merge_periods(days: Iterable[date]) -> List[Period]:
    """Sloučí jednotlivé dny do souvislých období (seřazeno od nejstaršího)."""
    periods: List[Period] = []
    for day in sorted(set(days)):
        if periods and periods[-1][1] + timedelta(days=1) == day:
            periods[-1] = (periods[-1][0], day)
        else:
            periods.append((day, day))
    return periods
