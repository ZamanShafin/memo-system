from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_db
from app import models, schemas, security
from app.services import workflow_service
from app.routers.memos import MEMO_EAGER_LOAD

router = APIRouter(prefix="/workflow", tags=["Workflow Engine"])

@router.post("/{memo_id}/action", response_model=schemas.MemoOut)
def execute_workflow_action(
    memo_id: int,
    action_req: schemas.WorkflowActionRequest,
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes a workflow action (approve, reject, request_changes, forward) on the current step.
    Strictly verifies sequential order and participant turn (or active delegate).
    """
    memo = db.query(models.Memo).filter(
        models.Memo.id == memo_id,
        models.Memo.org_id == current_user.org_id
    ).first()
    
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
        
    workflow_service.process_workflow_action(
        db=db,
        memo=memo,
        user=current_user,
        action=action_req.action,
        comment=action_req.comment,
        ip_address=request.client.host if request.client else None
    )

    # Re-query with eager-loading for instant response serialization
    updated_memo = db.query(models.Memo).options(*MEMO_EAGER_LOAD).filter(
        models.Memo.id == memo_id
    ).first()
    
    return updated_memo

@router.get("/{memo_id}/steps", response_model=List[schemas.WorkflowStepOut])
def get_memo_workflow_steps(
    memo_id: int,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(models.Memo).filter(
        models.Memo.id == memo_id,
        models.Memo.org_id == current_user.org_id
    ).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
        
    steps = db.query(models.MemoWorkflowStep).filter(
        models.MemoWorkflowStep.memo_id == memo.id
    ).order_by(models.MemoWorkflowStep.step_index).all()
    
    return steps
