import json
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from app import models

def log_event(
    db: Session,
    org_id: int,
    user_id: Optional[int],
    event_type: str,
    object_type: str,
    object_id: Optional[str] = None,
    description: str = "",
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> models.AuditLog:
    """
    Creates an immutable audit log record.
    """
    details_str = json.dumps(details, default=str) if details else None
    audit = models.AuditLog(
        org_id=org_id,
        user_id=user_id,
        event_type=event_type,
        object_type=object_type,
        object_id=str(object_id) if object_id is not None else None,
        description=description,
        details_json=details_str,
        ip_address=ip_address
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit
