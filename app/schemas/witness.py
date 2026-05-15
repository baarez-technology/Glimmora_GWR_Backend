from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


class WitnessCreate(BaseModel):
    role: str  # specialist | independent | timekeeper
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    organisation: Optional[str] = None
    expertise: Optional[str] = None


class WitnessBulkCreate(BaseModel):
    witnesses: list[WitnessCreate]


class WitnessUpdate(BaseModel):
    role: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    organisation: Optional[str] = None
    expertise: Optional[str] = None
    status: Optional[str] = None


class WitnessOut(BaseModel):
    id: str
    attempt_id: str
    role: str
    status: str
    full_name: str
    email: str
    phone: Optional[str] = None
    organisation: Optional[str] = None
    expertise: Optional[str] = None
    invited_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
