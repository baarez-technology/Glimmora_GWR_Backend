from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel


class AttemptCreate(BaseModel):
    record_title: str
    category: Optional[str] = None
    description: Optional[str] = None
    attempt_date: Optional[str] = None
    location: Optional[str] = None


class AttemptUpdate(BaseModel):
    record_title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    attempt_date: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None


class AttemptOut(BaseModel):
    id: str
    application_ref: str
    record_title: str
    organizer_id: str
    status: str
    category: Optional[str] = None
    description: Optional[str] = None
    attempt_date: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubmissionHealth(BaseModel):
    score: int  # 0-100
    witnesses_ok: bool
    evidence_ok: bool
    logbook_ok: bool
    statements_ok: bool
    issues: list[str]
