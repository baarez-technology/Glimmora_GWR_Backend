from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class EvidenceInitRequest(BaseModel):
    type: str  # video | image | document | audio | link
    file_name: Optional[str] = None
    file_url: Optional[str] = None  # for link type
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    description: Optional[str] = None


class EvidenceCompleteRequest(BaseModel):
    etag: Optional[str] = None
    sha256: Optional[str] = None


class UploadUrlResponse(BaseModel):
    evidence_id: str
    upload_url: Optional[str] = None  # pre-signed S3 URL; null for link type
    upload_fields: Optional[dict] = None


class EvidenceOut(BaseModel):
    id: str
    attempt_id: str
    type: str
    status: str
    file_name: Optional[str] = None
    s3_key: Optional[str] = None
    file_url: Optional[str] = None
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    duration_seconds: Optional[float] = None
    ai_confidence: Optional[float] = None
    tags: Optional[List[str]] = None
    transcript: Optional[str] = None
    description: Optional[str] = None
    sha256: Optional[str] = None
    uploaded_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
