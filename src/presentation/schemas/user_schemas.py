from datetime import datetime
from typing import List
from pydantic import BaseModel, EmailStr, ConfigDict
from src.business.domain import UserRole


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
