from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: str
    user_id: str
    title: str
    detail: Optional[str] = None
    tone: str
    link: Optional[str] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
