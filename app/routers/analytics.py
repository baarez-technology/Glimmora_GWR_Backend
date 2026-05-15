from pydantic import BaseModel
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_adjudicator
from app.models.attempt import Attempt
from app.models.witness import Witness
from app.models.evidence import Evidence
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


class OverviewStats(BaseModel):
    total_attempts: int
    by_status: dict
    total_witnesses: int
    total_evidence: int
    evidence_by_type: dict


@router.get("/overview", response_model=OverviewStats)
async def overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_adjudicator),
):
    total_attempts = (await db.execute(select(func.count(Attempt.id)))).scalar_one()
    total_witnesses = (await db.execute(select(func.count(Witness.id)))).scalar_one()
    total_evidence = (await db.execute(select(func.count(Evidence.id)))).scalar_one()

    attempts = (await db.execute(select(Attempt.status))).scalars().all()
    by_status: dict = {}
    for s in attempts:
        by_status[s] = by_status.get(s, 0) + 1

    evidence_list = (await db.execute(select(Evidence.type))).scalars().all()
    evidence_by_type: dict = {}
    for t in evidence_list:
        evidence_by_type[t] = evidence_by_type.get(t, 0) + 1

    return OverviewStats(
        total_attempts=total_attempts,
        by_status=by_status,
        total_witnesses=total_witnesses,
        total_evidence=total_evidence,
        evidence_by_type=evidence_by_type,
    )
