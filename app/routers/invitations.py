from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.attempt import Attempt
from app.models.witness import Witness
from app.models.statement import Statement
from app.models.user import User
from app.schemas.statement import StatementSubmit, StatementOut
from app.services.auth_service import verify_magic_link_token

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.get("/{token}")
async def resolve_invitation(token: str, db: AsyncSession = Depends(get_db)):
    """Public endpoint — resolves a magic-link token to invitation details."""
    witness_id = verify_magic_link_token(token)
    if not witness_id:
        raise HTTPException(status_code=401, detail="Invalid or expired invitation link")

    result = await db.execute(select(Witness).where(Witness.id == witness_id))
    witness = result.scalar_one_or_none()
    if not witness:
        raise HTTPException(status_code=404, detail="Witness not found")

    attempt = (await db.execute(select(Attempt).where(Attempt.id == witness.attempt_id))).scalar_one_or_none()

    return {
        "witness_id": witness.id,
        "attempt_id": witness.attempt_id,
        "attempt_title": attempt.record_title if attempt else "",
        "witness_name": witness.full_name,
        "witness_role": witness.role,
        "status": witness.status,
    }


@router.post("/{token}/statement", response_model=StatementOut, status_code=201)
async def submit_witness_statement(
    token: str,
    body: StatementSubmit,
    db: AsyncSession = Depends(get_db),
):
    """Witness submits their statement via magic link."""
    import json, uuid
    witness_id = verify_magic_link_token(token)
    if not witness_id:
        raise HTTPException(status_code=401, detail="Invalid or expired invitation link")

    result = await db.execute(select(Witness).where(Witness.id == witness_id))
    witness = result.scalar_one_or_none()
    if not witness:
        raise HTTPException(status_code=404, detail="Witness not found")

    kind = "timekeeper" if witness.role == "timekeeper" else "witness"

    statement = Statement(
        id=str(uuid.uuid4()),
        attempt_id=witness.attempt_id,
        witness_id=witness.id,
        kind=kind,
        fields_jsonb=json.dumps(body.fields),
        signature_png=body.signature_png,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(statement)
    witness.status = "completed"
    witness.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(statement)

    out = StatementOut(
        id=statement.id,
        attempt_id=statement.attempt_id,
        witness_id=statement.witness_id,
        kind=statement.kind,
        fields=body.fields,
        submitted_at=statement.submitted_at,
        created_at=statement.created_at,
    )
    return out
