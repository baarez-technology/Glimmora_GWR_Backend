import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.attempt import Attempt
from app.models.user import User
from app.models.witness import Witness
from app.schemas.witness import WitnessCreate, WitnessBulkCreate, WitnessUpdate, WitnessOut
from app.services.auth_service import create_magic_link_token
from app.services.email_service import send_magic_link
from app.services.audit_service import write_audit

router = APIRouter(prefix="/attempts/{attempt_id}/witnesses", tags=["witnesses"])


async def _get_attempt(attempt_id: str, db: AsyncSession) -> Attempt:
    result = await db.execute(select(Attempt).where(Attempt.id == attempt_id))
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return attempt


@router.get("", response_model=List[WitnessOut])
async def list_witnesses(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_attempt(attempt_id, db)
    result = await db.execute(select(Witness).where(Witness.attempt_id == attempt_id))
    return result.scalars().all()


@router.post("", response_model=WitnessOut, status_code=201)
async def invite_witness(
    attempt_id: str,
    body: WitnessCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attempt = await _get_attempt(attempt_id, db)
    token = create_magic_link_token(str(uuid.uuid4()))  # token for invite; we'll set id first
    witness = Witness(
        id=str(uuid.uuid4()),
        attempt_id=attempt_id,
        role=body.role,
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        organisation=body.organisation,
        expertise=body.expertise,
        status="invited",
        token=create_magic_link_token(str(uuid.uuid4())),
        invited_at=datetime.now(timezone.utc),
    )
    # Re-create token using witness id as the payload
    witness.token = create_magic_link_token(witness.id)
    db.add(witness)
    await db.commit()
    await db.refresh(witness)

    await send_magic_link(witness.email, witness.full_name, witness.token, attempt.record_title)
    await write_audit(db, "witness.invited", actor_id=user.id, target_type="witness", target_id=witness.id)
    return witness


@router.post("/bulk", response_model=List[WitnessOut], status_code=201)
async def bulk_invite(
    attempt_id: str,
    body: WitnessBulkCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attempt = await _get_attempt(attempt_id, db)
    created = []
    for w in body.witnesses:
        witness = Witness(
            id=str(uuid.uuid4()),
            attempt_id=attempt_id,
            role=w.role,
            full_name=w.full_name,
            email=w.email,
            phone=w.phone,
            organisation=w.organisation,
            expertise=w.expertise,
            status="invited",
            invited_at=datetime.now(timezone.utc),
        )
        witness.token = create_magic_link_token(witness.id)
        db.add(witness)
        created.append(witness)
    await db.commit()
    for w in created:
        await db.refresh(w)
        await send_magic_link(w.email, w.full_name, w.token, attempt.record_title)
    return created


@router.patch("/{witness_id}", response_model=WitnessOut)
async def update_witness(
    attempt_id: str,
    witness_id: str,
    body: WitnessUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Witness).where(Witness.id == witness_id, Witness.attempt_id == attempt_id)
    )
    witness = result.scalar_one_or_none()
    if not witness:
        raise HTTPException(status_code=404, detail="Witness not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(witness, field, value)

    await db.commit()
    await db.refresh(witness)
    return witness


@router.post("/{witness_id}/invite", response_model=WitnessOut)
async def resend_invite(
    attempt_id: str,
    witness_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attempt = await _get_attempt(attempt_id, db)
    result = await db.execute(
        select(Witness).where(Witness.id == witness_id, Witness.attempt_id == attempt_id)
    )
    witness = result.scalar_one_or_none()
    if not witness:
        raise HTTPException(status_code=404, detail="Witness not found")

    witness.token = create_magic_link_token(witness.id)
    witness.invited_at = datetime.now(timezone.utc)
    witness.status = "invited"
    await db.commit()
    await db.refresh(witness)
    await send_magic_link(witness.email, witness.full_name, witness.token, attempt.record_title)
    return witness
