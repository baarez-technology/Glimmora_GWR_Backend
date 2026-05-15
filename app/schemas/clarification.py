from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ClarificationCreate(BaseModel):
    subject: str
    witness_id: Optional[str] = None
    body: str  # first message


class ClarificationUpdate(BaseModel):
    status: Optional[str] = None  # open | responded | closed


class MessageCreate(BaseModel):
    body: str


class MessageOut(BaseModel):
    id: str
    clarification_id: str
    author_id: str
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ClarificationOut(BaseModel):
    id: str
    attempt_id: str
    witness_id: Optional[str] = None
    raised_by_id: Optional[str] = None
    subject: str
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None
    messages: list[MessageOut] = []

    model_config = {"from_attributes": True}
