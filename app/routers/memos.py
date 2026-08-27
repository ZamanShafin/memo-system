import os
import uuid
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from app.database import get_db
from app.config import settings
from app import models, schemas, security
from app.services import workflow_service, version_service, audit_service, notification_service, pdf_service

router = APIRouter(prefix="/memos", tags=["Memos"])

def generate_memo_number(db: Session, org: models.Organization) -> str:
    """
    Generates a unique memo reference number: MEMO-{ORG_CODE}-{YEAR}-{SEQ:04d}
    """
    year = datetime.datetime.now(datetime.timezone.utc).year
    prefix = f"MEMO-{org.code.upper()}-{year}-"
    # Find highest sequence for this year and org
    existing = db.query(models.Memo).filter(
        models.Memo.org_id == org.id,
        models.Memo.memo_number.like(f"{prefix}%")
    ).count()
    return f"{prefix}{existing + 1:04d}"

def verify_memo_access(memo: models.Memo, user: models.User, db: Session) -> bool:
    """
    Enforces strict tenant isolation and memo access authorization.
    """
    if memo.org_id != user.org_id:
        return False
    if user.role == "admin":
        return True
    if memo.author_id == user.id:
        return True
    if memo.current_assignee_id == user.id:
        return True
    
    # Check if participant in any step
    is_step_user = any(s.assigned_user_id == user.id for s in memo.workflow_steps)
    if is_step_user:
        return True
        
    # Check if active delegate for any assigned step
    now = datetime.datetime.now(datetime.timezone.utc)
    delegation = db.query(models.WorkflowDelegation).filter(
        models.WorkflowDelegation.org_id == memo.org_id,
        models.WorkflowDelegation.delegatee_id == user.id,
        models.WorkflowDelegation.is_active == True,
        models.WorkflowDelegation.start_date <= now,
        models.WorkflowDelegation.end_date >= now
    ).first()
    if delegation:
        if any(s.assigned_user_id == delegation.delegator_id for s in memo.workflow_steps):
            return True
            
    # For completed memos in same department
    if memo.status == "Approved" and memo.department_id and memo.department_id == user.department_id:
        return True
        
    return False


@router.post("", response_model=schemas.MemoOut)
def create_memo(
    memo_in: schemas.MemoCreate,
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    org = db.query(models.Organization).filter(models.Organization.id == current_user.org_id).first()
    memo_num = generate_memo_number(db, org)
    
    # Always create with Draft status initially, then submit if is_draft is False
    memo = models.Memo(
        org_id=current_user.org_id,
        author_id=current_user.id,
        department_id=memo_in.department_id or current_user.department_id,
        category_id=memo_in.category_id,
        memo_number=memo_num,
        title=memo_in.title.strip(),
        body=memo_in.body.strip(),
        priority=memo_in.priority,
        status="Draft",
        current_step_index=0,
        current_assignee_id=current_user.id
    )
    db.add(memo)
    db.commit()
    db.refresh(memo)
    
    # Create workflow steps
    # Step 0 is always Author
    step_0 = models.MemoWorkflowStep(
        memo_id=memo.id,
        step_index=0,
        step_type="author",
        role_name="Author / Submitter",
        assigned_user_id=current_user.id,
        status="pending",
        is_current=True
    )
    db.add(step_0)
    
    if memo_in.workflow_steps:
        for idx, s in enumerate(memo_in.workflow_steps, start=1):
            # Verify assigned user belongs to same org
            u = db.query(models.User).filter(models.User.id == s.assigned_user_id, models.User.org_id == current_user.org_id).first()
            if not u:
                raise HTTPException(status_code=400, detail=f"Invalid participant user ID #{s.assigned_user_id}")
                
            w_step = models.MemoWorkflowStep(
                memo_id=memo.id,
                step_index=idx,
                step_type=s.step_type,
                role_name=s.role_name,
                assigned_user_id=s.assigned_user_id,
                status="pending",
                is_current=False
            )
            db.add(w_step)
    
    db.commit()
    db.refresh(memo)
    
    audit_service.log_event(
        db=db,
        org_id=memo.org_id,
        user_id=current_user.id,
        event_type="MEMO_CREATE",
        object_type="Memo",
        object_id=str(memo.id),
        description=f"Memo '{memo.memo_number}' created ({'Draft' if memo_in.is_draft else 'Submitted'}) by {current_user.full_name}",
        ip_address=request.client.host if request.client else None
    )
    
    # If not draft, submit into workflow
    if not memo_in.is_draft:
        workflow_service.submit_memo(db, memo, current_user, ip_address=request.client.host if request.client else None)
        
    return memo


@router.get("/inbox", response_model=List[schemas.MemoOut])
def get_inbox_memos(
    priority: Optional[str] = None,
    sort_by: Optional[str] = "date_desc",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns memos awaiting current user's action or delegated action.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Active delegations where current user is delegatee
    delegations = db.query(models.WorkflowDelegation).filter(
        models.WorkflowDelegation.org_id == current_user.org_id,
        models.WorkflowDelegation.delegatee_id == current_user.id,
        models.WorkflowDelegation.is_active == True,
        models.WorkflowDelegation.start_date <= now,
        models.WorkflowDelegation.end_date >= now
    ).all()
    delegator_ids = [d.delegator_id for d in delegations]
    
    target_user_ids = [current_user.id] + delegator_ids
    
    query = db.query(models.Memo).filter(
        models.Memo.org_id == current_user.org_id,
        models.Memo.status.in_(["Pending Approval", "Pending Review", "Changes Requested"]),
        models.Memo.current_assignee_id.in_(target_user_ids)
    )
    
    if priority:
        query = query.filter(models.Memo.priority == priority)
        
    if sort_by == "priority":
        query = query.order_by(desc(models.Memo.priority == "Urgent"), desc(models.Memo.priority == "High"), desc(models.Memo.created_at))
    else:
        query = query.order_by(desc(models.Memo.submitted_at), desc(models.Memo.created_at))
        
    return query.all()


@router.get("/sent", response_model=List[schemas.MemoOut])
def get_sent_memos(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns memos created or submitted by the current user.
    """
    memos = db.query(models.Memo).filter(
        models.Memo.org_id == current_user.org_id,
        models.Memo.author_id == current_user.id,
        models.Memo.status != "Draft"
    ).order_by(desc(models.Memo.created_at)).all()
    return memos


@router.get("/drafts", response_model=List[schemas.MemoOut])
def get_draft_memos(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns draft memos created by the current user.
    """
    memos = db.query(models.Memo).filter(
        models.Memo.org_id == current_user.org_id,
        models.Memo.author_id == current_user.id,
        models.Memo.status == "Draft"
    ).order_by(desc(models.Memo.created_at)).all()
    return memos


@router.get("/completed", response_model=List[schemas.MemoOut])
def get_completed_memos(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns completed/approved/rejected memos accessible to the user.
    """
    query = db.query(models.Memo).filter(
        models.Memo.org_id == current_user.org_id,
        models.Memo.status.in_(["Approved", "Rejected"])
    )
    
    if current_user.role != "admin":
        memos = query.order_by(desc(models.Memo.updated_at)).all()
        return [m for m in memos if verify_memo_access(m, current_user, db)]
    
    return query.order_by(desc(models.Memo.updated_at)).all()


@router.get("/all", response_model=List[schemas.MemoOut])
def get_all_memos_search(
    q: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    department_id: Optional[int] = None,
    category_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Comprehensive search and filter across memos respecting tenant and permission boundaries.
    """
    query = db.query(models.Memo).filter(models.Memo.org_id == current_user.org_id)
    
    if q and q.strip():
        search_term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.Memo.memo_number.ilike(search_term),
                models.Memo.title.ilike(search_term),
                models.Memo.body.ilike(search_term)
            )
        )
        
    if status and status != "All":
        query = query.filter(models.Memo.status == status)
    if priority and priority != "All":
        query = query.filter(models.Memo.priority == priority)
    if department_id:
        query = query.filter(models.Memo.department_id == department_id)
    if category_id:
        query = query.filter(models.Memo.category_id == category_id)
    if date_from:
        try:
            d_from = datetime.datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(models.Memo.created_at >= d_from)
        except Exception:
            pass
    if date_to:
        try:
            d_to = datetime.datetime.strptime(date_to, "%Y-%m-%d") + datetime.timedelta(days=1)
            query = query.filter(models.Memo.created_at <= d_to)
        except Exception:
            pass
            
    all_results = query.order_by(desc(models.Memo.created_at)).all()
    
    if current_user.role != "admin":
        return [m for m in all_results if verify_memo_access(m, current_user, db)]
    return all_results


@router.get("/{memo_id}", response_model=schemas.MemoOut)
def get_memo_detail(
    memo_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id, models.Memo.org_id == current_user.org_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
        
    if not verify_memo_access(memo, current_user, db):
        raise HTTPException(status_code=403, detail="Unauthorized to view this memo")
        
    return memo


@router.put("/{memo_id}", response_model=schemas.MemoOut)
def update_memo(
    memo_id: int,
    memo_update: schemas.MemoUpdate,
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id, models.Memo.org_id == current_user.org_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
        
    if memo.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only the author or an admin can edit this memo")
        
    if memo.status not in ["Draft", "Changes Requested"]:
        raise HTTPException(status_code=400, detail=f"Cannot edit memo in status '{memo.status}'")
        
    if memo_update.title is not None:
        memo.title = memo_update.title.strip()
    if memo_update.body is not None:
        memo.body = memo_update.body.strip()
    if memo_update.category_id is not None:
        memo.category_id = memo_update.category_id
    if memo_update.department_id is not None:
        memo.department_id = memo_update.department_id
    if memo_update.priority is not None:
        memo.priority = memo_update.priority
        
    if memo.status == "Draft" and memo_update.workflow_steps is not None:
        db.query(models.MemoWorkflowStep).filter(models.MemoWorkflowStep.memo_id == memo.id).delete()
        
        step_0 = models.MemoWorkflowStep(
            memo_id=memo.id,
            step_index=0,
            step_type="author",
            role_name="Author / Submitter",
            assigned_user_id=current_user.id,
            status="pending",
            is_current=True
        )
        db.add(step_0)
        
        for idx, s in enumerate(memo_update.workflow_steps, start=1):
            w_step = models.MemoWorkflowStep(
                memo_id=memo.id,
                step_index=idx,
                step_type=s.step_type,
                role_name=s.role_name,
                assigned_user_id=s.assigned_user_id,
                status="pending",
                is_current=False
            )
            db.add(w_step)
            
    db.commit()
    db.refresh(memo)
    
    audit_service.log_event(
        db=db,
        org_id=memo.org_id,
        user_id=current_user.id,
        event_type="MEMO_UPDATE",
        object_type="Memo",
        object_id=str(memo.id),
        description=f"Memo '{memo.memo_number}' modified by {current_user.full_name}",
        ip_address=request.client.host if request.client else None
    )
    return memo


@router.delete("/{memo_id}")
def delete_draft_memo(
    memo_id: int,
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id, models.Memo.org_id == current_user.org_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
        
    if memo.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only the author or an admin can delete this memo")
        
    if memo.status != "Draft":
        raise HTTPException(status_code=400, detail="Only draft memos can be deleted")
        
    db.delete(memo)
    db.commit()
    
    audit_service.log_event(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        event_type="MEMO_DELETE",
        object_type="Memo",
        object_id=str(memo_id),
        description=f"Draft memo '{memo.memo_number}' deleted by {current_user.full_name}",
        ip_address=request.client.host if request.client else None
    )
    return {"message": "Draft memo deleted successfully"}


@router.post("/{memo_id}/submit", response_model=schemas.MemoOut)
def submit_draft_memo(
    memo_id: int,
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id, models.Memo.org_id == current_user.org_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
        
    return workflow_service.submit_memo(db, memo, current_user, ip_address=request.client.host if request.client else None)


@router.post("/{memo_id}/resubmit", response_model=schemas.MemoOut)
def resubmit_memo(
    memo_id: int,
    memo_update: schemas.MemoUpdate,
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id, models.Memo.org_id == current_user.org_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
        
    if memo_update.title is not None:
        memo.title = memo_update.title.strip()
    if memo_update.body is not None:
        memo.body = memo_update.body.strip()
    if memo_update.category_id is not None:
        memo.category_id = memo_update.category_id
    if memo_update.department_id is not None:
        memo.department_id = memo_update.department_id
    if memo_update.priority is not None:
        memo.priority = memo_update.priority
        
    db.commit()
    db.refresh(memo)
    
    return workflow_service.resubmit_memo_after_changes(
        db=db,
        memo=memo,
        user=current_user,
        summary_of_changes=memo_update.summary_of_changes,
        ip_address=request.client.host if request.client else None
    )


@router.post("/{memo_id}/attachments", response_model=schemas.AttachmentOut)
async def upload_attachment(
    memo_id: int,
    file: UploadFile = File(...),
    request: Request = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id, models.Memo.org_id == current_user.org_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
        
    if not verify_memo_access(memo, current_user, db):
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File extension '.{ext}' is not allowed")
        
    stored_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)
    
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds maximum allowed size of 25MB")
        
    with open(file_path, "wb") as f:
        f.write(content)
        
    attachment = models.MemoAttachment(
        memo_id=memo.id,
        org_id=current_user.org_id,
        uploaded_by_user_id=current_user.id,
        file_name=stored_name,
        original_name=file.filename,
        file_size=len(content),
        file_type=file.content_type or ext,
        storage_path=file_path
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    
    audit_service.log_event(
        db=db,
        org_id=memo.org_id,
        user_id=current_user.id,
        event_type="ATTACHMENT_UPLOAD",
        object_type="MemoAttachment",
        object_id=str(attachment.id),
        description=f"File '{file.filename}' ({len(content)} bytes) uploaded to memo '{memo.memo_number}'",
        ip_address=request.client.host if request and request.client else None
    )
    return attachment


@router.get("/{memo_id}/attachments/{attachment_id}")
def download_attachment(
    memo_id: int,
    attachment_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id, models.Memo.org_id == current_user.org_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
        
    if not verify_memo_access(memo, current_user, db):
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    att = db.query(models.MemoAttachment).filter(
        models.MemoAttachment.id == attachment_id,
        models.MemoAttachment.memo_id == memo.id,
        models.MemoAttachment.org_id == current_user.org_id
    ).first()
    
    if not att or not os.path.exists(att.storage_path):
        raise HTTPException(status_code=404, detail="Attachment file not found")
        
    return FileResponse(
        path=att.storage_path,
        filename=att.original_name,
        media_type=att.file_type or "application/octet-stream"
    )


@router.delete("/{memo_id}/attachments/{attachment_id}")
def delete_attachment(
    memo_id: int,
    attachment_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id, models.Memo.org_id == current_user.org_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
        
    att = db.query(models.MemoAttachment).filter(
        models.MemoAttachment.id == attachment_id,
        models.MemoAttachment.memo_id == memo.id,
        models.MemoAttachment.org_id == current_user.org_id
    ).first()
    
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
        
    if att.uploaded_by_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only uploader or admin can delete attachment")
        
    if os.path.exists(att.storage_path):
        try:
            os.remove(att.storage_path)
        except Exception:
            pass
            
    db.delete(att)
    db.commit()
    return {"message": "Attachment deleted"}


@router.get("/{memo_id}/pdf")
def export_memo_pdf(
    memo_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id, models.Memo.org_id == current_user.org_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
        
    if not verify_memo_access(memo, current_user, db):
        raise HTTPException(status_code=403, detail="Unauthorized to export this memo")
        
    org = db.query(models.Organization).filter(models.Organization.id == current_user.org_id).first()
    pdf_buffer = pdf_service.generate_memo_pdf(memo, org)
    
    filename = f"{memo.memo_number}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/{memo_id}/comments", response_model=schemas.CommentOut)
def add_comment(
    memo_id: int,
    comment_in: schemas.CommentCreate,
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id, models.Memo.org_id == current_user.org_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
        
    if not verify_memo_access(memo, current_user, db):
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    comment = models.MemoComment(
        memo_id=memo.id,
        org_id=current_user.org_id,
        user_id=current_user.id,
        comment_type=comment_in.comment_type,
        text=comment_in.text.strip()
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    if memo.author_id != current_user.id:
        notification_service.create_notification(
            db=db,
            org_id=memo.org_id,
            user_id=memo.author_id,
            memo_id=memo.id,
            title="New Comment on Memo",
            message=f"{current_user.full_name} commented on memo '{memo.memo_number}': {comment.text[:100]}",
            event_type="comment_added"
        )
        
    audit_service.log_event(
        db=db,
        org_id=memo.org_id,
        user_id=current_user.id,
        event_type="COMMENT_ADD",
        object_type="MemoComment",
        object_id=str(comment.id),
        description=f"Comment added on memo '{memo.memo_number}' by {current_user.full_name}",
        ip_address=request.client.host if request.client else None
    )
    return comment
