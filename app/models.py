import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, LargeBinary
)
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)
    logo_url = Column(String(500), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    settings_json = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    departments = relationship("Department", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    memo_categories = relationship("MemoCategory", back_populates="organization", cascade="all, delete-orphan")
    workflow_templates = relationship("WorkflowTemplate", back_populates="organization", cascade="all, delete-orphan")
    memos = relationship("Memo", back_populates="organization", cascade="all, delete-orphan")
    delegations = relationship("WorkflowDelegation", back_populates="organization", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="organization", cascade="all, delete-orphan")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_department_org_name"),
    )

    organization = relationship("Organization", back_populates="departments")
    users = relationship("User", back_populates="department")
    memos = relationship("Memo", back_populates="department")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    designation = Column(String(150), nullable=True)
    role = Column(String(50), default="user", nullable=False)  # "admin", "user"
    is_active = Column(Boolean, default=True, nullable=False)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_user_org_email"),
    )

    organization = relationship("Organization", back_populates="users")
    department = relationship("Department", back_populates="users")
    authored_memos = relationship("Memo", back_populates="author", foreign_keys="Memo.author_id")
    assigned_steps = relationship("MemoWorkflowStep", back_populates="assigned_user", foreign_keys="MemoWorkflowStep.assigned_user_id")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class MemoCategory(Base):
    __tablename__ = "memo_categories"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_category_org_name"),
    )

    organization = relationship("Organization", back_populates="memo_categories")
    memos = relationship("Memo", back_populates="category")


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    steps_json = Column(Text, nullable=False, default="[]")  # List of { role_name, step_type, default_user_id }
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization", back_populates="workflow_templates")


class Memo(Base):
    __tablename__ = "memos"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("memo_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    
    memo_number = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    priority = Column(String(50), default="Normal", nullable=False)  # Normal, High, Urgent
    status = Column(String(50), default="Draft", nullable=False, index=True)  # Draft, Submitted, Pending Review, Pending Approval, Changes Requested, Rejected, Approved, Cancelled
    
    current_step_index = Column(Integer, default=0, nullable=False)
    current_assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    final_approver_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    final_approved_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("org_id", "memo_number", name="uq_memo_org_number"),
    )

    organization = relationship("Organization", back_populates="memos")
    author = relationship("User", back_populates="authored_memos", foreign_keys=[author_id])
    department = relationship("Department", back_populates="memos")
    category = relationship("MemoCategory", back_populates="memos")
    current_assignee = relationship("User", foreign_keys=[current_assignee_id])
    final_approver = relationship("User", foreign_keys=[final_approver_id])

    workflow_steps = relationship("MemoWorkflowStep", back_populates="memo", cascade="all, delete-orphan", order_by="MemoWorkflowStep.step_index")
    attachments = relationship("MemoAttachment", back_populates="memo", cascade="all, delete-orphan")
    comments = relationship("MemoComment", back_populates="memo", cascade="all, delete-orphan", order_by="MemoComment.created_at")
    versions = relationship("MemoVersion", back_populates="memo", cascade="all, delete-orphan", order_by="MemoVersion.version_number")


class MemoWorkflowStep(Base):
    __tablename__ = "memo_workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    memo_id = Column(Integer, ForeignKey("memos.id", ondelete="CASCADE"), nullable=False, index=True)
    step_index = Column(Integer, nullable=False)
    step_type = Column(String(50), default="approval", nullable=False)  # author, review, approval, final_approval
    role_name = Column(String(100), nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    status = Column(String(50), default="pending", nullable=False)  # pending, completed, rejected, changes_requested, skipped
    action_taken = Column(String(50), nullable=True)  # submitted, approved, rejected, changes_requested, forwarded
    action_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    on_behalf_of_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action_timestamp = Column(DateTime(timezone=True), nullable=True)
    comments = Column(Text, nullable=True)
    is_current = Column(Boolean, default=False, nullable=False)

    memo = relationship("Memo", back_populates="workflow_steps")
    assigned_user = relationship("User", back_populates="assigned_steps", foreign_keys=[assigned_user_id])
    action_by_user = relationship("User", foreign_keys=[action_by_user_id])
    on_behalf_of_user = relationship("User", foreign_keys=[on_behalf_of_user_id])


class MemoAttachment(Base):
    __tablename__ = "memo_attachments"

    id = Column(Integer, primary_key=True, index=True)
    memo_id = Column(Integer, ForeignKey("memos.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    file_name = Column(String(255), nullable=False)  # disk filename
    original_name = Column(String(255), nullable=False)  # original uploaded filename
    file_size = Column(Integer, nullable=False)  # in bytes
    file_type = Column(String(100), nullable=True)  # MIME type / extension
    storage_path = Column(String(500), nullable=False)
    file_data = Column(LargeBinary, nullable=True)  # Persistent serverless storage
    created_at = Column(DateTime(timezone=True), default=utcnow)

    memo = relationship("Memo", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by_user_id])


class MemoComment(Base):
    __tablename__ = "memo_comments"

    id = Column(Integer, primary_key=True, index=True)
    memo_id = Column(Integer, ForeignKey("memos.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    comment_type = Column(String(50), default="general", nullable=False)  # general, approval, rejection, change_request
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    memo = relationship("Memo", back_populates="comments")
    author = relationship("User", foreign_keys=[user_id])


class MemoVersion(Base):
    __tablename__ = "memo_versions"

    id = Column(Integer, primary_key=True, index=True)
    memo_id = Column(Integer, ForeignKey("memos.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    summary_of_changes = Column(Text, nullable=True)
    snapshot_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    memo = relationship("Memo", back_populates="versions")
    author = relationship("User", foreign_keys=[author_id])


class WorkflowDelegation(Base):
    __tablename__ = "workflow_delegations"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    delegator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    delegatee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization", back_populates="delegations")
    delegator = relationship("User", foreign_keys=[delegator_id])
    delegatee = relationship("User", foreign_keys=[delegatee_id])


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    memo_id = Column(Integer, ForeignKey("memos.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    event_type = Column(String(50), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    organization = relationship("Organization", back_populates="notifications")
    user = relationship("User", back_populates="notifications")
    memo = relationship("Memo")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    object_type = Column(String(100), nullable=False)
    object_id = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    details_json = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User")
