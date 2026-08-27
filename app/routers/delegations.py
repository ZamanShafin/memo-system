import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, security
from app.services import audit_service

router = APIRouter(prefix="/delegations", tags=["Delegations"])

@router.get("", response_model=List[schemas.DelegationOut])
def list_my_delegations(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns delegations created by current user or assigned to current user.
    """
    delegations = db.query(models.WorkflowDelegation).filter(
        models.WorkflowDelegation.org_id == current_user.org_id,
        (models.WorkflowDelegation.delegator_id == current_user.id) | (models.WorkflowDelegation.delegatee_id == current_user.id)
    ).order_by(models.WorkflowDelegation.created_at.desc()).all()
    return delegations


@router.post("", response_model=schemas.DelegationOut)
def create_delegation(
    delegation_in: schemas.DelegationCreate,
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Designates another user in the organization as delegate for a time window.
    """
    if delegation_in.delegatee_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delegate to yourself")
        
    delegatee = db.query(models.User).filter(
        models.User.id == delegation_in.delegatee_id,
        models.User.org_id == current_user.org_id,
        models.User.is_active == True
    ).first()
    
    if not delegatee:
        raise HTTPException(status_code=404, detail="Delegate user not found or inactive")
        
    if delegation_in.end_date <= delegation_in.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
        
    delegation = models.WorkflowDelegation(
        org_id=current_user.org_id,
        delegator_id=current_user.id,
        delegatee_id=delegatee.id,
        start_date=delegation_in.start_date,
        end_date=delegation_in.end_date,
        reason=delegation_in.reason,
        is_active=True
    )
    db.add(delegation)
    db.commit()
    db.refresh(delegation)
    
    audit_service.log_event(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        event_type="DELEGATION_CREATE",
        object_type="WorkflowDelegation",
        object_id=str(delegation.id),
        description=f"Delegation created: {current_user.full_name} delegated authority to {delegatee.full_name} from {delegation.start_date.strftime('%Y-%m-%d')} to {delegation.end_date.strftime('%Y-%m-%d')}",
        ip_address=request.client.host if request.client else None
    )
    return delegation


@router.put("/{delegation_id}", response_model=schemas.DelegationOut)
def update_delegation(
    delegation_id: int,
    delegation_up: schemas.DelegationUpdate,
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    delegation = db.query(models.WorkflowDelegation).filter(
        models.WorkflowDelegation.id == delegation_id,
        models.WorkflowDelegation.org_id == current_user.org_id
    ).first()
    
    if not delegation:
        raise HTTPException(status_code=404, detail="Delegation not found")
        
    if delegation.delegator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only delegator or admin can update delegation")
        
    if delegation_up.is_active is not None:
        delegation.is_active = delegation_up.is_active
    if delegation_up.reason is not None:
        delegation.reason = delegation_up.reason
        
    db.commit()
    db.refresh(delegation)
    
    audit_service.log_event(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        event_type="DELEGATION_UPDATE",
        object_type="WorkflowDelegation",
        object_id=str(delegation.id),
        description=f"Delegation #{delegation.id} status updated to active={delegation.is_active}",
        ip_address=request.client.host if request.client else None
    )
    return delegation


@router.delete("/{delegation_id}")
def delete_delegation(
    delegation_id: int,
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    delegation = db.query(models.WorkflowDelegation).filter(
        models.WorkflowDelegation.id == delegation_id,
        models.WorkflowDelegation.org_id == current_user.org_id
    ).first()
    
    if not delegation:
        raise HTTPException(status_code=404, detail="Delegation not found")
        
    if delegation.delegator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only delegator or admin can delete delegation")
        
    db.delete(delegation)
    db.commit()
    
    audit_service.log_event(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        event_type="DELEGATION_DELETE",
        object_type="WorkflowDelegation",
        object_id=str(delegation_id),
        description=f"Delegation #{delegation_id} removed",
        ip_address=request.client.host if request.client else None
    )
    return {"message": "Delegation removed successfully"}
