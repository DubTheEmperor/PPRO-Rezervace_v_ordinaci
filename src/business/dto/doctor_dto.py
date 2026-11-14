"""Vstupní DTO pro správu lékařů a ordinačních hodin."""
from datetime import date, time
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from src.business.doctor_colors import DOCTOR_COLORS, is_palette_color, normalize_color

COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"
ICP_PATTERN = r"^\d{8}$"
SPECIALTY_CODE_PATTERN = r"^\d{3}$"


class OfficeHoursBlock(BaseModel):
    weekday: int = Field(..., ge=0, le=6, description="Den v týdnu (0 = pondělí … 6 = neděle)")
    start_time: time = Field(..., description="Začátek bloku (HH:MM, zarovnáno na 15 min)")
    end_time: time = Field(..., description="Konec bloku (HH:MM, zarovnáno na 15 min)")
    kind: Literal["OFFICE", "ELSEWHERE"] = Field(
        "OFFICE", description="OFFICE = ordinuje v ordinaci, ELSEWHERE = jiné pracoviště (nelze rezervovat)"
    )
    location: Optional[str] = Field(
        None, max_length=100, description="Kde lékař ordinuje (povinné u jiného pracoviště)"
    )

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def check_location(self) -> "OfficeHoursBlock":
        location = (self.location or "").strip()
        if self.kind == "ELSEWHERE":
            if not location:
                raise ValueError("Uveďte, kde lékař v tuto dobu ordinuje (jiné pracoviště).")
            self.location = location
        else:
            self.location = None
        return self


class OfficeHoursUpdate(BaseModel):
    blocks: List[OfficeHoursBlock] = Field(default_factory=list, description="Kompletní týdenní rozvrh")


def _palette_color(value: Optional[str]) -> Optional[str]:
    """Barva lékaře musí být z palety (tlumené barvy ladící s rozhraním)."""
    if value is None:
        return None
    if not is_palette_color(value):
        names = ", ".join(f"{hex_} ({name})" for hex_, name in DOCTOR_COLORS)
        raise ValueError(f"Barva lékaře musí být jedna z barev palety: {names}.")
    return normalize_color(value)


class DoctorCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Celé jméno včetně titulu")
    color: Optional[str] = Field(
        None, pattern=COLOR_PATTERN,
        description="Barva lékaře z palety; bez uvedení se přidělí první volná barva",
    )
    user_id: Optional[int] = Field(None, description="Propojený uživatelský účet s rolí DOCTOR")
    icp: Optional[str] = Field(None, pattern=ICP_PATTERN, description="IČP – identifikační číslo pracoviště (8 číslic)")
    specialty_code: Optional[str] = Field(None, pattern=SPECIALTY_CODE_PATTERN, description="Kód odbornosti (3 číslice)")
    is_active: bool = True

    @field_validator("color")
    @classmethod
    def check_palette_color(cls, value: Optional[str]) -> Optional[str]:
        return _palette_color(value)


class DoctorUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    color: Optional[str] = Field(None, pattern=COLOR_PATTERN)
    user_id: Optional[int] = None
    icp: Optional[str] = Field(None, pattern=ICP_PATTERN)
    specialty_code: Optional[str] = Field(None, pattern=SPECIALTY_CODE_PATTERN)
    is_active: Optional[bool] = None

    @field_validator("color")
    @classmethod
    def check_palette_color(cls, value: Optional[str]) -> Optional[str]:
        return _palette_color(value)


class SickDaysChange(BaseModel):
    """Označení (sick=True) nebo odznačení (sick=False) celých dnů nemoci lékaře."""
    date_from: date = Field(..., description="První den (včetně)")
    date_to: date = Field(..., description="Poslední den (včetně)")
    sick: bool = Field(True, description="True = lékař je nemocný, False = nemoc v těchto dnech zrušit")
