from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from src.infrastructure.models.user_model import UserRole



class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Uživatelské jméno")
    email: EmailStr = Field(..., description="E-mailová adresa")
    full_name: str = Field(..., min_length=2, max_length=100, description="Celé jméno a příjmení")
    role: UserRole = Field(default=UserRole.RECEPTIONIST, description="Role v systému")
    is_active: bool = Field(default=True, description="Stav aktivity účtu")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100, description="Heslo uživatele (min. 6 znaků)")


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100, description="Nové heslo (volitelné)")


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    skip: int
    limit: int
