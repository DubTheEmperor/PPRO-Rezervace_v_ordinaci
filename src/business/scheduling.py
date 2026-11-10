"""Čistá doménová logika plánování termínů (bez závislosti na databázi).

Model času: pevná mřížka 15minutových slotů (otevřený bod 1). Rezervace zabírá
1 až MAX_SLOTS_PER_APPOINTMENT po sobě jdoucích slotů a musí celá ležet v jednom
bloku ordinačních hodin lékaře. Všechny časy jsou naivní lokální čas ordinace.
"""
from datetime import datetime, time, timedelta
from typing import Iterable, List, Sequence, Tuple
from zoneinfo import ZoneInfo

SLOT_MINUTES = 15
SLOT_DELTA = timedelta(minutes=SLOT_MINUTES)
MAX_SLOTS_PER_APPOINTMENT = 16  # 4 hodiny
LOCAL_TZ = ZoneInfo("Europe/Prague")

TimeBlock = Tuple[time, time]


def local_now() -> datetime:
    """Aktuální lokální čas ordinace jako naivní datetime."""
    return datetime.now(LOCAL_TZ).replace(tzinfo=None, microsecond=0)


def is_aligned(value: datetime | time) -> bool:
    """Leží čas přesně na hranici 15minutového slotu?"""
    return value.minute % SLOT_MINUTES == 0 and value.second == 0 and value.microsecond == 0


def slot_count(start: datetime, end: datetime) -> int:
    return int((end - start) / SLOT_DELTA)


def slot_starts(start: datetime, end: datetime) -> List[datetime]:
    """Rozpad intervalu [start, end) na začátky jednotlivých 15min slotů."""
    result = []
    current = start
    while current < end:
        result.append(current)
        current += SLOT_DELTA
    return result


def fits_office_hours(blocks_for_weekday: Iterable[TimeBlock], start: datetime, end: datetime) -> bool:
    """Interval musí celý ležet v jednom bloku ordinačních hodin téhož dne.

    Rezervace tedy nesmí přesahovat přes přestávku mezi bloky (např. polední pauzu).
    """
    if start.date() != end.date() or start >= end:
        return False
    start_t, end_t = start.time(), end.time()
    return any(b_start <= start_t and end_t <= b_end for b_start, b_end in blocks_for_weekday)


def validate_blocks(blocks: Sequence[Tuple[int, time, time]]) -> List[str]:
    """Validace týdenních bloků (weekday, start, end). Vrací seznam chybových hlášek."""
    errors: List[str] = []
    by_day: dict[int, List[TimeBlock]] = {}
    for weekday, start, end in blocks:
        if not 0 <= weekday <= 6:
            errors.append(f"Neplatný den v týdnu: {weekday}.")
            continue
        if not (is_aligned(start) and is_aligned(end)):
            errors.append(
                f"Časy {start:%H:%M}–{end:%H:%M} musí být zarovnané na {SLOT_MINUTES} minut."
            )
        if start >= end:
            errors.append(f"Blok {start:%H:%M}–{end:%H:%M} musí začínat dříve, než končí.")
        by_day.setdefault(weekday, []).append((start, end))

    for weekday, day_blocks in by_day.items():
        ordered = sorted(day_blocks)
        for (s1, e1), (s2, e2) in zip(ordered, ordered[1:]):
            if s2 < e1:
                errors.append(
                    f"Bloky {s1:%H:%M}–{e1:%H:%M} a {s2:%H:%M}–{e2:%H:%M} se ve stejném dni překrývají."
                )
    return errors

