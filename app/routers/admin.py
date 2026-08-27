import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models, schemas, security
from app.services import audit_service

router = APIRouter(prefix="/admin", tags=["Organization Administration"])

# --- Organization Settings ---
@router.get("/organization", response_model=schemas.OrganizationOut)
def get_organization_details(
    admin_user: models.User = Depends(security.get_current_active_admin),
    db: Session = Depends(get_db)
):
    org = db.query(models.Organization).filter(models.Organization.id == admin_user.org_id).first()
    return org

@router.put("/organization", response_model=schemas.OrganizationOut)
def update_organization_details(
    org_up: schemas.OrganizationUpdate,
    request: Request,
    admin_user: models.User = Depends(security.get_current_active_admin),
    db: Session = Depends(get_db)
):
    org = db.query(models.Organization).filter(models.Organization.id == admin_user.org_id).first()
    if org_up.name is not None:
        org.name = org_up.name.strip()
    if org_up.logo_url is not None:
        org.logo_url = org_up.logo_url
    if org_up.contact_email is not None:
        org.contact_email = org_up.contact_email
    if org_up.contact_phone is not None:
        org.contact_phone = org_up.contact_phone
    if org_up.address is not None:
        org.address = org_up.address
    if org_up.settings_json is not None:
        org.settings_json = org_up.settings_json
        
    db.commit()
    db.refresh(org)
    
    audit_service.log_event(
        db=db,
        org_id=org.id,
        user_id=admin_user.id,
        event_type="ORGANIZATION_UPDATE",
        object_type="Organization",
        object_id=str(org.id),
        description=f"Organization settings updated by {admin_user.full_name}",
        ip_address=request.client.host if request.client else None
    )
    return org


# --- User Management ---
@router.get("/users", response_model=List[schemas.UserOut])
def list_organization_users(
    department_id: Optional[int] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists users belonging to the active organization (regular users can also list active users to select workflow participants).
    """
    query = db.query(models.User).filter(models.User.org_id == current_user.org_id)
    if department_id:
        query = query.filter(models.User.department_id == department_id)
    if role:
        query = query.filter(models.User.role == role)
    if is_active is not None:
        query = query.filter(models.User.is_active == is_active)
        
    return query.order_by(models.User.full_name).all()


@router.post("/users", response_model=schemas.UserOut)
def create_organization_user(
    user_in: schemas.UserCreate,
    request: Request,
    admin_user: models.User = Depends(security.get_current_active_admin),
    db: Session = Depends(get_db)
):
    # Check if email exists in this org
    existing = db.query(models.User).filter(
        models.User.org_id == admin_user.org_id,
        models.User.email == user_in.email.lower().strip()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists in organization")
        
    if user_in.department_id:
        dept = db.query(models.Department).filter(
            models.Department.id == user_in.department_id,
            models.Department.org_id == admin_user.org_id
        ).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Invalid department specified")
            
    user = models.User(
        org_id=admin_user.org_id,
        department_id=user_in.department_id,
        email=user_in.email.lower().strip(),
        password_hash=security.get_password_hash(user_in.password),
        full_name=user_in.full_name.strip(),
        designation=user_in.designation,
        role=user_in.role if user_in.role in ["admin", "user"] else "user",
        is_active=user_in.is_active
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    audit_service.log_event(
        db=db,
        org_id=admin_user.org_id,
        user_id=admin_user.id,
        event_type="USER_CREATE",
        object_type="User",
        object_id=str(user.id),
        description=f"User {user.full_name} ({user.email}) created with role '{user.role}'",
        ip_address=request.client.host if request.client else None
    )
    return user


@router.put("/users/{user_id}", response_model=schemas.UserOut)
def update_organization_user(
    user_id: int,
    user_up: schemas.UserUpdate,
    request: Request,
    admin_user: models.User = Depends(security.get_current_active_admin),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.org_id == admin_user.org_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user_up.email is not None:
        user.email = user_up.email.lower().strip()
    if user_up.password is not None and user_up.password.strip():
        user.password_hash = security.get_password_hash(user_up.password)
    if user_up.full_name is not None:
        user.full_name = user_up.full_name.strip()
    if user_up.designation is not None:
        user.designation = user_up.designation.strip()
    if user_up.department_id is not None:
        user.department_id = user_up.department_id if user_up.department_id > 0 else None
    if user_up.role is not None:
        user.role = user_up.role
    if user_up.is_active is not None:
        user.is_active = user_up.is_active
        
    db.commit()
    db.refresh(user)
    
    audit_service.log_event(
        db=db,
        org_id=admin_user.org_id,
        user_id=admin_user.id,
        event_type="USER_UPDATE",
        object_type="User",
        object_id=str(user.id),
        description=f"User {user.full_name} updated by admin {admin_user.full_name}. Active status: {user.is_active}",
        ip_address=request.client.host if request.client else None
    )
    return user


# --- Department Management ---
@router.get("/departments", response_model=List[schemas.DepartmentOut])
def list_departments(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    depts = db.query(models.Department).filter(
        models.Department.org_id == current_user.org_id
    ).order_by(models.Department.name).all()
    
    # Enrich with user counts
    results = []
    for d in depts:
        u_count = db.query(models.User).filter(models.User.department_id == d.id).count()
        d_out = schemas.DepartmentOut(
            id=d.id,
            org_id=d.org_id,
            name=d.name,
            description=d.description,
            is_active=d.is_active,
            created_at=d.created_at,
            user_count=u_count
        )
        results.append(d_out)
    return results


@router.post("/departments", response_model=schemas.DepartmentOut)
def create_department(
    dept_in: schemas.DepartmentCreate,
    request: Request,
    admin_user: models.User = Depends(security.get_current_active_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(models.Department).filter(
        models.Department.org_id == admin_user.org_id,
        models.Department.name.ilike(dept_in.name.strip())
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department with this name already exists")
        
    dept = models.Department(
        org_id=admin_user.org_id,
        name=dept_in.name.strip(),
        description=dept_in.description
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    
    audit_service.log_event(
        db=db,
        org_id=admin_user.org_id,
        user_id=admin_user.id,
        event_type="DEPARTMENT_CREATE",
        object_type="Department",
        object_id=str(dept.id),
        description=f"Department '{dept.name}' created",
        ip_address=request.client.host if request.client else None
    )
    return dept


@router.put("/departments/{dept_id}", response_model=schemas.DepartmentOut)
def update_department(
    dept_id: int,
    dept_up: schemas.DepartmentUpdate,
    request: Request,
    admin_user: models.User = Depends(security.get_current_active_admin),
    db: Session = Depends(get_db)
):
    dept = db.query(models.Department).filter(
        models.Department.id == dept_id,
        models.Department.org_id == admin_user.org_id
    ).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
        
    if dept_up.name is not None:
        new_name = dept_up.name.strip()
        existing = db.query(models.Department).filter(
            models.Department.org_id == admin_user.org_id,
            models.Department.id != dept.id,
            models.Department.name.ilike(new_name)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Department with this name already exists")
        dept.name = new_name
    if dept_up.description is not None:
        dept.description = dept_up.description
    if dept_up.is_active is not None:
        dept.is_active = dept_up.is_active
        
    db.commit()
    db.refresh(dept)
    
    audit_service.log_event(
        db=db,
        org_id=admin_user.org_id,
        user_id=admin_user.id,
        event_type="DEPARTMENT_UPDATE",
        object_type="Department",
        object_id=str(dept.id),
        description=f"Department '{dept.name}' updated (Active: {dept.is_active})",
        ip_address=request.client.host if request.client else None
    )
    return dept


# --- Memo Category Management ---
@router.get("/categories", response_model=List[schemas.MemoCategoryOut])
def list_categories(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    cats = db.query(models.MemoCategory).filter(
        models.MemoCategory.org_id == current_user.org_id
    ).order_by(models.MemoCategory.name).all()
    return cats


@router.post("/categories", response_model=schemas.MemoCategoryOut)
def create_category(
    cat_in: schemas.MemoCategoryCreate,
    request: Request,
    admin_user: models.User = Depends(security.get_current_active_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(models.MemoCategory).filter(
        models.MemoCategory.org_id == admin_user.org_id,
        models.MemoCategory.name.ilike(cat_in.name.strip())
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name already exists")
        
    cat = models.MemoCategory(
        org_id=admin_user.org_id,
        name=cat_in.name.strip(),
        description=cat_in.description
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    
    audit_service.log_event(
        db=db,
        org_id=admin_user.org_id,
        user_id=admin_user.id,
        event_type="CATEGORY_CREATE",
        object_type="MemoCategory",
        object_id=str(cat.id),
        description=f"Memo category '{cat.name}' created",
        ip_address=request.client.host if request.client else None
    )
    return cat


@router.put("/categories/{cat_id}", response_model=schemas.MemoCategoryOut)
def update_category(
    cat_id: int,
    cat_up: schemas.MemoCategoryUpdate,
    request: Request,
    admin_user: models.User = Depends(security.get_current_active_admin),
    db: Session = Depends(get_db)
):
    cat = db.query(models.MemoCategory).filter(
        models.MemoCategory.id == cat_id,
        models.MemoCategory.org_id == admin_user.org_id
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
        
    if cat_up.name is not None:
        new_name = cat_up.name.strip()
        existing = db.query(models.MemoCategory).filter(
            models.MemoCategory.org_id == admin_user.org_id,
            models.MemoCategory.id != cat.id,
            models.MemoCategory.name.ilike(new_name)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Category with this name already exists")
        cat.name = new_name
    if cat_up.description is not None:
        cat.description = cat_up.description
    if cat_up.is_active is not None:
        cat.is_active = cat_up.is_active
        
    db.commit()
    db.refresh(cat)
    return cat


# --- Reusable Workflow Templates ---
@router.get("/templates", response_model=List[schemas.WorkflowTemplateOut])
def list_workflow_templates(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    templates = db.query(models.WorkflowTemplate).filter(
        models.WorkflowTemplate.org_id == current_user.org_id
    ).order_by(models.WorkflowTemplate.name).all()
    return templates


@router.post("/templates", response_model=schemas.WorkflowTemplateOut)
def create_workflow_template(
    tmpl_in: schemas.WorkflowTemplateCreate,
    request: Request,
    admin_user: models.User = Depends(security.get_current_active_admin),
    db: Session = Depends(get_db)
):
    steps_data = [s.model_dump() for s in tmpl_in.steps]
    tmpl = models.WorkflowTemplate(
        org_id=admin_user.org_id,
        name=tmpl_in.name.strip(),
        description=tmpl_in.description,
        steps_json=json.dumps(steps_data)
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    
    audit_service.log_event(
        db=db,
        org_id=admin_user.org_id,
        user_id=admin_user.id,
        event_type="TEMPLATE_CREATE",
        object_type="WorkflowTemplate",
        object_id=str(tmpl.id),
        description=f"Workflow template '{tmpl.name}' created with {len(steps_data)} steps",
        ip_address=request.client.host if request.client else None
    )
    return tmpl


@router.put("/templates/{tmpl_id}", response_model=schemas.WorkflowTemplateOut)
def update_workflow_template(
    tmpl_id: int,
    tmpl_up: schemas.WorkflowTemplateUpdate,
    request: Request,
    admin_user: models.User = Depends(security.get_current_active_admin),
    db: Session = Depends(get_db)
):
    tmpl = db.query(models.WorkflowTemplate).filter(
        models.WorkflowTemplate.id == tmpl_id,
        models.WorkflowTemplate.org_id == admin_user.org_id
    ).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
        
    if tmpl_up.name is not None:
        tmpl.name = tmpl_up.name.strip()
    if tmpl_up.description is not None:
        tmpl.description = tmpl_up.description
    if tmpl_up.steps is not None:
        steps_data = [s.model_dump() for s in tmpl_up.steps]
        tmpl.steps_json = json.dumps(steps_data)
    if tmpl_up.is_active is not None:
        tmpl.is_active = tmpl_up.is_active
        
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.delete("/templates/{tmpl_id}")
def delete_workflow_template(
    tmpl_id: int,
    admin_user: models.User = Depends(security.get_current_active_admin),
    db: Session = Depends(get_db)
):
    tmpl = db.query(models.WorkflowTemplate).filter(
        models.WorkflowTemplate.id == tmpl_id,
        models.WorkflowTemplate.org_id == admin_user.org_id
    ).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tmpl)
    db.commit()
    return {"message": "Workflow template deleted"}
