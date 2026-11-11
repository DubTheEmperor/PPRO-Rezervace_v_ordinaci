"""Spolehlivost pacienta (FP5) – čistá doménová logika bez přístupu k databázi.

Skóre = počet termínů zrušených pacientem + počet nedostavení za posuvné okno
posledních `WINDOW_MONTHS` měsíců (podle data termínu). Zrušení ze strany ordinace
se nepočítá – pacient za ně nemůže. Pozdní zrušení (méně než `LATE_CANCEL_HOURS`
před začátkem) se pouze eviduje pro informaci, na barvu vliv nemá.
"""
import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional, Tuple
from src.business.scheduling import LOCAL_TZ

WINDOW_MONTHS = 12
LATE_CANCEL_HOURS = 24
# Prahy barev: 0–1 zelená, 2–3 žlutá, 4 a více červená
YELLOW_FROM = 2
RED_FROM = 4

LEVEL_GREEN = "GREEN"
LEVEL_YELLOW = "YELLOW"
LEVEL_RED = "RED"

EVENT_CANCELLED = "CANCELLED_BY_PATIENT"
EVENT_NO_SHOW = "NO_SHOW"


@dataclass(frozen=True)
class Reliability:
    cancelled: int = 0
    no_show: int = 0
    late: int = 0

    @property
    def score(self) -> int:
        return self.cancelled + self.no_show

    @property
    def level(self) -> str:
        return level_for(self.score)

    @property
    def window_months(self) -> int:
        return WINDOW_MONTHS


def level_for(score: int) -> str:
    if score >= RED_FROM:
        return LEVEL_RED
    if score >= YELLOW_FROM:
        return LEVEL_YELLOW
    return LEVEL_GREEN


def window_start(now: datetime, months: int = WINDOW_MONTHS) -> datetime:
    """Začátek posuvného okna – stejný den o `months` měsíců dříve (31. → konec měsíce)."""
    month_index = now.year * 12 + (now.month - 1) - months
    year, month = divmod(month_index, 12)
    month += 1
    day = min(now.day, calendar.monthrange(year, month)[1])
    return now.replace(year=year, month=month, day=day)


def to_local_naive(value: datetime) -> datetime:
    """Čas s časovou zónou (např. UTC z DB) převede na naivní lokální čas ordinace."""
    if value.tzinfo is not None:
        return value.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return value


def is_late(cancelled_at: Optional[datetime], start_at: datetime) -> bool:
    """Zrušení méně než `LATE_CANCEL_HOURS` před začátkem termínu."""
    if cancelled_at is None:
        return False
    return start_at - to_local_naive(cancelled_at) < timedelta(hours=LATE_CANCEL_HOURS)


def evaluate(events: Iterable[Tuple[str, datetime, Optional[datetime]]]) -> Reliability:
    """Spočítá spolehlivost z událostí (stav, začátek termínu, čas zrušení)."""
    cancelled = no_show = late = 0
    for status, start_at, cancelled_at in events:
        if status == EVENT_CANCELLED:
            cancelled += 1
            if is_late(cancelled_at, start_at):
                late += 1
        elif status == EVENT_NO_SHOW:
            no_show += 1
    return Reliability(cancelled=cancelled, no_show=no_show, late=late)
