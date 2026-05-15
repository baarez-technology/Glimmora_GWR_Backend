from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MagicLinkVerifyRequest(BaseModel):
    token: str


class MFAVerifyRequest(BaseModel):
    code: str
    temp_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


class TempTokenResponse(BaseModel):
    temp_token: str
    requires_mfa: bool = True


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    full_name: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "organizer"
