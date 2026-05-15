from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


class StewardCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    organisation: Optional[str] = None


class StewardUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    organisation: Optional[str] = None
    status: Optional[str] = None


class StewardOut(BaseModel):
    id: str
    attempt_id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    organisation: Optional[str] = None
    status: str
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
