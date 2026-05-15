from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class AIAlertOut(BaseModel):
    id: str
    attempt_id: str
    severity: str  # critical | warning | info
    title: str
    description: str
    recommendation: Optional[str] = None
    evidence_id: Optional[str] = None
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TimelineEvent(BaseModel):
    timestamp: str
    title: str
    description: Optional[str] = None
    evidence_ids: list[str] = []
    type: str = "milestone"


class ProcessingStatus(BaseModel):
    attempt_id: str
    total_evidence: int
    indexed: int
    processing: int
    failed: int
    workers: dict[str, str]  # worker_name -> status


class CoverLetterExpandRequest(BaseModel):
    current_text: str
    context_hint: Optional[str] = None


class CoverLetterExpandResponse(BaseModel):
    expanded_text: str
