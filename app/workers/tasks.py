"""
Celery background tasks.
Each task runs in a sync context but uses asyncio.run() to call async DB operations.
"""
import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.workers.tasks.process_evidence")
def process_evidence(self, evidence_id: str):
    """
    Post-upload processing pipeline:
    1. Antivirus scan (stub)
    2. AI classification
    3. OCR / speech-to-text (by type)
    4. Mark as indexed
    """
    logger.info("Processing evidence %s", evidence_id)

    async def _run():
        from app.database import AsyncSessionLocal
        from app.models.evidence import Evidence
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
            evidence = result.scalar_one_or_none()
            if not evidence:
                return

            # Stub: mark as indexed after "processing"
            evidence.status = "indexed"
            await db.commit()
            logger.info("Evidence %s indexed", evidence_id)

    asyncio.run(_run())
    return {"evidence_id": evidence_id, "status": "indexed"}


@celery_app.task(bind=True, name="app.workers.tasks.build_submission_package")
def build_submission_package(self, attempt_id: str, job_id: str):
    """
    Build a ZIP package with the 7-folder GWR submission structure.
    Streams using zipstream-ng to avoid buffering large video files.
    """
    logger.info("Building package for attempt %s", attempt_id)

    async def _run():
        from app.database import AsyncSessionLocal
        from app.models.evidence import Evidence
        from app.models.statement import Statement
        from sqlalchemy import select
        import json

        async with AsyncSessionLocal() as db:
            evidence = (await db.execute(
                select(Evidence).where(Evidence.attempt_id == attempt_id)
            )).scalars().all()
            statements = (await db.execute(
                select(Statement).where(Statement.attempt_id == attempt_id)
            )).scalars().all()

        # Stub: in production, stream files from S3 into a ZIP using zipstream-ng
        logger.info("Package for attempt %s would contain %d evidence items and %d statements",
                    attempt_id, len(evidence), len(statements))

    asyncio.run(_run())
    return {"attempt_id": attempt_id, "status": "done", "download_url": None}


@celery_app.task(name="app.workers.tasks.run_logbook_validation")
def run_logbook_validation(attempt_id: str):
    """Validate logbook and create AIAlert rows for violations."""
    logger.info("Validating logbook for attempt %s", attempt_id)

    async def _run():
        from app.database import AsyncSessionLocal
        from app.models.activity import ActivityRow, RestRow
        from app.models.ai_alert import AIAlert
        from app.services.gwr_logic import compute_logbook, LogbookRow
        from sqlalchemy import select
        import uuid

        async with AsyncSessionLocal() as db:
            act_rows = (await db.execute(
                select(ActivityRow).where(ActivityRow.attempt_id == attempt_id)
            )).scalars().all()
            rest_rows = (await db.execute(
                select(RestRow).where(RestRow.attempt_id == attempt_id)
            )).scalars().all()

            result = compute_logbook(
                [LogbookRow("activity", r.sequence, r.start_hhmm, r.end_hhmm, r.notes) for r in act_rows],
                [LogbookRow("rest", r.sequence, r.start_hhmm, r.end_hhmm, r.notes) for r in rest_rows],
            )

            for violation in result.violations:
                alert = AIAlert(
                    id=str(uuid.uuid4()),
                    attempt_id=attempt_id,
                    severity="warning",
                    title="Logbook Violation",
                    description=violation,
                    recommendation="Review and correct the rest/activity schedule.",
                )
                db.add(alert)
            await db.commit()

    asyncio.run(_run())
