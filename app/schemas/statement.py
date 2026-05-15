from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel


class StatementSubmit(BaseModel):
    fields: Dict[str, Any]  # flexible statement fields
    signature_png: Optional[str] = None  # base64 encoded PNG


class StatementOut(BaseModel):
    id: str
    attempt_id: str
    witness_id: Optional[str] = None
    steward_id: Optional[str] = None
    kind: str
    fields: Optional[Dict[str, Any]] = None
    pdf_s3_key: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PDFDownloadResponse(BaseModel):
    url: str
    expires_in: int = 300  # seconds
