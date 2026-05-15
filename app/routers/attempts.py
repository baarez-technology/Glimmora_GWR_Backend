import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.attempt import Attempt
from app.models.user import User
from app.models.witness import Witness
from app.models.evidence import Evidence
from app.models.statement import Statement
from app.schemas.attempt import AttemptCreate, AttemptUpdate, AttemptOut, SubmissionHealth
from app.services.audit_service import write_audit
from app.services.gwr_logic import compute_submission_health, AttemptHealthInput, compute_logbook, LogbookRow

router = APIRouter(prefix="/attempts", tags=["attempts"])


def _gen_ref() -> str:
    return f"GWR-{uuid.uuid4().hex[:8].upper()}"


@router.get("", response_model=List[AttemptOut])
async def list_attempts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "organizer":
        result = await db.execute(select(Attempt).where(Attempt.organizer_id == user.id))
    else:
        result = await db.execute(select(Attempt))
    return result.scalars().all()


@router.post("", response_model=AttemptOut, status_code=201)
async def create_attempt(
    body: AttemptCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attempt = Attempt(
        id=str(uuid.uuid4()),
        application_ref=_gen_ref(),
        record_title=body.record_title,
        organizer_id=user.id,
        category=body.category,
        description=body.description,
        attempt_date=body.attempt_date,
        location=body.location,
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    await write_audit(db, "attempt.created", actor_id=user.id, target_type="attempt", target_id=attempt.id)
    return attempt


@router.get("/{attempt_id}", response_model=AttemptOut)
async def get_attempt(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Attempt).where(Attempt.id == attempt_id))
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return attempt


@router.patch("/{attempt_id}", response_model=AttemptOut)
async def update_attempt(
    attempt_id: str,
    body: AttemptUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Attempt).where(Attempt.id == attempt_id))
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(attempt, field, value)

    await db.commit()
    await db.refresh(attempt)
    await write_audit(db, "attempt.updated", actor_id=user.id, target_type="attempt", target_id=attempt_id)
    return attempt


@router.get("/{attempt_id}/health", response_model=SubmissionHealth)
async def get_health(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Attempt).where(Attempt.id == attempt_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Attempt not found")

    witnesses = (await db.execute(select(Witness).where(Witness.attempt_id == attempt_id))).scalars().all()
    evidence = (await db.execute(select(Evidence).where(Evidence.attempt_id == attempt_id))).scalars().all()
    statements = (await db.execute(select(Statement).where(Statement.attempt_id == attempt_id))).scalars().all()

    from app.models.activity import ActivityRow, RestRow
    act_rows = (await db.execute(select(ActivityRow).where(ActivityRow.attempt_id == attempt_id))).scalars().all()
    rest_rows = (await db.execute(select(RestRow).where(RestRow.attempt_id == attempt_id))).scalars().all()

    logbook = compute_logbook(
        [LogbookRow("activity", r.sequence, r.start_hhmm, r.end_hhmm, r.notes) for r in act_rows],
        [LogbookRow("rest", r.sequence, r.start_hhmm, r.end_hhmm, r.notes) for r in rest_rows],
    )

    data = AttemptHealthInput(
        witness_count=len(witnesses),
        witness_completed_count=sum(1 for w in witnesses if w.status == "completed"),
        evidence_count=len(evidence),
        evidence_indexed_count=sum(1 for e in evidence if e.status == "indexed"),
        statement_count=len(statements),
        logbook_violations=logbook.violations,
    )
    return compute_submission_health(data)
