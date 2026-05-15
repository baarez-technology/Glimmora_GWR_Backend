from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class CommentCreate(BaseModel):
    body: str
    parent_id: Optional[str] = None


class CommentOut(BaseModel):
    id: str
    attempt_id: str
    author_id: str
    body: str
    parent_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
