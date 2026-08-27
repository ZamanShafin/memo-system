import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app import models, schemas, security

router = APIRouter(prefix="/audit", tags=["Audit Log"])

@router.get("", response_model=List[schemas.AuditLogOut])
@router.get("/logs", response_model=List[schemas.AuditLogOut])
def get_audit_logs(
    event_type: Optional[str] = None,
    user_id: Optional[int] = None,
    object_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    admin_user: models.User = Depends(security.get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    Returns immutable audit logs for the organization (admin only).
    """
    query = db.query(models.AuditLog).filter(models.AuditLog.org_id == admin_user.org_id)
    
    if event_type and event_type != "All":
        query = query.filter(models.AuditLog.event_type == event_type)
    if user_id:
        query = query.filter(models.AuditLog.user_id == user_id)
    if object_type and object_type != "All":
        query = query.filter(models.AuditLog.object_type == object_type)
    if date_from:
        try:
            d_from = datetime.datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(models.AuditLog.created_at >= d_from)
        except Exception:
            pass
    if date_to:
        try:
            d_to = datetime.datetime.strptime(date_to, "%Y-%m-%d") + datetime.timedelta(days=1)
            query = query.filter(models.AuditLog.created_at <= d_to)
        except Exception:
            pass
            
    logs = query.order_by(desc(models.AuditLog.created_at)).limit(limit).all()
    return logs
