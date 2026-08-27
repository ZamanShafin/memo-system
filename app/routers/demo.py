from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session

from app.database import get_db, Base, engine
from app import models, schemas, security
from app.seed import seed_database

router = APIRouter(prefix="/demo", tags=["Demo & Evaluation"])

@router.get("/accounts")
def get_demo_accounts(db: Session = Depends(get_db)):
    """
    Returns pre-configured demonstration accounts across multiple tenants.
    """
    orgs = db.query(models.Organization).order_by(models.Organization.name).all()
    result = []
    
    for org in orgs:
        users = db.query(models.User).filter(
            models.User.org_id == org.id,
            models.User.is_active == True
        ).order_by(models.User.role.desc(), models.User.full_name).all()
        
        u_list = []
        for u in users:
            dept_name = u.department.name if u.department else "General"
            u_list.append({
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "designation": u.designation,
                "role": u.role,
                "department": dept_name,
                "password": "password123"  # Standard demo password
            })
            
        result.append({
            "org_id": org.id,
            "org_name": org.name,
            "org_code": org.code,
            "logo_url": org.logo_url,
            "users": u_list
        })
        
    return result


@router.post("/quick-login/{user_id}")
def quick_login(
    user_id: int,
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Instantly logs in as the selected demo user for effortless grading/testing.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    org = db.query(models.Organization).filter(models.Organization.id == user.org_id).first()
    
    access_token = security.create_access_token(
        data={"sub": str(user.id), "org_id": user.org_id, "role": user.role}
    )
    
    response.set_cookie(
        key="memo_session",
        value=access_token,
        httponly=True,
        max_age=60 * 60 * 24,
        samesite="lax"
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": schemas.UserOut.model_validate(user),
        "organization": schemas.OrganizationOut.model_validate(org)
    }


@router.post("/reset-seed")
def reset_database(db: Session = Depends(get_db)):
    """
    Resets the database and re-seeds rich demonstration data.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()
    return {"message": "Database reset and seeded successfully"}
