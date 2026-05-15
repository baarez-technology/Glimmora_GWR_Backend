import uuid
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.attempt import Attempt
from app.models.user import User

router = APIRouter(tags=["packages"])


class JobStatus(BaseModel):
    job_id: str
    status: str  # queued | running | done | failed
    download_url: Optional[str] = None


@router.post("/attempts/{attempt_id}/package/build", response_model=JobStatus)
async def build_package(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Attempt).where(Attempt.id == attempt_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Attempt not found")

    job_id = str(uuid.uuid4())

    try:
        from app.workers.tasks import build_submission_package
        task = build_submission_package.delay(attempt_id, job_id)
        job_id = task.id
    except Exception:
        pass

    return JobStatus(job_id=job_id, status="queued")


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    user: User = Depends(get_current_user),
):
    try:
        from app.workers.celery_app import celery_app
        result = celery_app.AsyncResult(job_id)
        status_map = {
            "PENDING": "queued",
            "STARTED": "running",
            "SUCCESS": "done",
            "FAILURE": "failed",
        }
        status = status_map.get(result.state, "queued")
        download_url = result.result.get("download_url") if status == "done" and isinstance(result.result, dict) else None
        return JobStatus(job_id=job_id, status=status, download_url=download_url)
    except Exception:
        return JobStatus(job_id=job_id, status="queued")


@router.get("/attempts/{attempt_id}/package/download")
async def download_package(
    attempt_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=404, detail="No package built yet")
