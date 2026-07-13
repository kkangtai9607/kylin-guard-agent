from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.db.models import AuditChainHead, AuditEvent
from backend.app.guardrails.untrusted import sanitize_text

SENSITIVE_MARKERS = ("password", "token", "secret", "api_key", "authorization", "private_key")


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "***REDACTED***"
            if any(marker in str(key).lower() for marker in SENSITIVE_MARKERS)
            else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def write_audit(
    db: Session,
    event_type: str,
    payload: Mapping[str, Any],
    actor_id: str | None = None,
    task_id: str | None = None,
) -> AuditEvent:
    head = db.get(AuditChainHead, 1)
    if head is None:
        head = AuditChainHead(id=1, current_hash="", version=0)
        db.add(head)
        db.flush()
    db.execute(
        update(AuditChainHead)
        .where(AuditChainHead.id == 1)
        .values(version=AuditChainHead.version + 1)
    )
    db.refresh(head)
    previous_hash = head.current_hash
    safe_payload = json.dumps(
        redact(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    event_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    material = json.dumps(
        {
            "actor_id": actor_id,
            "created_at": _timestamp(created_at),
            "event_id": event_id,
            "event_type": event_type,
            "payload_json": safe_payload,
            "previous_hash": previous_hash,
            "task_id": task_id,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    current_hash = hashlib.sha256(material.encode()).hexdigest()
    event = AuditEvent(
        id=event_id,
        event_type=event_type,
        actor_id=actor_id,
        task_id=task_id,
        payload_json=safe_payload,
        previous_hash=previous_hash,
        current_hash=current_hash,
        created_at=created_at,
    )
    db.add(event)
    head.current_hash = current_hash
    return event


def verify_chain(db: Session) -> tuple[bool, str | None]:
    previous_hash = ""
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at, AuditEvent.id)).all()
    for event in events:
        material = json.dumps(
            {
                "actor_id": event.actor_id,
                "created_at": _timestamp(event.created_at),
                "event_id": event.id,
                "event_type": event.event_type,
                "payload_json": event.payload_json,
                "previous_hash": previous_hash,
                "task_id": event.task_id,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        expected = hashlib.sha256(material.encode()).hexdigest()
        if event.previous_hash != previous_hash or event.current_hash != expected:
            return False, event.id
        previous_hash = event.current_hash
    return True, None


def _timestamp(value: datetime) -> str:
    return (
        (value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc))
        .astimezone(timezone.utc)
        .isoformat()
    )
