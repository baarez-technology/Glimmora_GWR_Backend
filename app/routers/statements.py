import uuid
import json
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.statement import Statement
from app.models.user import User
from app.schemas.statement import StatementSubmit, StatementOut, PDFDownloadResponse
from app.services.storage_service import generate_download_url

router = APIRouter(prefix="/attempts/{attempt_id}/statements", tags=["statements"])


@router.post("/{kind}", response_model=StatementOut, status_code=201)
async def submit_statement(
    attempt_id: str,
    kind: str,
    body: StatementSubmit,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    statement = Statement(
        id=str(uuid.uuid4()),
        attempt_id=attempt_id,
        kind=kind,
        fields_jsonb=json.dumps(body.fields),
        signature_png=body.signature_png,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(statement)
    await db.commit()
    await db.refresh(statement)

    return StatementOut(
        id=statement.id,
        attempt_id=statement.attempt_id,
        kind=statement.kind,
        fields=body.fields,
        submitted_at=statement.submitted_at,
        created_at=statement.created_at,
    )


@router.get("", response_model=List[StatementOut])
async def list_statements(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Statement).where(Statement.attempt_id == attempt_id))
    statements = result.scalars().all()
    out = []
    for s in statements:
        fields = json.loads(s.fields_jsonb) if s.fields_jsonb else None
        out.append(StatementOut(
            id=s.id,
            attempt_id=s.attempt_id,
            witness_id=s.witness_id,
            steward_id=s.steward_id,
            kind=s.kind,
            fields=fields,
            pdf_s3_key=s.pdf_s3_key,
            submitted_at=s.submitted_at,
            created_at=s.created_at,
        ))
    return out


@router.get("/{statement_id}/pdf", response_model=PDFDownloadResponse)
async def get_pdf_url(
    attempt_id: str,
    statement_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Statement).where(Statement.id == statement_id))
    statement = result.scalar_one_or_none()
    if not statement or not statement.pdf_s3_key:
        raise HTTPException(status_code=404, detail="PDF not found")

    url = await generate_download_url(statement.pdf_s3_key)
    if not url:
        raise HTTPException(status_code=503, detail="Storage not configured")

    return PDFDownloadResponse(url=url)
