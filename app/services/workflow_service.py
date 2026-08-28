import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app import models, schemas
from app.services import audit_service, notification_service, version_service

def is_user_authorized_for_step(
    db: Session,
    memo: models.Memo,
    step: models.MemoWorkflowStep,
    user: models.User
) -> Tuple[bool, Optional[int]]:
    """
    Checks if user is either the assigned user or an active delegate.
    Returns (is_authorized, on_behalf_of_user_id).
    """
    if step.assigned_user_id == user.id:
        return True, None
    
    # Check for active delegation
    now = datetime.datetime.now(datetime.timezone.utc)
    delegation = db.query(models.WorkflowDelegation).filter(
        models.WorkflowDelegation.org_id == memo.org_id,
        models.WorkflowDelegation.delegator_id == step.assigned_user_id,
        models.WorkflowDelegation.delegatee_id == user.id,
        models.WorkflowDelegation.is_active == True,
        models.WorkflowDelegation.start_date <= now,
        models.WorkflowDelegation.end_date >= now
    ).first()
    
    if delegation:
        return True, step.assigned_user_id
    
    return False, None


def submit_memo(
    db: Session,
    memo: models.Memo,
    user: models.User,
    ip_address: Optional[str] = None
) -> models.Memo:
    """
    Submits a draft memo into the sequential workflow.
    """
    if memo.author_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the author or an admin can submit this memo"
        )
    
    if memo.status not in ["Draft", "Changes Requested"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Memo in status '{memo.status}' cannot be submitted"
        )
    
    # Ensure workflow steps exist
    steps = db.query(models.MemoWorkflowStep).filter(
        models.MemoWorkflowStep.memo_id == memo.id
    ).order_by(models.MemoWorkflowStep.step_index).all()
    
    if not steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow participants must be defined before submission"
        )
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # If initial submission from Draft
    if memo.status == "Draft":
        memo.submitted_at = now
        # Initial snapshot
        version_service.create_version_snapshot(
            db=db,
            memo=memo,
            editor_id=user.id,
            summary_of_changes="Initial submission"
        )
        
        # Step 0 is Author submission
        if steps[0].assigned_user_id == memo.author_id and steps[0].step_type == "author":
            steps[0].status = "completed"
            steps[0].action_taken = "submitted"
            steps[0].action_by_user_id = user.id
            steps[0].action_timestamp = now
            steps[0].is_current = False
            
            if len(steps) > 1:
                next_step = steps[1]
                next_step.is_current = True
                next_step.status = "pending"
                memo.current_step_index = 1
                memo.current_assignee_id = next_step.assigned_user_id
                memo.status = "Pending Review" if next_step.step_type == "review" else "Pending Approval"
                notification_service.notify_workflow_assignee(db, memo, next_step.assigned_user_id, next_step.role_name)
            else:
                # Single step workflow
                memo.status = "Approved"
                memo.final_approver_id = user.id
                memo.final_approved_at = now
                memo.current_assignee_id = None
        else:
            # First step is direct approver
            steps[0].is_current = True
            steps[0].status = "pending"
            memo.current_step_index = 0
            memo.current_assignee_id = steps[0].assigned_user_id
            memo.status = "Pending Review" if steps[0].step_type == "review" else "Pending Approval"
            notification_service.notify_workflow_assignee(db, memo, steps[0].assigned_user_id, steps[0].role_name)
        
        db.commit()
        db.refresh(memo)
        
        audit_service.log_event(
            db=db,
            org_id=memo.org_id,
            user_id=user.id,
            event_type="MEMO_SUBMIT",
            object_type="Memo",
            object_id=str(memo.id),
            description=f"Memo '{memo.memo_number}' submitted to workflow by {user.full_name}",
            ip_address=ip_address
        )
        return memo
    
    return memo


def process_workflow_action(
    db: Session,
    memo: models.Memo,
    user: models.User,
    action: str,  # "approve", "reject", "request_changes", "forward", "reassign", "approve_insert"
    comment: Optional[str] = None,
    reassign_to_user_id: Optional[int] = None,
    insert_step: Optional[schemas.WorkflowStepCreate] = None,
    ip_address: Optional[str] = None
) -> models.Memo:
    """
    Executes a sequential workflow action strictly validating current participant turn,
    supporting dynamic re-assignment, and ad-hoc intermediate reviewer step insertion.
    """
    if memo.status in ["Draft", "Approved", "Rejected", "Cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot perform workflow action on memo with status '{memo.status}'"
        )
    
    # Find current active step
    current_step = db.query(models.MemoWorkflowStep).filter(
        models.MemoWorkflowStep.memo_id == memo.id,
        models.MemoWorkflowStep.step_index == memo.current_step_index,
        models.MemoWorkflowStep.is_current == True
    ).first()
    
    if not current_step:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workflow step awaiting action"
        )
    
    # Check authorization (assignee, active delegate, or organization admin)
    is_auth, on_behalf_of = is_user_authorized_for_step(db, memo, current_step, user)
    if not is_auth:
        if user.role == "admin":
            is_auth = True
            on_behalf_of = current_step.assigned_user_id
        else:
            assigned_name = current_step.assigned_user.full_name if current_step.assigned_user else f"User #{current_step.assigned_user_id}"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: It is currently {assigned_name}'s turn ({current_step.role_name}) to act on this memo"
            )
    
    now = datetime.datetime.now(datetime.timezone.utc)
    action = action.lower()

    # 1. DECLINE & REASSIGN / REROUTE
    if action in ["reassign", "decline_reroute"]:
        if not reassign_to_user_id:
            raise HTTPException(status_code=400, detail="Target user ID for reassignment is required")
        
        target_user = db.query(models.User).filter(
            models.User.id == reassign_to_user_id,
            models.User.org_id == memo.org_id,
            models.User.is_active == True
        ).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="Selected colleague not found or inactive")
        
        orig_assignee_name = current_step.assigned_user.full_name if current_step.assigned_user else "Reviewer"
        current_step.assigned_user_id = target_user.id
        current_step.status = "pending"
        current_step.is_current = True
        memo.current_assignee_id = target_user.id

        # Comment in discussion
        c_text = f"[Declined & Rerouted] {user.full_name} declined and rerouted this step ({current_step.role_name}) to {target_user.full_name}."
        if comment and comment.strip():
            c_text += f" Note: {comment.strip()}"
        
        db.add(models.MemoComment(
            memo_id=memo.id,
            org_id=memo.org_id,
            user_id=user.id,
            comment_type="general",
            text=c_text
        ))

        # Notify new assignee
        notification_service.create_notification(
            db=db,
            org_id=memo.org_id,
            user_id=target_user.id,
            memo_id=memo.id,
            title="Memo Rerouted to You",
            message=f"Memo '{memo.memo_number}: {memo.title}' was rerouted to you by {user.full_name} for {current_step.role_name}.",
            event_type="action_required"
        )

        # Notify author
        notification_service.create_notification(
            db=db,
            org_id=memo.org_id,
            user_id=memo.author_id,
            memo_id=memo.id,
            title="Workflow Rerouted",
            message=f"Step '{current_step.role_name}' on memo '{memo.memo_number}' was rerouted from {orig_assignee_name} to {target_user.full_name}.",
            event_type="general"
        )

        db.commit()
        db.refresh(memo)

        audit_service.log_event(
            db=db,
            org_id=memo.org_id,
            user_id=user.id,
            event_type="WORKFLOW_REASSIGN",
            object_type="MemoWorkflowStep",
            object_id=str(current_step.id),
            description=f"Step #{current_step.step_index} rerouted to {target_user.full_name} by {user.full_name}",
            details={"reassigned_to_user_id": target_user.id, "comment": comment},
            ip_address=ip_address
        )
        return memo
    
    # 2. APPROVE & INSERT INTERMEDIATE REVIEWER
    elif action == "approve_insert" or (action in ["approve", "forward"] and insert_step is not None):
        target_user = db.query(models.User).filter(
            models.User.id == insert_step.assigned_user_id,
            models.User.org_id == memo.org_id,
            models.User.is_active == True
        ).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="Selected intermediate reviewer not found or inactive")

        # Mark current step completed
        current_step.status = "completed"
        current_step.action_taken = "approved"
        current_step.action_by_user_id = user.id
        current_step.on_behalf_of_user_id = on_behalf_of
        current_step.action_timestamp = now
        current_step.comments = comment
        current_step.is_current = False

        # Shift downstream steps down by 1
        downstream = db.query(models.MemoWorkflowStep).filter(
            models.MemoWorkflowStep.memo_id == memo.id,
            models.MemoWorkflowStep.step_index > memo.current_step_index
        ).order_by(models.MemoWorkflowStep.step_index.desc()).all()
        for ds in downstream:
            ds.step_index += 1

        # Insert new intermediate step
        inserted_index = memo.current_step_index + 1
        new_step = models.MemoWorkflowStep(
            memo_id=memo.id,
            step_index=inserted_index,
            step_type=insert_step.step_type or "approval",
            role_name=insert_step.role_name.strip() or f"Specialist Review ({target_user.full_name})",
            assigned_user_id=target_user.id,
            status="pending",
            is_current=True
        )
        db.add(new_step)

        # Advance memo pointer to inserted step
        memo.current_step_index = inserted_index
        memo.current_assignee_id = target_user.id
        memo.status = "Pending Review" if new_step.step_type == "review" else "Pending Approval"

        # Discussion Comment
        c_text = f"[Approved & Inserted Reviewer] {user.full_name} approved and inserted intermediate step '{new_step.role_name}' assigned to {target_user.full_name}."
        if comment and comment.strip():
            c_text += f" Remarks: {comment.strip()}"

        db.add(models.MemoComment(
            memo_id=memo.id,
            org_id=memo.org_id,
            user_id=user.id,
            comment_type="approval",
            text=c_text
        ))

        # Notify inserted reviewer
        notification_service.notify_workflow_assignee(db, memo, target_user.id, new_step.role_name)

        # Notify author
        notification_service.create_notification(
            db=db,
            org_id=memo.org_id,
            user_id=memo.author_id,
            memo_id=memo.id,
            title="Workflow Extended",
            message=f"Your memo '{memo.memo_number}' was approved by {user.full_name}, who inserted an additional review step with {target_user.full_name}.",
            event_type="approved"
        )

        db.commit()
        db.refresh(memo)

        audit_service.log_event(
            db=db,
            org_id=memo.org_id,
            user_id=user.id,
            event_type="WORKFLOW_INSERT_STEP",
            object_type="Memo",
            object_id=str(memo.id),
            description=f"Intermediate step '{new_step.role_name}' inserted for {target_user.full_name} by {user.full_name}",
            details={"inserted_user_id": target_user.id, "step_index": inserted_index, "comment": comment},
            ip_address=ip_address
        )
        return memo

    # 3. STANDARD APPROVE / FORWARD TO NEXT PRE-DEFINED STEP
    elif action in ["approve", "forward"]:
        current_step.status = "completed"
        current_step.action_taken = "approved" if action == "approve" else "forwarded"
        current_step.action_by_user_id = user.id
        current_step.on_behalf_of_user_id = on_behalf_of
        current_step.action_timestamp = now
        current_step.comments = comment
        current_step.is_current = False
        
        # Save comment in discussion log
        if comment:
            c_text = f"[{'Approved' if action == 'approve' else 'Forwarded'}] {comment}"
            if on_behalf_of:
                c_text = f"{c_text} (on behalf of {current_step.assigned_user.full_name})"
            db.add(models.MemoComment(
                memo_id=memo.id,
                org_id=memo.org_id,
                user_id=user.id,
                comment_type="approval",
                text=c_text
            ))
        
        # Check if there is a next step
        next_step = db.query(models.MemoWorkflowStep).filter(
            models.MemoWorkflowStep.memo_id == memo.id,
            models.MemoWorkflowStep.step_index == memo.current_step_index + 1
        ).first()
        
        if next_step:
            next_step.is_current = True
            next_step.status = "pending"
            memo.current_step_index += 1
            memo.current_assignee_id = next_step.assigned_user_id
            memo.status = "Pending Review" if next_step.step_type == "review" else "Pending Approval"
            notification_service.notify_workflow_assignee(db, memo, next_step.assigned_user_id, next_step.role_name)
            
            # Notify author of progress
            delegated_str = f" (via delegate {user.full_name})" if on_behalf_of else ""
            notification_service.create_notification(
                db=db,
                org_id=memo.org_id,
                user_id=memo.author_id,
                memo_id=memo.id,
                title="Memo Step Approved",
                message=f"Your memo '{memo.memo_number}' was approved by {current_step.assigned_user.full_name}{delegated_str} and advanced to {next_step.role_name}.",
                event_type="approved"
            )
        else:
            # Workflow completed! Final Approval reached
            memo.status = "Approved"
            memo.final_approver_id = user.id
            memo.final_approved_at = now
            memo.current_assignee_id = None
            
            # Notify author and participants
            notification_service.create_notification(
                db=db,
                org_id=memo.org_id,
                user_id=memo.author_id,
                memo_id=memo.id,
                title="Memo Approved & Completed",
                message=f"Congratulations! Your memo '{memo.memo_number}: {memo.title}' has received final approval.",
                event_type="workflow_completed"
            )
            
            audit_service.log_event(
                db=db,
                org_id=memo.org_id,
                user_id=user.id,
                event_type="WORKFLOW_COMPLETE",
                object_type="Memo",
                object_id=str(memo.id),
                description=f"Memo '{memo.memo_number}' completed all workflow approval steps.",
                ip_address=ip_address
            )
        
        db.commit()
        db.refresh(memo)
        
        audit_service.log_event(
            db=db,
            org_id=memo.org_id,
            user_id=user.id,
            event_type="WORKFLOW_APPROVE",
            object_type="MemoWorkflowStep",
            object_id=str(current_step.id),
            description=f"Step #{current_step.step_index} ({current_step.role_name}) approved by {user.full_name}" + (f" on behalf of {current_step.assigned_user.full_name}" if on_behalf_of else ""),
            details={"action": action, "comment": comment, "on_behalf_of": on_behalf_of},
            ip_address=ip_address
        )
        return memo
    
    elif action == "reject":
        if not comment or not comment.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A rejection reason/comment is required"
            )
        
        current_step.status = "rejected"
        current_step.action_taken = "rejected"
        current_step.action_by_user_id = user.id
        current_step.on_behalf_of_user_id = on_behalf_of
        current_step.action_timestamp = now
        current_step.comments = comment
        current_step.is_current = False
        
        memo.status = "Rejected"
        memo.current_assignee_id = None
        
        # Save rejection comment in discussion
        c_text = f"[Rejected] {comment}"
        if on_behalf_of:
            c_text = f"{c_text} (on behalf of {current_step.assigned_user.full_name})"
        db.add(models.MemoComment(
            memo_id=memo.id,
            org_id=memo.org_id,
            user_id=user.id,
            comment_type="rejection",
            text=c_text
        ))
        
        # Notify author
        notification_service.create_notification(
            db=db,
            org_id=memo.org_id,
            user_id=memo.author_id,
            memo_id=memo.id,
            title="Memo Rejected",
            message=f"Your memo '{memo.memo_number}' was rejected by {current_step.assigned_user.full_name}. Reason: {comment}",
            event_type="rejected"
        )
        
        db.commit()
        db.refresh(memo)
        
        audit_service.log_event(
            db=db,
            org_id=memo.org_id,
            user_id=user.id,
            event_type="WORKFLOW_REJECT",
            object_type="MemoWorkflowStep",
            object_id=str(current_step.id),
            description=f"Memo '{memo.memo_number}' rejected by {user.full_name}. Reason: {comment}",
            details={"comment": comment, "on_behalf_of": on_behalf_of},
            ip_address=ip_address
        )
        return memo
    
    elif action == "request_changes":
        if not comment or not comment.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A comment explaining the requested changes is required"
            )
        
        current_step.status = "changes_requested"
        current_step.action_taken = "changes_requested"
        current_step.action_by_user_id = user.id
        current_step.on_behalf_of_user_id = on_behalf_of
        current_step.action_timestamp = now
        current_step.comments = comment
        current_step.is_current = False
        
        memo.status = "Changes Requested"
        memo.current_assignee_id = memo.author_id
        
        # Save change request comment in discussion
        c_text = f"[Change Request] {comment}"
        if on_behalf_of:
            c_text = f"{c_text} (on behalf of {current_step.assigned_user.full_name})"
        db.add(models.MemoComment(
            memo_id=memo.id,
            org_id=memo.org_id,
            user_id=user.id,
            comment_type="change_request",
            text=c_text
        ))
        
        # Notify author
        notification_service.create_notification(
            db=db,
            org_id=memo.org_id,
            user_id=memo.author_id,
            memo_id=memo.id,
            title="Changes Requested on Memo",
            message=f"Changes were requested on memo '{memo.memo_number}' by {current_step.assigned_user.full_name}. Feedback: {comment}",
            event_type="changes_requested"
        )
        
        db.commit()
        db.refresh(memo)
        
        audit_service.log_event(
            db=db,
            org_id=memo.org_id,
            user_id=user.id,
            event_type="WORKFLOW_REQUEST_CHANGES",
            object_type="MemoWorkflowStep",
            object_id=str(current_step.id),
            description=f"Changes requested on memo '{memo.memo_number}' by {user.full_name}: {comment}",
            details={"comment": comment, "on_behalf_of": on_behalf_of},
            ip_address=ip_address
        )
        return memo
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown workflow action '{action}'. Valid actions: approve, reject, request_changes, forward"
        )


def resubmit_memo_after_changes(
    db: Session,
    memo: models.Memo,
    user: models.User,
    summary_of_changes: Optional[str] = None,
    ip_address: Optional[str] = None
) -> models.Memo:
    """
    Allows the author to resubmit a memo when changes were requested, snapshotting a new version.
    """
    if memo.author_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the author or an admin can resubmit this memo"
        )
    
    if memo.status != "Changes Requested":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only memos in 'Changes Requested' status can be resubmitted. Current status: '{memo.status}'"
        )
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Snapshot new version (e.g. Version 2, 3...)
    version_service.create_version_snapshot(
        db=db,
        memo=memo,
        editor_id=user.id,
        summary_of_changes=summary_of_changes or "Updated and resubmitted after change request"
    )
    
    # 2. Reset workflow step that requested changes (or restart from Step 1)
    steps = db.query(models.MemoWorkflowStep).filter(
        models.MemoWorkflowStep.memo_id == memo.id
    ).order_by(models.MemoWorkflowStep.step_index).all()
    
    # Find step that requested changes
    target_step = None
    for step in steps:
        if step.status == "changes_requested":
            target_step = step
            break
            
    # If not found or author wants to start from first approver
    if not target_step and len(steps) > 1:
        target_step = steps[1]
    elif not target_step and len(steps) > 0:
        target_step = steps[0]
        
    target_step.status = "pending"
    target_step.is_current = True
    target_step.action_taken = None
    target_step.action_by_user_id = None
    target_step.on_behalf_of_user_id = None
    target_step.action_timestamp = None
    target_step.comments = None
    
    memo.current_step_index = target_step.step_index
    memo.current_assignee_id = target_step.assigned_user_id
    memo.status = "Pending Review" if target_step.step_type == "review" else "Pending Approval"
    
    # Notify assignee
    notification_service.notify_workflow_assignee(db, memo, target_step.assigned_user_id, target_step.role_name)
    
    db.commit()
    db.refresh(memo)
    
    audit_service.log_event(
        db=db,
        org_id=memo.org_id,
        user_id=user.id,
        event_type="WORKFLOW_RESUBMIT",
        object_type="Memo",
        object_id=str(memo.id),
        description=f"Memo '{memo.memo_number}' revised and resubmitted by {user.full_name}. Summary: {summary_of_changes or 'None'}",
        details={"summary_of_changes": summary_of_changes},
        ip_address=ip_address
    )
    return memo


def modify_downstream_steps(
    db: Session,
    memo: models.Memo,
    user: models.User,
    new_downstream_steps: list,
    ip_address: Optional[str] = None
) -> models.Memo:
    """
    Allows the current active reviewer or admin to dynamically add, remove,
    or adjust upcoming downstream workflow participants.
    """
    if memo.status in ["Approved", "Rejected", "Draft", "Cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify workflow steps on finalized or draft memos"
        )
    
    if memo.current_assignee_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the current active reviewer or admin can modify downstream workflow participants"
        )
    
    # Delete existing downstream steps
    db.query(models.MemoWorkflowStep).filter(
        models.MemoWorkflowStep.memo_id == memo.id,
        models.MemoWorkflowStep.step_index > memo.current_step_index
    ).delete()
    
    # Re-create downstream steps
    curr_idx = memo.current_step_index
    for offset, step_data in enumerate(new_downstream_steps, start=1):
        target_u = db.query(models.User).filter(
            models.User.id == step_data.assigned_user_id,
            models.User.org_id == memo.org_id,
            models.User.is_active == True
        ).first()
        if not target_u:
            raise HTTPException(status_code=400, detail=f"Participant #{step_data.assigned_user_id} is invalid or inactive")
        
        w_step = models.MemoWorkflowStep(
            memo_id=memo.id,
            step_index=curr_idx + offset,
            step_type=step_data.step_type or "approval",
            role_name=step_data.role_name.strip() or target_u.designation or target_u.full_name,
            assigned_user_id=target_u.id,
            status="pending",
            is_current=False
        )
        db.add(w_step)
        
    db.add(models.MemoComment(
        memo_id=memo.id,
        org_id=memo.org_id,
        user_id=user.id,
        comment_type="general",
        text=f"[Workflow Modified] {user.full_name} updated the upcoming downstream workflow participants ({len(new_downstream_steps)} remaining steps)."
    ))
    
    db.commit()
    db.refresh(memo)
    
    audit_service.log_event(
        db=db,
        org_id=memo.org_id,
        user_id=user.id,
        event_type="WORKFLOW_STEPS_MODIFIED",
        object_type="Memo",
        object_id=str(memo.id),
        description=f"Downstream workflow steps updated for memo '{memo.memo_number}' by {user.full_name}",
        details={"downstream_steps_count": len(new_downstream_steps)},
        ip_address=ip_address
    )
    return memo
