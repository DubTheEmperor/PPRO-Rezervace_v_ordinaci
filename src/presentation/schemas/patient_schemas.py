import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


VALID_INSURANCE_CODES = {"111", "201", "205", "207", "209", "211", "213"}


class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50, description="Křestní jméno")
    last_name: str = Field(..., min_length=2, max_length=50, description="Příjmení")
    birth_year: int = Field(..., ge=1900, le=2026, description="Rok narození")
    phone_number: str = Field(..., min_length=9, max_length=20, description="Telefonní číslo")
    insurance_number: str = Field(..., min_length=9, max_length=20, description="Číslo pojištěnce / rodné číslo")
    insurance_company_code: str = Field(..., min_length=3, max_length=10, description="Kód zdravotní pojišťovny (např. 111)")
    notes: Optional[str] = Field(None, max_length=1000, description="Interní poznámka k pacientovi")
    is_active: bool = Field(default=True, description="Aktivní záznam pacienta")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^(\+420|\+421)?\d{9}$", cleaned):
            raise ValueError("Telefonní číslo musí obsahovat 9 číslic (volitelně s předvolbou +420 nebo +421).")
        return cleaned

    @field_validator("insurance_number")
    @classmethod
    def validate_insurance_number(cls, v: str) -> str:
        cleaned = re.sub(r"[\s/]", "", v)
        if not re.match(r"^\d{9,10}$", cleaned):
            raise ValueError("Číslo pojištěnce musí obsahovat 9 nebo 10 číslic (rodné číslo).")
        return cleaned

    @field_validator("insurance_company_code")
    @classmethod
    def validate_insurance_company(cls, v: str) -> str:
        code = v.strip()
        if code not in VALID_INSURANCE_CODES:
            raise ValueError(
                f"Neplatný kód zdravotní pojišťovny '{code}'. Povolené kódy: {', '.join(sorted(VALID_INSURANCE_CODES))}."
            )
        return code


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    birth_year: Optional[int] = Field(None, ge=1900, le=2026)
    phone_number: Optional[str] = Field(None, min_length=9, max_length=20)
    insurance_number: Optional[str] = Field(None, min_length=9, max_length=20)
    insurance_company_code: Optional[str] = Field(None, min_length=3, max_length=10)
    notes: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^(\+420|\+421)?\d{9}$", cleaned):
            raise ValueError("Telefonní číslo musí obsahovat 9 číslic (volitelně s předvolbou +420 nebo +421).")
        return cleaned

    @field_validator("insurance_number")
    @classmethod
    def validate_insurance_number(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = re.sub(r"[\s/]", "", v)
        if not re.match(r"^\d{9,10}$", cleaned):
            raise ValueError("Číslo pojištěnce musí obsahovat 9 nebo 10 číslic (rodné číslo).")
        return cleaned

    @field_validator("insurance_company_code")
    @classmethod
    def validate_insurance_company(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        code = v.strip()
        if code not in VALID_INSURANCE_CODES:
            raise ValueError(
                f"Neplatný kód zdravotní pojišťovny '{code}'. Povolené kódy: {', '.join(sorted(VALID_INSURANCE_CODES))}."
            )
        return code


class PatientResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    birth_year: int
    phone_number: str
    insurance_number: str
    insurance_company_code: str
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientListResponse(BaseModel):
    items: List[PatientResponse]
    total: int
    skip: int
    limit: int
