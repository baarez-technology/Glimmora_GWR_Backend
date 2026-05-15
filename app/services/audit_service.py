import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def write_audit(
    db: AsyncSession,
    action: str,
    actor_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    ip: Optional[str] = None,
    detail: Optional[dict] = None,
) -> AuditLog:
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.ts.desc()).limit(1)
    )
    last = result.scalar_one_or_none()
    prev_hash = last.hash if last else None

    canonical = json.dumps({
        "action": action,
        "actor_id": actor_id,
        "target_type": target_type,
        "target_id": target_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "detail": detail,
    }, sort_keys=True)

    current_hash = hashlib.sha256(
        (prev_hash or "" + canonical).encode()
    ).hexdigest()

    entry = AuditLog(
        id=str(uuid.uuid4()),
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip=ip,
        detail_json=json.dumps(detail) if detail else None,
        prev_hash=prev_hash,
        hash=current_hash,
    )
    db.add(entry)
    await db.commit()
    return entry
