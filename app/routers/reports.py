import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, security
from app.services import reporting_service

router = APIRouter(prefix="/reports", tags=["Reporting & Analytics"])

@router.get("/statistics", response_model=schemas.ReportingStatsOut)
def get_reports(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    department_id: Optional[int] = None,
    category_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    d_start = None
    if start_date:
        try:
            d_start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        except Exception:
            pass
            
    d_end = None
    if end_date:
        try:
            d_end = datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        except Exception:
            pass
            
    stats = reporting_service.get_organization_statistics(
        db=db,
        org_id=current_user.org_id,
        start_date=d_start,
        end_date=d_end,
        department_id=department_id,
        category_id=category_id,
        status_filter=status_filter if status_filter != "All" else None
    )
    return stats
