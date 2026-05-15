from typing import Optional, List
from pydantic import BaseModel

from fastapi import APIRouter, Depends
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.evidence import Evidence
from app.models.witness import Witness
from app.models.user import User

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    q: str
    attempt_id: Optional[str] = None


class SearchResult(BaseModel):
    type: str
    id: str
    title: str
    snippet: Optional[str] = None
    attempt_id: Optional[str] = None


@router.post("/search", response_model=List[SearchResult])
async def search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    results = []
    q = f"%{body.q}%"

    # Evidence keyword search
    ev_query = select(Evidence).where(
        or_(
            Evidence.file_name.ilike(q),
            Evidence.description.ilike(q),
            Evidence.transcript.ilike(q),
        )
    )
    if body.attempt_id:
        ev_query = ev_query.where(Evidence.attempt_id == body.attempt_id)

    for e in (await db.execute(ev_query)).scalars().all():
        results.append(SearchResult(
            type="evidence",
            id=e.id,
            title=e.file_name or e.type,
            snippet=e.description,
            attempt_id=e.attempt_id,
        ))

    # Witness keyword search
    w_query = select(Witness).where(
        or_(
            Witness.full_name.ilike(q),
            Witness.email.ilike(q),
            Witness.organisation.ilike(q),
        )
    )
    if body.attempt_id:
        w_query = w_query.where(Witness.attempt_id == body.attempt_id)

    for w in (await db.execute(w_query)).scalars().all():
        results.append(SearchResult(
            type="witness",
            id=w.id,
            title=w.full_name,
            snippet=w.organisation,
            attempt_id=w.attempt_id,
        ))

    return results
