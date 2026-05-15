from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ActivityRowCreate(BaseModel):
    sequence: int
    start_hhmm: str  # "HH:MM"
    end_hhmm: str
    activity_type: Optional[str] = None
    notes: Optional[str] = None
    witness1_id: Optional[str] = None
    witness2_id: Optional[str] = None


class RestRowCreate(BaseModel):
    sequence: int
    start_hhmm: str
    end_hhmm: str
    notes: Optional[str] = None
    witness1_id: Optional[str] = None
    witness2_id: Optional[str] = None


class ActivityRowOut(BaseModel):
    id: str
    attempt_id: str
    sequence: int
    start_hhmm: str
    end_hhmm: str
    activity_type: Optional[str] = None
    notes: Optional[str] = None
    witness1_id: Optional[str] = None
    witness2_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RestRowOut(BaseModel):
    id: str
    attempt_id: str
    sequence: int
    start_hhmm: str
    end_hhmm: str
    notes: Optional[str] = None
    witness1_id: Optional[str] = None
    witness2_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LogbookEntry(BaseModel):
    type: str  # "activity" | "rest"
    sequence: int
    start_hhmm: str
    end_hhmm: str
    duration_minutes: int
    notes: Optional[str] = None


class LogbookResponse(BaseModel):
    entries: list[LogbookEntry]
    total_activity_minutes: int
    total_rest_minutes: int
    accrued_rest_minutes: int
    rest_balance_minutes: int
    violations: list[str]
