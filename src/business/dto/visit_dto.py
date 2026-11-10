"""Vstupní DTO pro číselník výkonů a záznam o návštěvě."""
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

MAX_QUANTITY = 99


class ProcedureCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=10, description="Kód výkonu")
    name: str = Field(..., min_length=2, max_length=200, description="Název výkonu")
    points: int = Field(..., ge=0, le=100000, description="Bodové ohodnocení za 1 provedení")
    is_active: bool = True

    @field_validator("code", "name")
    @classmethod
    def strip(cls, v: str) -> str:
        return v.strip()


class ProcedureUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    points: Optional[int] = Field(None, ge=0, le=100000)
    is_active: Optional[bool] = None


class VisitItemInput(BaseModel):
    procedure_id: int
    quantity: int = Field(1, ge=1, le=MAX_QUANTITY, description="Počet provedení / aplikací")


class VisitUpdate(BaseModel):
    clinical_note: Optional[str] = Field(None, max_length=5000, description="Klinická poznámka")
    items: List[VisitItemInput] = Field(default_factory=list, description="Kompletní seznam provedených výkonů")
