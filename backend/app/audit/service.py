

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditLog

GENESIS_HASH = "0" * 64


def _timestamp_text(value: datetime) -> str:
    """Normalize timestamps so SQLite timezone handling stays consistent."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value.isoformat()


def _event_hash(
    previous_hash: str,
    actor_id: int | None,
    action: str,
    resource_type: str,
    resource_id: str | None,
    outcome: str,
    details: str,
    timestamp: str,
) -> str:
    payload = {
        "previous_hash": previous_hash,
        "actor_id": actor_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "outcome": outcome,
        "details": details,
        "timestamp": timestamp,
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record_audit_event(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    outcome: str = "success",
    details: str = "",
) -> AuditLog:
    previous = db.scalar(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(1)
    )
    previous_hash = previous.event_hash if previous else GENESIS_HASH

    timestamp = datetime.now(timezone.utc)

    event = AuditLog(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        details=details,
        timestamp=timestamp,
        previous_hash=previous_hash,
        event_hash=_event_hash(
            previous_hash,
            actor_id,
            action,
            resource_type,
            resource_id,
            outcome,
            details,
            _timestamp_text(timestamp),
        ),
    )

    db.add(event)
    db.flush()

    return event


def verify_audit_chain(db: Session) -> bool:
    events = db.scalars(
        select(AuditLog).order_by(AuditLog.id.asc())
    ).all()

    expected_previous = GENESIS_HASH

    for event in events:
        if event.previous_hash != expected_previous:
            return False

        expected_hash = _event_hash(
            event.previous_hash,
            event.actor_id,
            event.action,
            event.resource_type,
            event.resource_id,
            event.outcome,
            event.details,
            _timestamp_text(event.timestamp),
        )

        if event.event_hash != expected_hash:
            return False

        expected_previous = event.event_hash

    return True
