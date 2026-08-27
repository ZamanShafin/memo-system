import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# --- Auth & User Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
    user: "UserOut"
    organization: "OrganizationOut"

class LoginRequest(BaseModel):
    org_code: str
    email: EmailStr
    password: str

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

class PasswordResetRequest(BaseModel):
    org_code: str
    email: EmailStr
    new_password: str

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    designation: Optional[str] = None
    department_id: Optional[int] = None
    avatar_url: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    designation: Optional[str] = None
    department_id: Optional[int] = None
    role: str = "user"  # "admin" or "user"
    is_active: bool = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    designation: Optional[str] = None
    department_id: Optional[int] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    org_id: int
    department_id: Optional[int] = None
    email: str
    full_name: str
    designation: Optional[str] = None
    role: str
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: datetime.datetime

# --- Organization Schemas ---
class OrganizationCreate(BaseModel):
    name: str
    code: str
    logo_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    admin_email: EmailStr
    admin_password: str
    admin_name: str

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    settings_json: Optional[str] = None

class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    logo_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    settings_json: Optional[str] = None
    created_at: datetime.datetime

# --- Department Schemas ---
class DepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = None

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    org_id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime.datetime
    user_count: Optional[int] = 0

# --- Memo Category Schemas ---
class MemoCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class MemoCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class MemoCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    org_id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime.datetime

# --- Workflow Template Schemas ---
class WorkflowStepDef(BaseModel):
    step_type: str = "approval"  # author, review, approval, final_approval
    role_name: str
    default_user_id: Optional[int] = None

class WorkflowTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[WorkflowStepDef]

class WorkflowTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[WorkflowStepDef]] = None
    is_active: Optional[bool] = None

class WorkflowTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    org_id: int
    name: str
    description: Optional[str] = None
    steps_json: str
    is_active: bool
    created_at: datetime.datetime

# --- Workflow Delegation Schemas ---
class DelegationCreate(BaseModel):
    delegatee_id: int
    start_date: datetime.datetime
    end_date: datetime.datetime
    reason: Optional[str] = None

class DelegationUpdate(BaseModel):
    is_active: Optional[bool] = None
    reason: Optional[str] = None

class DelegationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    org_id: int
    delegator_id: int
    delegatee_id: int
    start_date: datetime.datetime
    end_date: datetime.datetime
    reason: Optional[str] = None
    is_active: bool
    created_at: datetime.datetime
    delegator: Optional[UserOut] = None
    delegatee: Optional[UserOut] = None

# --- Memo Workflow Step Schemas ---
class WorkflowStepCreate(BaseModel):
    step_type: str = "approval"
    role_name: str
    assigned_user_id: int

class WorkflowStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    memo_id: int
    step_index: int
    step_type: str
    role_name: str
    assigned_user_id: int
    status: str
    action_taken: Optional[str] = None
    action_by_user_id: Optional[int] = None
    on_behalf_of_user_id: Optional[int] = None
    action_timestamp: Optional[datetime.datetime] = None
    comments: Optional[str] = None
    is_current: bool
    assigned_user: Optional[UserOut] = None
    action_by_user: Optional[UserOut] = None
    on_behalf_of_user: Optional[UserOut] = None

# --- Memo Attachment & Comment Schemas ---
class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    memo_id: int
    org_id: int
    uploaded_by_user_id: Optional[int] = None
    file_name: str
    original_name: str
    file_size: int
    file_type: Optional[str] = None
    created_at: datetime.datetime
    uploader: Optional[UserOut] = None

class CommentCreate(BaseModel):
    comment_type: str = "general"  # general, approval, rejection, change_request
    text: str

class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    memo_id: int
    org_id: int
    user_id: int
    comment_type: str
    text: str
    created_at: datetime.datetime
    author: Optional[UserOut] = None

class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    memo_id: int
    version_number: int
    author_id: Optional[int] = None
    title: str
    body: str
    summary_of_changes: Optional[str] = None
    created_at: datetime.datetime
    author: Optional[UserOut] = None

# --- Memo Schemas ---
class MemoCreate(BaseModel):
    title: str
    body: str
    category_id: Optional[int] = None
    department_id: Optional[int] = None
    priority: str = "Normal"  # Normal, High, Urgent
    is_draft: bool = False
    workflow_steps: Optional[List[WorkflowStepCreate]] = None

class MemoUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    category_id: Optional[int] = None
    department_id: Optional[int] = None
    priority: Optional[str] = None
    workflow_steps: Optional[List[WorkflowStepCreate]] = None
    summary_of_changes: Optional[str] = None  # When resubmitting after changes requested

class WorkflowActionRequest(BaseModel):
    action: str  # "approve", "reject", "request_changes", "forward"
    comment: Optional[str] = None

class MemoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    org_id: int
    author_id: int
    department_id: Optional[int] = None
    category_id: Optional[int] = None
    memo_number: str
    title: str
    body: str
    priority: str
    status: str
    current_step_index: int
    current_assignee_id: Optional[int] = None
    final_approver_id: Optional[int] = None
    final_approved_at: Optional[datetime.datetime] = None
    submitted_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    author: Optional[UserOut] = None
    department: Optional[DepartmentOut] = None
    category: Optional[MemoCategoryOut] = None
    current_assignee: Optional[UserOut] = None
    final_approver: Optional[UserOut] = None
    workflow_steps: Optional[List[WorkflowStepOut]] = None
    attachments: Optional[List[AttachmentOut]] = None
    comments: Optional[List[CommentOut]] = None
    versions: Optional[List[VersionOut]] = None

# --- Notification & Audit Schemas ---
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    org_id: int
    user_id: int
    memo_id: Optional[int] = None
    title: str
    message: str
    event_type: str
    is_read: bool
    created_at: datetime.datetime

class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    org_id: int
    user_id: Optional[int] = None
    event_type: str
    object_type: str
    object_id: Optional[str] = None
    description: str
    details_json: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime.datetime
    user: Optional[UserOut] = None

# --- Reporting Schemas ---
class StatusCount(BaseModel):
    status: str
    count: int

class DepartmentCount(BaseModel):
    department: str
    count: int

class CategoryCount(BaseModel):
    category: str
    count: int

class PriorityCount(BaseModel):
    priority: str
    count: int

class ReportingStatsOut(BaseModel):
    total_memos: int
    pending_approvals: int
    completed_memos: int
    rejected_memos: int
    urgent_memos: int
    changes_requested: int
    average_completion_hours: float
    memos_by_status: List[StatusCount]
    memos_by_department: List[DepartmentCount]
    memos_by_category: List[CategoryCount]
    memos_by_priority: List[PriorityCount]
    total_users: Optional[int] = None
    active_users: Optional[int] = None
    total_departments: Optional[int] = None
