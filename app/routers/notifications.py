from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app import models, schemas, security

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("", response_model=List[schemas.NotificationOut])
def get_user_notifications(
    unread_only: bool = False,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.org_id == current_user.org_id
    )
    if unread_only:
        query = query.filter(models.Notification.is_read == False)
        
    return query.order_by(desc(models.Notification.created_at)).limit(50).all()


@router.get("/unread-count")
def get_unread_notification_count(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    count = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.org_id == current_user.org_id,
        models.Notification.is_read == False
    ).count()
    return {"unread_count": count}


@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    n = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_id == current_user.id,
        models.Notification.org_id == current_user.org_id
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    n.is_read = True
    db.commit()
    return {"message": "Notification marked as read"}


@router.post("/mark-all-read")
def mark_all_notifications_read(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.org_id == current_user.org_id,
        models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}
