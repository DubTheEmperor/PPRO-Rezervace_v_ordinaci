from pydantic import BaseModel, Field
from src.presentation.schemas.user_schemas import UserResponse


class LoginRequest(BaseModel):
    username: str = Field(..., description="Uživatelské jméno")
    password: str = Field(..., description="Heslo")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
