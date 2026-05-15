import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.clarification import Clarification, ClarificationMessage
from app.models.user import User
from app.schemas.clarification import ClarificationCreate, ClarificationUpdate, MessageCreate, ClarificationOut, MessageOut

router = APIRouter(tags=["clarifications"])


@router.post("/attempts/{attempt_id}/clarifications", response_model=ClarificationOut, status_code=201)
async def create_clarification(
    attempt_id: str,
    body: ClarificationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    clarif = Clarification(
        id=str(uuid.uuid4()),
        attempt_id=attempt_id,
        witness_id=body.witness_id,
        raised_by_id=user.id,
        subject=body.subject,
    )
    db.add(clarif)
    await db.flush()

    msg = ClarificationMessage(
        id=str(uuid.uuid4()),
        clarification_id=clarif.id,
        author_id=user.id,
        body=body.body,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(clarif)
    await db.refresh(msg)

    return ClarificationOut(
        id=clarif.id,
        attempt_id=clarif.attempt_id,
        witness_id=clarif.witness_id,
        raised_by_id=clarif.raised_by_id,
        subject=clarif.subject,
        status=clarif.status,
        opened_at=clarif.opened_at,
        messages=[MessageOut(
            id=msg.id,
            clarification_id=msg.clarification_id,
            author_id=msg.author_id,
            body=msg.body,
            created_at=msg.created_at,
        )],
    )


@router.patch("/clarifications/{clarif_id}", response_model=ClarificationOut)
async def update_clarification(
    clarif_id: str,
    body: ClarificationUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Clarification).where(Clarification.id == clarif_id))
    clarif = result.scalar_one_or_none()
    if not clarif:
        raise HTTPException(status_code=404, detail="Clarification not found")

    if body.status:
        clarif.status = body.status
        if body.status == "closed":
            clarif.closed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(clarif)

    msgs = (await db.execute(
        select(ClarificationMessage).where(ClarificationMessage.clarification_id == clarif_id)
    )).scalars().all()

    return ClarificationOut(
        id=clarif.id,
        attempt_id=clarif.attempt_id,
        witness_id=clarif.witness_id,
        raised_by_id=clarif.raised_by_id,
        subject=clarif.subject,
        status=clarif.status,
        opened_at=clarif.opened_at,
        closed_at=clarif.closed_at,
        messages=[MessageOut(**m.__dict__) for m in msgs],
    )


@router.post("/clarifications/{clarif_id}/messages", response_model=MessageOut, status_code=201)
async def add_message(
    clarif_id: str,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Clarification).where(Clarification.id == clarif_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Clarification not found")

    msg = ClarificationMessage(
        id=str(uuid.uuid4()),
        clarification_id=clarif_id,
        author_id=user.id,
        body=body.body,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
