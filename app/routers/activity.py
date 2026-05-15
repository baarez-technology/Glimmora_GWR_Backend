import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.activity import ActivityRow, RestRow
from app.models.user import User
from app.schemas.activity import ActivityRowCreate, RestRowCreate, ActivityRowOut, RestRowOut, LogbookResponse
from app.services.gwr_logic import compute_logbook, LogbookRow

router = APIRouter(prefix="/attempts/{attempt_id}", tags=["logbook"])


@router.post("/activity-rows", response_model=ActivityRowOut, status_code=201)
async def add_activity_row(
    attempt_id: str,
    body: ActivityRowCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = ActivityRow(
        id=str(uuid.uuid4()),
        attempt_id=attempt_id,
        **body.model_dump(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.post("/rest-rows", response_model=RestRowOut, status_code=201)
async def add_rest_row(
    attempt_id: str,
    body: RestRowCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = RestRow(
        id=str(uuid.uuid4()),
        attempt_id=attempt_id,
        **body.model_dump(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/logbook", response_model=LogbookResponse)
async def get_logbook(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    act_rows = (await db.execute(select(ActivityRow).where(ActivityRow.attempt_id == attempt_id))).scalars().all()
    rest_rows = (await db.execute(select(RestRow).where(RestRow.attempt_id == attempt_id))).scalars().all()

    result = compute_logbook(
        [LogbookRow("activity", r.sequence, r.start_hhmm, r.end_hhmm, r.notes) for r in act_rows],
        [LogbookRow("rest", r.sequence, r.start_hhmm, r.end_hhmm, r.notes) for r in rest_rows],
    )

    return LogbookResponse(
        entries=result.entries,
        total_activity_minutes=result.total_activity_minutes,
        total_rest_minutes=result.total_rest_minutes,
        accrued_rest_minutes=result.accrued_rest_minutes,
        rest_balance_minutes=result.rest_balance_minutes,
        violations=result.violations,
    )
