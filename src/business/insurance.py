"""Číselník zdravotních pojišťoven v ČR (kód → název).

Jediný zdroj pravdy pro validaci kódu pojišťovny pacienta i pro hlavičky
oddílů měsíčního výkazu (FP7).
"""
from typing import Dict

INSURANCE_COMPANIES: Dict[str, str] = {
    "111": "Všeobecná zdravotní pojišťovna ČR",
    "201": "Vojenská zdravotní pojišťovna ČR",
    "205": "Česká průmyslová zdravotní pojišťovna",
    "207": "Oborová zdravotní poj. zam. bank, pojišťoven a stavebnictví",
    "209": "Zaměstnanecká pojišťovna Škoda",
    "211": "Zdravotní pojišťovna ministerstva vnitra ČR",
    "213": "Revírní bratrská pokladna, zdrav. pojišťovna",
}

# Zkratky pro úzké sloupce a výběrové seznamy
INSURANCE_SHORT_NAMES: Dict[str, str] = {
    "111": "VZP ČR",
    "201": "VoZP ČR",
    "205": "ČPZP",
    "207": "OZP",
    "209": "ZPŠ",
    "211": "ZPMV ČR",
    "213": "RBP",
}

VALID_INSURANCE_CODES = frozenset(INSURANCE_COMPANIES)


def insurance_name(code: str) -> str:
    return INSURANCE_COMPANIES.get(code, "Neznámá pojišťovna")
