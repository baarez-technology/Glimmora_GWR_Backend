from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.ai_alert import AIAlert
from app.models.evidence import Evidence
from app.models.user import User
from app.schemas.ai_alert import AIAlertOut, TimelineEvent, ProcessingStatus, CoverLetterExpandRequest, CoverLetterExpandResponse

router = APIRouter(prefix="/attempts/{attempt_id}/ai", tags=["ai"])


@router.get("/alerts", response_model=List[AIAlertOut])
async def get_alerts(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(AIAlert).where(AIAlert.attempt_id == attempt_id))
    return result.scalars().all()


@router.get("/timeline", response_model=List[TimelineEvent])
async def get_timeline(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Return evidence as basic timeline events until AI worker runs
    result = await db.execute(
        select(Evidence).where(Evidence.attempt_id == attempt_id, Evidence.status == "indexed")
    )
    events = []
    for e in result.scalars().all():
        events.append(TimelineEvent(
            timestamp=e.uploaded_at.isoformat(),
            title=e.file_name or e.type,
            description=e.description,
            evidence_ids=[e.id],
            type="evidence",
        ))
    return events


@router.get("/processing-status", response_model=ProcessingStatus)
async def get_processing_status(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Evidence).where(Evidence.attempt_id == attempt_id))
    all_evidence = result.scalars().all()

    return ProcessingStatus(
        attempt_id=attempt_id,
        total_evidence=len(all_evidence),
        indexed=sum(1 for e in all_evidence if e.status == "indexed"),
        processing=sum(1 for e in all_evidence if e.status == "scanning"),
        failed=sum(1 for e in all_evidence if e.status == "rejected"),
        workers={
            "classifier": "idle",
            "ocr": "idle",
            "speech": "idle",
            "logbook_validator": "idle",
        },
    )


@router.post("/cover-letter/expand", response_model=CoverLetterExpandResponse)
async def expand_cover_letter(
    attempt_id: str,
    body: CoverLetterExpandRequest,
    user: User = Depends(get_current_user),
):
    from app.config import settings

    if not settings.ANTHROPIC_API_KEY:
        return CoverLetterExpandResponse(expanded_text=body.current_text)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": (
                    f"Expand and improve the following GWR attempt cover letter. "
                    f"Keep the factual content, improve clarity and completeness.\n\n"
                    f"Context: {body.context_hint or 'GWR world record attempt'}\n\n"
                    f"Current text:\n{body.current_text}"
                ),
            }],
        )
        return CoverLetterExpandResponse(expanded_text=message.content[0].text)
    except Exception:
        return CoverLetterExpandResponse(expanded_text=body.current_text)
