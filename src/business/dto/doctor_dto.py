"""Vstupní DTO pro správu lékařů a ordinačních hodin."""
from datetime import time
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"
ICP_PATTERN = r"^\d{8}$"
SPECIALTY_CODE_PATTERN = r"^\d{3}$"


class OfficeHoursBlock(BaseModel):
    weekday: int = Field(..., ge=0, le=6, description="Den v týdnu (0 = pondělí … 6 = neděle)")
    start_time: time = Field(..., description="Začátek bloku (HH:MM, zarovnáno na 15 min)")
    end_time: time = Field(..., description="Konec bloku (HH:MM, zarovnáno na 15 min)")

    model_config = ConfigDict(from_attributes=True)


class OfficeHoursUpdate(BaseModel):
    blocks: List[OfficeHoursBlock] = Field(default_factory=list, description="Kompletní týdenní rozvrh")


class DoctorCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Celé jméno včetně titulu")
    specialization: Optional[str] = Field(None, max_length=100)
    color: str = Field("#0284c7", pattern=COLOR_PATTERN, description="Barva lékaře v kalendáři")
    user_id: Optional[int] = Field(None, description="Propojený uživatelský účet s rolí DOCTOR")
    icp: Optional[str] = Field(None, pattern=ICP_PATTERN, description="IČP – identifikační číslo pracoviště (8 číslic)")
    specialty_code: Optional[str] = Field(None, pattern=SPECIALTY_CODE_PATTERN, description="Kód odbornosti (3 číslice)")
    is_active: bool = True


class DoctorUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    specialization: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, pattern=COLOR_PATTERN)
    user_id: Optional[int] = None
    icp: Optional[str] = Field(None, pattern=ICP_PATTERN)
    specialty_code: Optional[str] = Field(None, pattern=SPECIALTY_CODE_PATTERN)
    is_active: Optional[bool] = None
