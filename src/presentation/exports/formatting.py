"""Společné formátování hodnot výkazu pro exporty (české zvyklosti)."""
import re
import unicodedata
from datetime import datetime
from src.business.reports import MonthlyReport, UNFINISHED_DRAFT


def fmt_points(value: int) -> str:
    """1047 → '1 047' (nezlomitelná mezera jako oddělovač tisíců)."""
    return f"{value:,}".replace(",", " ")


def plural(count: int, one: str, few: str, many: str) -> str:
    """České skloňování podle počtu: 1 návštěva, 2 návštěvy, 5 návštěv."""
    if count == 1:
        word = one
    elif 2 <= count <= 4:
        word = few
    else:
        word = many
    return f"{count} {word}"


def visits_label(count: int) -> str:
    return plural(count, "návštěva", "návštěvy", "návštěv")


def patients_label(count: int) -> str:
    return plural(count, "pacient", "pacienti", "pacientů")


def items_label(count: int) -> str:
    return plural(count, "výkon", "výkony", "výkonů")


def fmt_date(value: datetime) -> str:
    return value.strftime("%d.%m.%Y")


def fmt_datetime(value: datetime) -> str:
    return value.strftime("%d.%m.%Y %H:%M")


def unfinished_label(state: str) -> str:
    return "rozpracovaný záznam" if state == UNFINISHED_DRAFT else "bez záznamu návštěvy"


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    # Titul (MUDr.) do názvu souboru nepatří – použije se příjmení
    words = [w for w in re.split(r"\s+", ascii_text) if w and not w.endswith(".")]
    surname = words[-1] if words else "lekar"
    return re.sub(r"[^a-z0-9]+", "-", surname.lower()).strip("-") or "lekar"


def report_filename(report: MonthlyReport, extension: str) -> str:
    """Např. vykaz_hruba_2026-10_111.pdf"""
    parts = ["vykaz", _slug(report.doctor.full_name), report.month_key]
    if report.insurance_code:
        parts.append(report.insurance_code)
    return "_".join(parts) + f".{extension}"
