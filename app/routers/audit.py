from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_adjudicator
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(tags=["audit"])


class AuditLogOut(BaseModel):
    id: str
    actor_id: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    ip: Optional[str] = None
    ts: datetime
    hash: Optional[str] = None

    model_config = {"from_attributes": True}


@router.get("/audit", response_model=List[AuditLogOut])
async def get_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_adjudicator),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.ts.desc()).offset(offset).limit(page_size)
    )
    return result.scalars().all()
