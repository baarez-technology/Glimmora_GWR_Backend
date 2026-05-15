import os
import uuid
import logging
from typing import Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


def _s3_client():
    import boto3
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def _s3_configured() -> bool:
    return bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)


def generate_s3_key(attempt_id: str, evidence_id: str, file_name: str) -> str:
    ext = os.path.splitext(file_name)[1] if file_name else ""
    return f"attempts/{attempt_id}/evidence/{evidence_id}{ext}"


async def generate_upload_url(s3_key: str, mime_type: Optional[str] = None) -> Optional[str]:
    """Returns a pre-signed PUT URL for direct browser → S3 upload."""
    if not _s3_configured():
        logger.info("S3 not configured, skipping pre-signed URL generation for key: %s", s3_key)
        return None

    try:
        s3 = _s3_client()
        params = {
            "Bucket": settings.S3_BUCKET,
            "Key": s3_key,
        }
        if mime_type:
            params["ContentType"] = mime_type

        url = s3.generate_presigned_url("put_object", Params=params, ExpiresIn=3600)
        return url
    except Exception as e:
        logger.error("Failed to generate upload URL: %s", e)
        return None


async def generate_download_url(s3_key: str, expires_in: int = 300) -> Optional[str]:
    """Returns a pre-signed GET URL for evidence download/playback."""
    if not _s3_configured():
        return None

    try:
        s3 = _s3_client()
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": s3_key},
            ExpiresIn=expires_in,
        )
        return url
    except Exception as e:
        logger.error("Failed to generate download URL: %s", e)
        return None


async def delete_object(s3_key: str) -> bool:
    if not _s3_configured():
        return True
    try:
        s3 = _s3_client()
        s3.delete_object(Bucket=settings.S3_BUCKET, Key=s3_key)
        return True
    except Exception as e:
        logger.error("Failed to delete S3 object: %s", e)
        return False
