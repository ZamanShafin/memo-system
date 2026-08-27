from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app import models, schemas, security
from app.services import audit_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=schemas.Token)
def login(
    login_data: schemas.LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    # Find organization by code
    org = db.query(models.Organization).filter(
        models.Organization.code == login_data.org_code.lower().strip()
    ).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid organization identifier"
        )
    
    # Find user within tenant
    user = db.query(models.User).filter(
        models.User.org_id == org.id,
        models.User.email == login_data.email.lower().strip()
    ).first()
    
    if not user or not security.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact organization administrator."
        )
    
    # Create token
    access_token = security.create_access_token(
        data={"sub": str(user.id), "org_id": org.id, "role": user.role}
    )
    
    # Set secure cookie
    response.set_cookie(
        key="memo_session",
        value=access_token,
        httponly=True,
        max_age=60 * 60 * 24,
        samesite="lax"
    )
    
    audit_service.log_event(
        db=db,
        org_id=org.id,
        user_id=user.id,
        event_type="LOGIN",
        object_type="User",
        object_id=str(user.id),
        description=f"User {user.full_name} ({user.email}) logged in",
        ip_address=request.client.host if request.client else None
    )
    
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=user,
        organization=org
    )


@router.post("/logout")
def logout(
    response: Response,
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    response.delete_cookie(key="memo_session")
    audit_service.log_event(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        event_type="LOGOUT",
        object_type="User",
        object_id=str(current_user.id),
        description=f"User {current_user.full_name} logged out",
        ip_address=request.client.host if request.client else None
    )
    return {"message": "Successfully logged out"}


@router.get("/me")
def get_me(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    org = db.query(models.Organization).filter(models.Organization.id == current_user.org_id).first()
    dept = db.query(models.Department).filter(models.Department.id == current_user.department_id).first() if current_user.department_id else None
    return {
        "user": schemas.UserOut.model_validate(current_user),
        "organization": schemas.OrganizationOut.model_validate(org),
        "department": schemas.DepartmentOut.model_validate(dept) if dept else None
    }


@router.put("/profile", response_model=schemas.UserOut)
def update_profile(
    profile_data: schemas.UserProfileUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    if profile_data.full_name is not None:
        current_user.full_name = profile_data.full_name.strip()
    if profile_data.designation is not None:
        current_user.designation = profile_data.designation.strip()
    if profile_data.department_id is not None:
        # Validate department belongs to same org
        if profile_data.department_id > 0:
            dept = db.query(models.Department).filter(
                models.Department.id == profile_data.department_id,
                models.Department.org_id == current_user.org_id
            ).first()
            if not dept:
                raise HTTPException(status_code=400, detail="Invalid department")
            current_user.department_id = dept.id
        else:
            current_user.department_id = None
    if profile_data.avatar_url is not None:
        current_user.avatar_url = profile_data.avatar_url
        
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
def change_password(
    pwd_data: schemas.PasswordChangeRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    if not security.verify_password(pwd_data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    
    if len(pwd_data.new_password) < 4:
        raise HTTPException(status_code=400, detail="New password must be at least 4 characters")
        
    current_user.password_hash = security.get_password_hash(pwd_data.new_password)
    db.commit()
    
    audit_service.log_event(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        event_type="PASSWORD_CHANGE",
        object_type="User",
        object_id=str(current_user.id),
        description=f"User {current_user.full_name} changed their password"
    )
    return {"message": "Password updated successfully"}


@router.post("/reset-password")
def reset_password(
    reset_data: schemas.PasswordResetRequest,
    db: Session = Depends(get_db)
):
    org = db.query(models.Organization).filter(
        models.Organization.code == reset_data.org_code.lower().strip()
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    user = db.query(models.User).filter(
        models.User.org_id == org.id,
        models.User.email == reset_data.email.lower().strip()
    ).first()
    
    if not user:
        # Avoid user enumeration in real prod, but return clean message
        raise HTTPException(status_code=404, detail="User account not found in this organization")
        
    user.password_hash = security.get_password_hash(reset_data.new_password)
    db.commit()
    
    audit_service.log_event(
        db=db,
        org_id=org.id,
        user_id=user.id,
        event_type="PASSWORD_RESET",
        object_type="User",
        object_id=str(user.id),
        description=f"Password reset completed for {user.full_name}"
    )
    return {"message": "Password has been successfully reset"}


@router.post("/register-organization")
def register_organization(
    org_data: schemas.OrganizationCreate,
    db: Session = Depends(get_db)
):
    # Check if org code already taken
    existing_org = db.query(models.Organization).filter(
        models.Organization.code == org_data.code.lower().strip()
    ).first()
    if existing_org:
        raise HTTPException(status_code=400, detail="Organization identifier already in use")
        
    org = models.Organization(
        name=org_data.name.strip(),
        code=org_data.code.lower().strip(),
        logo_url=org_data.logo_url,
        contact_email=org_data.contact_email,
        contact_phone=org_data.contact_phone,
        address=org_data.address
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    
    # Create Default Departments
    default_depts = ["Administration", "Finance & Accounts", "Human Resources", "Procurement", "Information Technology"]
    first_dept = None
    for d_name in default_depts:
        d = models.Department(org_id=org.id, name=d_name, description=f"{d_name} Department")
        db.add(d)
        db.commit()
        db.refresh(d)
        if first_dept is None:
            first_dept = d
            
    # Create Default Categories
    default_cats = ["Administrative", "Financial", "Procurement", "HR", "Academic", "Technical", "General"]
    for c_name in default_cats:
        c = models.MemoCategory(org_id=org.id, name=c_name, description=f"{c_name} category memos")
        db.add(c)
        
    # Create Admin User
    admin_user = models.User(
        org_id=org.id,
        department_id=first_dept.id if first_dept else None,
        email=org_data.admin_email.lower().strip(),
        password_hash=security.get_password_hash(org_data.admin_password),
        full_name=org_data.admin_name.strip(),
        designation="Organization Administrator",
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    audit_service.log_event(
        db=db,
        org_id=org.id,
        user_id=admin_user.id,
        event_type="ORGANIZATION_CREATE",
        object_type="Organization",
        object_id=str(org.id),
        description=f"New organization '{org.name}' ({org.code}) created with admin {admin_user.full_name}"
    )
    
    return {"message": "Organization created successfully", "organization": org, "admin_email": admin_user.email}
