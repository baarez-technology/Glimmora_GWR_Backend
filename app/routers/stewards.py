import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.steward import Steward
from app.models.attempt import Attempt
from app.models.user import User
from app.schemas.steward import StewardCreate, StewardUpdate, StewardOut

router = APIRouter(prefix="/attempts/{attempt_id}/stewards", tags=["stewards"])


@router.get("", response_model=List[StewardOut])
async def list_stewards(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Steward).where(Steward.attempt_id == attempt_id))
    return result.scalars().all()


@router.post("", response_model=StewardOut, status_code=201)
async def create_steward(
    attempt_id: str,
    body: StewardCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Attempt).where(Attempt.id == attempt_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Attempt not found")

    steward = Steward(
        id=str(uuid.uuid4()),
        attempt_id=attempt_id,
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        organisation=body.organisation,
    )
    db.add(steward)
    await db.commit()
    await db.refresh(steward)
    return steward


@router.patch("/{steward_id}", response_model=StewardOut)
async def update_steward(
    attempt_id: str,
    steward_id: str,
    body: StewardUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Steward).where(Steward.id == steward_id, Steward.attempt_id == attempt_id)
    )
    steward = result.scalar_one_or_none()
    if not steward:
        raise HTTPException(status_code=404, detail="Steward not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(steward, field, value)

    await db.commit()
    await db.refresh(steward)
    return steward
