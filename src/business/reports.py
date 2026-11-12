"""Měsíční výkaz pro pojišťovny (FP7) – čistá doménová logika bez databáze.

Výkaz za kalendářní měsíc a lékaře obsahuje jen **uzavřené** návštěvy. Body se berou
ze snapshotu položky návštěvy (`points_per_unit` v okamžiku zápisu), takže pozdější
změna číselníku výkaz nezmění. Výkaz je členěný po zdravotních pojišťovnách
(každé pojišťovně se vykazuje zvlášť) s mezisoučty, souhrnem podle kódů výkonů
a celkovým součtem bodů.
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional, Tuple
from src.business.exceptions import BusinessRuleError
from src.business.insurance import INSURANCE_SHORT_NAMES, insurance_name

MONTH_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")

# Stav proběhlého termínu, který brání úplnosti výkazu
UNFINISHED_TO_RECORD = "TO_RECORD"  # termín proběhl, záznam návštěvy chybí
UNFINISHED_DRAFT = "DRAFT"          # záznam je rozpracovaný (neuzavřený)


@dataclass(frozen=True)
class ReportItem:
    code: str
    name: str
    quantity: int
    points_per_unit: int

    @property
    def total_points(self) -> int:
        return self.quantity * self.points_per_unit


@dataclass(frozen=True)
class ReportVisit:
    visit_id: int
    start_at: datetime
    patient_id: int
    patient_first_name: str
    patient_last_name: str
    patient_birth_year: int
    insurance_number: str
    insurance_code: str
    items: Tuple[ReportItem, ...]

    @property
    def patient_name(self) -> str:
        return f"{self.patient_last_name} {self.patient_first_name}"

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def total_points(self) -> int:
        return sum(item.total_points for item in self.items)


@dataclass(frozen=True)
class InsuranceSection:
    code: str
    name: str
    short_name: str
    visits: Tuple[ReportVisit, ...]

    @property
    def visit_count(self) -> int:
        return len(self.visits)

    @property
    def patient_count(self) -> int:
        return len({v.patient_id for v in self.visits})

    @property
    def item_count(self) -> int:
        return sum(v.item_count for v in self.visits)

    @property
    def total_points(self) -> int:
        return sum(v.total_points for v in self.visits)


@dataclass(frozen=True)
class ProcedureSummary:
    code: str
    name: str
    quantity: int
    total_points: int


@dataclass(frozen=True)
class UnfinishedVisit:
    appointment_id: int
    start_at: datetime
    patient_name: str
    state: str


@dataclass(frozen=True)
class PracticeInfo:
    name: str
    address: str
    icz: str


@dataclass(frozen=True)
class DoctorInfo:
    id: int
    full_name: str
    specialization: Optional[str]
    icp: Optional[str]
    specialty_code: Optional[str]


@dataclass(frozen=True)
class MonthlyReport:
    practice: PracticeInfo
    doctor: DoctorInfo
    year: int
    month: int
    period_start: datetime
    period_end: datetime
    insurance_code: Optional[str]
    generated_at: datetime
    generated_by: str
    period_complete: bool
    sections: Tuple[InsuranceSection, ...]
    procedure_summary: Tuple[ProcedureSummary, ...]
    unfinished: Tuple[UnfinishedVisit, ...] = field(default_factory=tuple)

    @property
    def period_label(self) -> str:
        return f"{self.month:02d}/{self.year}"

    @property
    def month_key(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def insurance_label(self) -> str:
        if self.insurance_code is None:
            return "všechny pojišťovny"
        return f"{self.insurance_code} – {insurance_name(self.insurance_code)}"

    @property
    def visit_count(self) -> int:
        return sum(s.visit_count for s in self.sections)

    @property
    def patient_count(self) -> int:
        return len({v.patient_id for s in self.sections for v in s.visits})

    @property
    def item_count(self) -> int:
        return sum(s.item_count for s in self.sections)

    @property
    def total_points(self) -> int:
        return sum(s.total_points for s in self.sections)


# --- Období -------------------------------------------------------------------------------

def parse_month(value: str) -> Tuple[int, int]:
    """Převede text 'RRRR-MM' na (rok, měsíc), jinak BusinessRuleError."""
    match = MONTH_PATTERN.match((value or "").strip())
    if not match:
        raise BusinessRuleError("Měsíc zadejte ve tvaru RRRR-MM (např. 2026-11).")
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12 or not 2000 <= year <= 2100:
        raise BusinessRuleError(f"Neplatný měsíc '{value}'.")
    return year, month


def month_bounds(year: int, month: int) -> Tuple[datetime, datetime]:
    """Interval [1. den 00:00, 1. den dalšího měsíce 00:00) v lokálním čase ordinace."""
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return start, end


def ensure_not_future(year: int, month: int, today: date) -> None:
    if (year, month) > (today.year, today.month):
        raise BusinessRuleError("Výkaz nelze vytvořit za měsíc, který ještě nezačal.")


# --- Sestavení výkazu -----------------------------------------------------------------------

def group_by_insurance(visits: Iterable[ReportVisit]) -> Tuple[InsuranceSection, ...]:
    """Rozdělí návštěvy do oddílů podle kódu pojišťovny (vzestupně), uvnitř podle času."""
    groups: Dict[str, List[ReportVisit]] = {}
    for visit in visits:
        groups.setdefault(visit.insurance_code, []).append(visit)
    return tuple(
        InsuranceSection(
            code=code,
            name=insurance_name(code),
            short_name=INSURANCE_SHORT_NAMES.get(code, code),
            visits=tuple(sorted(groups[code], key=lambda v: (v.start_at, v.visit_id))),
        )
        for code in sorted(groups)
    )


def summarize_procedures(visits: Iterable[ReportVisit]) -> Tuple[ProcedureSummary, ...]:
    """Souhrn podle kódů výkonů: celkový počet provedení a body, seřazeno podle kódu."""
    quantities: Dict[str, int] = {}
    points: Dict[str, int] = {}
    names: Dict[str, str] = {}
    for visit in visits:
        for item in visit.items:
            quantities[item.code] = quantities.get(item.code, 0) + item.quantity
            points[item.code] = points.get(item.code, 0) + item.total_points
            names.setdefault(item.code, item.name)
    return tuple(
        ProcedureSummary(code=code, name=names[code], quantity=quantities[code], total_points=points[code])
        for code in sorted(quantities)
    )


def build_monthly_report(
    *,
    practice: PracticeInfo,
    doctor: DoctorInfo,
    year: int,
    month: int,
    insurance_code: Optional[str],
    visits: Iterable[ReportVisit],
    unfinished: Iterable[UnfinishedVisit],
    now: datetime,
    generated_by: str,
) -> MonthlyReport:
    visits = list(visits)
    period_start, period_end = month_bounds(year, month)
    return MonthlyReport(
        practice=practice,
        doctor=doctor,
        year=year,
        month=month,
        period_start=period_start,
        period_end=period_end,
        insurance_code=insurance_code,
        generated_at=now,
        generated_by=generated_by,
        period_complete=now >= period_end,
        sections=group_by_insurance(visits),
        procedure_summary=summarize_procedures(visits),
        unfinished=tuple(sorted(unfinished, key=lambda u: u.start_at)),
    )
