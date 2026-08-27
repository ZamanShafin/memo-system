from typing import Optional
from sqlalchemy.orm import Session
from app import models

def create_notification(
    db: Session,
    org_id: int,
    user_id: int,
    title: str,
    message: str,
    event_type: str,
    memo_id: Optional[int] = None
) -> models.Notification:
    """
    Creates an in-app notification for a user.
    """
    notification = models.Notification(
        org_id=org_id,
        user_id=user_id,
        memo_id=memo_id,
        title=title,
        message=message,
        event_type=event_type,
        is_read=False
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification

def notify_workflow_assignee(db: Session, memo: models.Memo, assignee_id: int, role_name: str):
    """
    Notifies the newly assigned user (and their active delegate if any) that an action is required.
    """
    create_notification(
        db=db,
        org_id=memo.org_id,
        user_id=assignee_id,
        memo_id=memo.id,
        title="Action Required on Memo",
        message=f"Memo '{memo.memo_number}: {memo.title}' is pending your review/approval as {role_name}.",
        event_type="action_required"
    )
    
    # Check for active delegation
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    delegations = db.query(models.WorkflowDelegation).filter(
        models.WorkflowDelegation.org_id == memo.org_id,
        models.WorkflowDelegation.delegator_id == assignee_id,
        models.WorkflowDelegation.is_active == True,
        models.WorkflowDelegation.start_date <= now,
        models.WorkflowDelegation.end_date >= now
    ).all()
    
    for delegation in delegations:
        create_notification(
            db=db,
            org_id=memo.org_id,
            user_id=delegation.delegatee_id,
            memo_id=memo.id,
            title="Delegated Action Required",
            message=f"You have a delegated action for memo '{memo.memo_number}: {memo.title}' on behalf of user #{assignee_id}.",
            event_type="action_required"
        )
