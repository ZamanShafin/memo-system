import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas

def get_organization_statistics(
    db: Session,
    org_id: int,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    department_id: Optional[int] = None,
    category_id: Optional[int] = None,
    status_filter: Optional[str] = None
) -> schemas.ReportingStatsOut:
    """
    Computes tenant-scoped metrics, KPIs, and aggregations for reporting.
    """
    # Base memo query scoped to tenant
    query = db.query(models.Memo).filter(models.Memo.org_id == org_id)
    
    if start_date:
        query = query.filter(models.Memo.created_at >= start_date)
    if end_date:
        query = query.filter(models.Memo.created_at <= end_date)
    if department_id:
        query = query.filter(models.Memo.department_id == department_id)
    if category_id:
        query = query.filter(models.Memo.category_id == category_id)
    if status_filter:
        query = query.filter(models.Memo.status == status_filter)
        
    memos = query.all()
    total_memos = len(memos)
    
    pending_approvals = sum(1 for m in memos if m.status in ["Pending Approval", "Pending Review"])
    completed_memos = sum(1 for m in memos if m.status == "Approved")
    rejected_memos = sum(1 for m in memos if m.status == "Rejected")
    urgent_memos = sum(1 for m in memos if m.priority == "Urgent")
    changes_requested = sum(1 for m in memos if m.status == "Changes Requested")
    
    # Average completion time for approved memos
    completion_times = []
    for m in memos:
        if m.status == "Approved" and m.submitted_at and m.final_approved_at:
            diff = (m.final_approved_at - m.submitted_at).total_seconds() / 3600.0  # hours
            completion_times.append(diff)
            
    avg_completion = round(sum(completion_times) / len(completion_times), 1) if completion_times else 0.0
    
    # Aggregations by Status
    status_dict = {}
    for m in memos:
        status_dict[m.status] = status_dict.get(m.status, 0) + 1
    memos_by_status = [schemas.StatusCount(status=k, count=v) for k, v in status_dict.items()]
    
    # Aggregations by Department
    dept_map = {d.id: d.name for d in db.query(models.Department).filter(models.Department.org_id == org_id).all()}
    dept_dict = {}
    for m in memos:
        d_name = dept_map.get(m.department_id, "General / None")
        dept_dict[d_name] = dept_dict.get(d_name, 0) + 1
    memos_by_department = [schemas.DepartmentCount(department=k, count=v) for k, v in dept_dict.items()]
    
    # Aggregations by Category
    cat_map = {c.id: c.name for c in db.query(models.MemoCategory).filter(models.MemoCategory.org_id == org_id).all()}
    cat_dict = {}
    for m in memos:
        c_name = cat_map.get(m.category_id, "Uncategorized")
        cat_dict[c_name] = cat_dict.get(c_name, 0) + 1
    memos_by_category = [schemas.CategoryCount(category=k, count=v) for k, v in cat_dict.items()]
    
    # Aggregations by Priority
    priority_dict = {}
    for m in memos:
        priority_dict[m.priority] = priority_dict.get(m.priority, 0) + 1
    memos_by_priority = [schemas.PriorityCount(priority=k, count=v) for k, v in priority_dict.items()]
    
    # General Org counts
    total_users = db.query(models.User).filter(models.User.org_id == org_id).count()
    active_users = db.query(models.User).filter(models.User.org_id == org_id, models.User.is_active == True).count()
    total_departments = db.query(models.Department).filter(models.Department.org_id == org_id).count()
    
    return schemas.ReportingStatsOut(
        total_memos=total_memos,
        pending_approvals=pending_approvals,
        completed_memos=completed_memos,
        rejected_memos=rejected_memos,
        urgent_memos=urgent_memos,
        changes_requested=changes_requested,
        average_completion_hours=avg_completion,
        memos_by_status=memos_by_status,
        memos_by_department=memos_by_department,
        memos_by_category=memos_by_category,
        memos_by_priority=memos_by_priority,
        total_users=total_users,
        active_users=active_users,
        total_departments=total_departments
    )
