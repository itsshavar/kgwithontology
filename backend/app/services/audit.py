import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.security import AuditLog, User


def record_audit(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: str | int | None = None,
    actor: User | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    audit = AuditLog(
        actor_user_id=actor.id if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        metadata_json=json.dumps(metadata or {}, sort_keys=True),
    )
    db.add(audit)
    return audit
