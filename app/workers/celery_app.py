from celery import Celery
from app.config import settings

celery_app = Celery(
    "gwr_workers",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_routes={
        "app.workers.tasks.process_evidence": {"queue": "default"},
        "app.workers.tasks.build_submission_package": {"queue": "default"},
        "app.workers.tasks.run_logbook_validation": {"queue": "default"},
    },
)
