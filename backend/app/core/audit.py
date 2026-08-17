from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("video_factory.audit")

IMMUTABLE_LOG_PATH = "./data/audit_immutable.log"


def audit_log(
    db: Session,
    user_id: Optional[int],
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    from app.models.audit import AuditLog

    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=str(resource_id) if resource_id is not None else None,
        details_json=json.dumps(details or {}, ensure_ascii=False),
        ip=ip,
        user_agent=user_agent,
    )
    db.add(entry)
    db.commit()

    # Immutable append-only log (hash chained) for tamper-evidence
    _append_immutable(entry)


def _append_immutable(entry) -> None:
    import hashlib
    import os

    os.makedirs(os.path.dirname(IMMUTABLE_LOG_PATH), exist_ok=True)
    prev_hash = "0"
    if os.path.exists(IMMUTABLE_LOG_PATH):
        with open(IMMUTABLE_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    prev_hash = line.strip().split(" ")[-1]
    payload = json.dumps(
        {
            "id": entry.id,
            "user_id": entry.user_id,
            "action": entry.action,
            "resource": entry.resource,
            "resource_id": entry.resource_id,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        },
        default=str,
        ensure_ascii=False,
    )
    chain_hash = hashlib.sha256(f"{prev_hash}|{payload}".encode()).hexdigest()
    with open(IMMUTABLE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{payload} {chain_hash}\n")
    logger.info("audit %s %s %s", entry.action, entry.resource, entry.resource_id)
