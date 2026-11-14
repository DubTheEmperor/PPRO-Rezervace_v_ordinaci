"""Paleta barev lékařů (rychlé odlišení lékaře v kalendáři a seznamech).

Jediný zdroj pravdy pro validaci barvy lékaře. Barvy jsou tlumené, aby ladily
s paletou ordinace, liší se od akcentu (#167D8D), růžové (obsazeno / nemoc)
i jantarové (jiné pracoviště) a mají s bílým textem kontrast alespoň 4.5 : 1
(avatar s iniciálami). Stejný seznam zobrazuje formulář lékaře v UI.
"""
from typing import Iterable, List, Tuple

DOCTOR_COLORS: List[Tuple[str, str]] = [
    ("#3E5C9A", "břidlicově modrá"),
    ("#5F7F3B", "mechově zelená"),
    ("#7A4E8C", "švestková"),
    ("#8A6D3B", "oříšková"),
    ("#4F5B66", "grafitová"),
]

PALETTE = [hex_ for hex_, _ in DOCTOR_COLORS]
DEFAULT_DOCTOR_COLOR = PALETTE[0]


def normalize_color(value: str) -> str:
    return value.strip().upper()


def is_palette_color(value: str) -> bool:
    return normalize_color(value) in PALETTE


def next_free_color(used: Iterable[str]) -> str:
    """První barva palety, kterou zatím nemá žádný lékař.

    Když jsou obsazené všechny, pokračuje se cyklicky podle počtu lékařů.
    """
    used_list = [normalize_color(c) for c in used if c]
    for color in PALETTE:
        if color not in used_list:
            return color
    return PALETTE[len(used_list) % len(PALETTE)]
