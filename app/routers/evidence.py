import uuid
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.evidence import Evidence
from app.models.user import User
from app.schemas.evidence import EvidenceInitRequest, EvidenceCompleteRequest, UploadUrlResponse, EvidenceOut
from app.services.storage_service import generate_upload_url, generate_s3_key

router = APIRouter(prefix="/attempts/{attempt_id}/evidence", tags=["evidence"])


@router.post("/init", response_model=UploadUrlResponse, status_code=201)
async def init_evidence(
    attempt_id: str,
    body: EvidenceInitRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    evidence_id = str(uuid.uuid4())
    s3_key = None
    upload_url = None

    if body.type != "link":
        s3_key = generate_s3_key(attempt_id, evidence_id, body.file_name or "file")
        upload_url = await generate_upload_url(s3_key, body.mime_type)

    evidence = Evidence(
        id=evidence_id,
        attempt_id=attempt_id,
        type=body.type,
        file_name=body.file_name,
        file_url=body.file_url,
        s3_key=s3_key,
        size_bytes=body.size_bytes,
        mime_type=body.mime_type,
        description=body.description,
        status="uploading" if body.type != "link" else "indexed",
    )
    db.add(evidence)
    await db.commit()

    return UploadUrlResponse(evidence_id=evidence_id, upload_url=upload_url)


@router.post("/{evidence_id}/complete", response_model=EvidenceOut)
async def complete_evidence(
    attempt_id: str,
    evidence_id: str,
    body: EvidenceCompleteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = result.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    evidence.status = "scanning"
    if body.sha256:
        evidence.sha256 = body.sha256

    await db.commit()
    await db.refresh(evidence)

    # Enqueue background scan + classification
    try:
        from app.workers.tasks import process_evidence
        process_evidence.delay(evidence_id)
    except Exception:
        evidence.status = "indexed"
        await db.commit()
        await db.refresh(evidence)

    return _to_out(evidence)


@router.get("", response_model=List[EvidenceOut])
async def list_evidence(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Evidence).where(Evidence.attempt_id == attempt_id))
    return [_to_out(e) for e in result.scalars().all()]


def _to_out(e: Evidence) -> EvidenceOut:
    tags = json.loads(e.tags_json) if e.tags_json else None
    return EvidenceOut(
        id=e.id,
        attempt_id=e.attempt_id,
        type=e.type,
        status=e.status,
        file_name=e.file_name,
        s3_key=e.s3_key,
        file_url=e.file_url,
        size_bytes=e.size_bytes,
        mime_type=e.mime_type,
        duration_seconds=e.duration_seconds,
        ai_confidence=e.ai_confidence,
        tags=tags,
        transcript=e.transcript,
        description=e.description,
        sha256=e.sha256,
        uploaded_at=e.uploaded_at,
        updated_at=e.updated_at,
    )
