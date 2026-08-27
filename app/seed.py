import json
import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app import models, security
from app.services import audit_service, version_service, notification_service

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if already seeded
    if db.query(models.Organization).first():
        db.close()
        return

    print("Seeding generic multi-tenant enterprise demonstration data...")

    # ==========================================
    # TENANT 1: Acme Corporation (Generic Enterprise)
    # ==========================================
    org_acme = models.Organization(
        name="Acme Corporation",
        code="acme",
        logo_url="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=128&h=128&fit=crop",
        contact_email="operations@acmecorp.com",
        contact_phone="+1 (415) 555-0100",
        address="100 Enterprise Blvd, Suite 800, San Francisco, CA 94105, USA",
        settings_json=json.dumps({"currency": "USD", "allow_delegation": True})
    )
    db.add(org_acme)
    db.commit()
    db.refresh(org_acme)

    # Acme Corporate Departments
    dept_eng = models.Department(org_id=org_acme.id, name="Engineering & Technology", description="Software Development and Infrastructure")
    dept_fin = models.Department(org_id=org_acme.id, name="Finance & Accounts", description="Corporate Finance, Accounting, and Budgeting")
    dept_hr = models.Department(org_id=org_acme.id, name="Human Resources", description="People Operations and Talent Acquisition")
    dept_proc = models.Department(org_id=org_acme.id, name="Procurement & Operations", description="Procurement, Facilities, and Supply Chain")
    dept_exec = models.Department(org_id=org_acme.id, name="Executive Office", description="Executive Leadership & Strategic Direction")
    db.add_all([dept_eng, dept_fin, dept_hr, dept_proc, dept_exec])
    db.commit()
    for d in [dept_eng, dept_fin, dept_hr, dept_proc, dept_exec]:
        db.refresh(d)

    # Acme Categories
    categories = [
        models.MemoCategory(org_id=org_acme.id, name="Administrative", description="Administrative policies and general notices"),
        models.MemoCategory(org_id=org_acme.id, name="Financial", description="Budget approvals, capital expenditure, and funding"),
        models.MemoCategory(org_id=org_acme.id, name="Procurement", description="Equipment purchases, software licenses, and hardware"),
        models.MemoCategory(org_id=org_acme.id, name="HR", description="Staffing, leave applications, promotions, and compensation"),
        models.MemoCategory(org_id=org_acme.id, name="Technical", description="IT infrastructure, security upgrades, and engineering roadmaps"),
        models.MemoCategory(org_id=org_acme.id, name="Operations", description="Operational workflows, office policies, and vendor contracts"),
        models.MemoCategory(org_id=org_acme.id, name="General", description="General organizational communications")
    ]
    db.add_all(categories)
    db.commit()

    # Acme Corporate Users (Hierarchy: Employee -> Dept Head -> Finance -> Director -> CEO)
    hashed_pwd = security.get_password_hash("password123")

    u_admin = models.User(
        org_id=org_acme.id,
        department_id=dept_exec.id,
        email="admin@acmecorp.com",
        password_hash=hashed_pwd,
        full_name="Sarah Jenkins",
        designation="Organization & Systems Administrator",
        role="admin",
        is_active=True
    )
    u_head = models.User(
        org_id=org_acme.id,
        department_id=dept_eng.id,
        email="head.eng@acmecorp.com",
        password_hash=hashed_pwd,
        full_name="David Vance",
        designation="VP of Engineering & Dept Head",
        role="user",
        is_active=True
    )
    u_finance = models.User(
        org_id=org_acme.id,
        department_id=dept_fin.id,
        email="finance.mgr@acmecorp.com",
        password_hash=hashed_pwd,
        full_name="Rachel Green",
        designation="Chief Financial Manager",
        role="user",
        is_active=True
    )
    u_director = models.User(
        org_id=org_acme.id,
        department_id=dept_proc.id,
        email="director@acmecorp.com",
        password_hash=hashed_pwd,
        full_name="Marcus Sterling",
        designation="Director of Corporate Operations",
        role="user",
        is_active=True
    )
    u_ceo = models.User(
        org_id=org_acme.id,
        department_id=dept_exec.id,
        email="ceo@acmecorp.com",
        password_hash=hashed_pwd,
        full_name="Eleanor Vance",
        designation="Chief Executive Officer (CEO)",
        role="user",
        is_active=True
    )
    u_employee1 = models.User(
        org_id=org_acme.id,
        department_id=dept_eng.id,
        email="alex.morgan@acmecorp.com",
        password_hash=hashed_pwd,
        full_name="Alex Morgan",
        designation="Senior Software Engineer / Team Lead",
        role="user",
        is_active=True
    )
    u_employee2 = models.User(
        org_id=org_acme.id,
        department_id=dept_eng.id,
        email="jessica.taylor@acmecorp.com",
        password_hash=hashed_pwd,
        full_name="Jessica Taylor",
        designation="Operations & QA Specialist",
        role="user",
        is_active=True
    )

    db.add_all([u_admin, u_head, u_finance, u_director, u_ceo, u_employee1, u_employee2])
    db.commit()
    for u in [u_admin, u_head, u_finance, u_director, u_ceo, u_employee1, u_employee2]:
        db.refresh(u)

    # Reusable Workflow Templates for Acme Corp
    tmpl_purchase = models.WorkflowTemplate(
        org_id=org_acme.id,
        name="Procurement / Purchase Request",
        description="Standard 5-step executive approval workflow (Requester → Dept Head → Finance → Director → CEO)",
        steps_json=json.dumps([
            {"role_name": "Requester / Author", "step_type": "author", "default_user_id": u_employee1.id},
            {"role_name": "Department Head", "step_type": "approval", "default_user_id": u_head.id},
            {"role_name": "Finance Manager", "step_type": "approval", "default_user_id": u_finance.id},
            {"role_name": "Director of Operations", "step_type": "approval", "default_user_id": u_director.id},
            {"role_name": "Chief Executive Officer (CEO)", "step_type": "final_approval", "default_user_id": u_ceo.id}
        ])
    )
    tmpl_leave = models.WorkflowTemplate(
        org_id=org_acme.id,
        name="Employee Leave Request",
        description="Standard approval workflow for employee leave (Employee → Line Manager → HR)",
        steps_json=json.dumps([
            {"role_name": "Employee", "step_type": "author", "default_user_id": u_employee1.id},
            {"role_name": "Line Manager / Dept Head", "step_type": "approval", "default_user_id": u_head.id},
            {"role_name": "HR Manager", "step_type": "final_approval", "default_user_id": u_admin.id}
        ])
    )
    db.add_all([tmpl_purchase, tmpl_leave])
    db.commit()

    # Active Delegation: David Vance (Dept Head) delegates authority to Jessica Taylor
    now = datetime.datetime.now(datetime.timezone.utc)
    del_head = models.WorkflowDelegation(
        org_id=org_acme.id,
        delegator_id=u_head.id,
        delegatee_id=u_employee2.id,
        start_date=now - datetime.timedelta(days=1),
        end_date=now + datetime.timedelta(days=6),
        reason="Attending International Technology Leadership Summit in Zurich. Acting Dept Head designated for memo approvals.",
        is_active=True
    )
    db.add(del_head)
    db.commit()

    # Seed Memos in Acme Corp
    # 1. MEMO-ACME-2026-0001: In-Progress Procurement Memo (Pending Finance Manager Approval)
    cat_proc = categories[2]
    memo_1 = models.Memo(
        org_id=org_acme.id,
        author_id=u_employee1.id,
        department_id=dept_eng.id,
        category_id=cat_proc.id,
        memo_number="MEMO-ACME-2026-0001",
        title="Procurement of High-Performance Dedicated Cloud Infrastructure & GPU Clusters",
        body="""<p>Dear Management,</p>
<p>To support our expanding production microservices and next-generation AI model inference workloads, the Engineering department urgently requests authorization to procure <b>dedicated multi-region GPU clusters</b> and cloud capacity reserves.</p>
<p><b>Estimated Annual Investment:</b> $45,000 USD</p>
<p>Vendor comparison benchmarks, SLA terms, and architecture diagrams are attached. We request expedited review to ensure seamless onboarding prior to Q4 customer delivery milestones.</p>""",
        priority="Urgent",
        status="Pending Approval",
        current_step_index=2,
        current_assignee_id=u_finance.id,
        submitted_at=now - datetime.timedelta(hours=4),
        created_at=now - datetime.timedelta(hours=5)
    )
    db.add(memo_1)
    db.commit()
    db.refresh(memo_1)

    m1_s0 = models.MemoWorkflowStep(memo_id=memo_1.id, step_index=0, step_type="author", role_name="Requester / Author", assigned_user_id=u_employee1.id, status="completed", action_taken="submitted", action_by_user_id=u_employee1.id, action_timestamp=now - datetime.timedelta(hours=4), is_current=False)
    m1_s1 = models.MemoWorkflowStep(memo_id=memo_1.id, step_index=1, step_type="approval", role_name="Department Head", assigned_user_id=u_head.id, status="completed", action_taken="approved", action_by_user_id=u_head.id, action_timestamp=now - datetime.timedelta(hours=3), comments="Fully endorsed. Critical for scaling infrastructure.", is_current=False)
    m1_s2 = models.MemoWorkflowStep(memo_id=memo_1.id, step_index=2, step_type="approval", role_name="Finance Manager", assigned_user_id=u_finance.id, status="pending", is_current=True)
    m1_s3 = models.MemoWorkflowStep(memo_id=memo_1.id, step_index=3, step_type="approval", role_name="Director of Operations", assigned_user_id=u_director.id, status="pending", is_current=False)
    m1_s4 = models.MemoWorkflowStep(memo_id=memo_1.id, step_index=4, step_type="final_approval", role_name="Chief Executive Officer", assigned_user_id=u_ceo.id, status="pending", is_current=False)
    db.add_all([m1_s0, m1_s1, m1_s2, m1_s3, m1_s4])

    version_service.create_version_snapshot(db, memo_1, u_employee1.id, "Initial submission of cloud cluster procurement")
    db.add(models.MemoComment(memo_id=memo_1.id, org_id=org_acme.id, user_id=u_head.id, comment_type="approval", text="[Approved] Fully endorsed. Critical for scaling infrastructure."))
    notification_service.create_notification(db, org_acme.id, u_finance.id, "Action Required on Memo", f"Memo '{memo_1.memo_number}: {memo_1.title}' is pending your financial review.", "action_required", memo_id=memo_1.id)

    # 2. MEMO-ACME-2026-0002: Changes Requested Memo (Ready to demonstrate Resubmission & Versioning)
    cat_tech = categories[4]
    memo_2 = models.Memo(
        org_id=org_acme.id,
        author_id=u_employee1.id,
        department_id=dept_eng.id,
        category_id=cat_tech.id,
        memo_number="MEMO-ACME-2026-0002",
        title="Proposal for Enterprise Developer Tooling Licenses & AI Coding Subscriptions",
        body="""<p>We propose a budget of $12,000 for annual enterprise developer tooling licenses and automated testing infrastructure for the core software engineering teams.</p>""",
        priority="High",
        status="Changes Requested",
        current_step_index=1,
        current_assignee_id=u_employee1.id,
        submitted_at=now - datetime.timedelta(days=1),
        created_at=now - datetime.timedelta(days=1, hours=2)
    )
    db.add(memo_2)
    db.commit()
    db.refresh(memo_2)

    m2_s0 = models.MemoWorkflowStep(memo_id=memo_2.id, step_index=0, step_type="author", role_name="Author", assigned_user_id=u_employee1.id, status="completed", action_taken="submitted", action_by_user_id=u_employee1.id, action_timestamp=now - datetime.timedelta(days=1), is_current=False)
    m2_s1 = models.MemoWorkflowStep(memo_id=memo_2.id, step_index=1, step_type="approval", role_name="Department Head", assigned_user_id=u_head.id, status="changes_requested", action_taken="changes_requested", action_by_user_id=u_head.id, action_timestamp=now - datetime.timedelta(hours=18), comments="Please provide a per-seat seat utilization breakdown and projected developer velocity return on investment.", is_current=False)
    m2_s2 = models.MemoWorkflowStep(memo_id=memo_2.id, step_index=2, step_type="approval", role_name="Finance Manager", assigned_user_id=u_finance.id, status="pending", is_current=False)
    db.add_all([m2_s0, m2_s1, m2_s2])

    version_service.create_version_snapshot(db, memo_2, u_employee1.id, "Initial proposal submission")
    db.add(models.MemoComment(memo_id=memo_2.id, org_id=org_acme.id, user_id=u_head.id, comment_type="change_request", text="[Change Request] Please provide a per-seat seat utilization breakdown and projected developer velocity return on investment."))
    notification_service.create_notification(db, org_acme.id, u_employee1.id, "Changes Requested on Memo", "Changes requested on memo 'MEMO-ACME-2026-0002' by David Vance: Please provide a per-seat breakdown.", "changes_requested", memo_id=memo_2.id)

    # 3. MEMO-ACME-2026-0003: Approved & Finalized Memo (CEO Signed Off)
    cat_admin = categories[0]
    memo_3 = models.Memo(
        org_id=org_acme.id,
        author_id=u_employee2.id,
        department_id=dept_proc.id,
        category_id=cat_admin.id,
        memo_number="MEMO-ACME-2026-0003",
        title="Annual Corporate Information Security Policy & Remote Work Protocol",
        body="""<p>Submitted for formal executive approval is the comprehensive 2026 Corporate Information Security and Remote Work Protocol.</p>
<p>All departmental stakeholders, legal compliance, and IT leadership have aligned on zero-trust device access standards and incident management protocols.</p>""",
        priority="Normal",
        status="Approved",
        current_step_index=2,
        current_assignee_id=None,
        final_approver_id=u_ceo.id,
        final_approved_at=now - datetime.timedelta(days=2),
        submitted_at=now - datetime.timedelta(days=3),
        created_at=now - datetime.timedelta(days=3, hours=4)
    )
    db.add(memo_3)
    db.commit()
    db.refresh(memo_3)

    m3_s0 = models.MemoWorkflowStep(memo_id=memo_3.id, step_index=0, step_type="author", role_name="Author", assigned_user_id=u_employee2.id, status="completed", action_taken="submitted", action_by_user_id=u_employee2.id, action_timestamp=now - datetime.timedelta(days=3), is_current=False)
    m3_s1 = models.MemoWorkflowStep(memo_id=memo_3.id, step_index=1, step_type="approval", role_name="Director of Operations", assigned_user_id=u_director.id, status="completed", action_taken="approved", action_by_user_id=u_director.id, action_timestamp=now - datetime.timedelta(days=2, hours=12), comments="Compliance and operations reviewed.", is_current=False)
    m3_s2 = models.MemoWorkflowStep(memo_id=memo_3.id, step_index=2, step_type="final_approval", role_name="Chief Executive Officer", assigned_user_id=u_ceo.id, status="completed", action_taken="approved", action_by_user_id=u_ceo.id, action_timestamp=now - datetime.timedelta(days=2), comments="Approved for enterprise-wide implementation.", is_current=False)
    db.add_all([m3_s0, m3_s1, m3_s2])
    version_service.create_version_snapshot(db, memo_3, u_employee2.id, "Final policy approval version")
    db.add(models.MemoComment(memo_id=memo_3.id, org_id=org_acme.id, user_id=u_ceo.id, comment_type="approval", text="[Approved] Approved for enterprise-wide implementation."))

    # 4. MEMO-ACME-2026-0004: Rejected Memo
    cat_gen = categories[6]
    memo_4 = models.Memo(
        org_id=org_acme.id,
        author_id=u_employee2.id,
        department_id=dept_proc.id,
        category_id=cat_gen.id,
        memo_number="MEMO-ACME-2026-0004",
        title="Funding Request for Offsite Executive Luxury Resort Summit",
        body="""<p>Requesting allocation of $28,000 from corporate discretionary reserves for an offsite 5-star resort executive retreat.</p>""",
        priority="Normal",
        status="Rejected",
        current_step_index=1,
        current_assignee_id=None,
        submitted_at=now - datetime.timedelta(days=5),
        created_at=now - datetime.timedelta(days=5, hours=1)
    )
    db.add(memo_4)
    db.commit()
    db.refresh(memo_4)

    m4_s0 = models.MemoWorkflowStep(memo_id=memo_4.id, step_index=0, step_type="author", role_name="Author", assigned_user_id=u_employee2.id, status="completed", action_taken="submitted", action_by_user_id=u_employee2.id, action_timestamp=now - datetime.timedelta(days=5), is_current=False)
    m4_s1 = models.MemoWorkflowStep(memo_id=memo_4.id, step_index=1, step_type="approval", role_name="Finance Manager", assigned_user_id=u_finance.id, status="rejected", action_taken="rejected", action_by_user_id=u_finance.id, action_timestamp=now - datetime.timedelta(days=4), comments="Discretionary reserve policy does not permit luxury travel allocations outside standard operating budgets.", is_current=False)
    db.add_all([m4_s0, m4_s1])
    version_service.create_version_snapshot(db, memo_4, u_employee2.id, "Initial submission")
    db.add(models.MemoComment(memo_id=memo_4.id, org_id=org_acme.id, user_id=u_finance.id, comment_type="rejection", text="[Rejected] Discretionary reserve policy does not permit luxury travel allocations outside standard operating budgets."))

    # 5. MEMO-ACME-2026-0005: Saved Draft Memo
    memo_5 = models.Memo(
        org_id=org_acme.id,
        author_id=u_employee1.id,
        department_id=dept_eng.id,
        category_id=cat_tech.id,
        memo_number="MEMO-ACME-2026-0005",
        title="Draft: Strategic Roadmap for Zero-Downtime Multi-Region Database Replication",
        body="""<p>This draft memorandum outlines architectural specifications and cost estimates for transitioning global database clusters to zero-downtime active-active replication.</p>""",
        priority="Normal",
        status="Draft",
        current_step_index=0,
        current_assignee_id=u_employee1.id,
        created_at=now - datetime.timedelta(hours=2)
    )
    db.add(memo_5)
    db.commit()
    db.refresh(memo_5)
    m5_s0 = models.MemoWorkflowStep(memo_id=memo_5.id, step_index=0, step_type="author", role_name="Author", assigned_user_id=u_employee1.id, status="pending", is_current=True)
    db.add(m5_s0)

    # ==========================================
    # TENANT 2: Nexus Financial Group (Multi-Tenancy Isolation Proof)
    # ==========================================
    org_nexus = models.Organization(
        name="Nexus Financial Group",
        code="nexus",
        logo_url="https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=128&h=128&fit=crop",
        contact_email="compliance@nexusgroup.com",
        contact_phone="+1 (212) 555-0188",
        address="Wall Street Financial Plaza, New York, NY 10005, USA",
        settings_json=json.dumps({"currency": "USD", "allow_delegation": True})
    )
    db.add(org_nexus)
    db.commit()
    db.refresh(org_nexus)

    nexus_dept_risk = models.Department(org_id=org_nexus.id, name="Quantitative Risk & Analytics", description="Risk Management and Capital Modeling")
    nexus_dept_ops = models.Department(org_id=org_nexus.id, name="Capital Markets Operations", description="Settlements and Trade Operations")
    db.add_all([nexus_dept_risk, nexus_dept_ops])
    db.commit()
    db.refresh(nexus_dept_risk)
    db.refresh(nexus_dept_ops)

    nexus_cat_sec = models.MemoCategory(org_id=org_nexus.id, name="Regulatory Compliance", description="SEC and FINRA regulatory audits")
    db.add(nexus_cat_sec)
    db.commit()
    db.refresh(nexus_cat_sec)

    u_nexus_admin = models.User(
        org_id=org_nexus.id,
        department_id=nexus_dept_risk.id,
        email="admin@nexusgroup.com",
        password_hash=hashed_pwd,
        full_name="Jonathan Hayes",
        designation="Managing Director & Chief Risk Officer",
        role="admin",
        is_active=True
    )
    u_nexus_lead = models.User(
        org_id=org_nexus.id,
        department_id=nexus_dept_risk.id,
        email="lead.analyst@nexusgroup.com",
        password_hash=hashed_pwd,
        full_name="Victoria Price",
        designation="Principal Quantitative Strategist",
        role="user",
        is_active=True
    )
    db.add_all([u_nexus_admin, u_nexus_lead])
    db.commit()
    db.refresh(u_nexus_admin)
    db.refresh(u_nexus_lead)

    memo_nexus1 = models.Memo(
        org_id=org_nexus.id,
        author_id=u_nexus_lead.id,
        department_id=nexus_dept_risk.id,
        category_id=nexus_cat_sec.id,
        memo_number="MEMO-NEXUS-2026-0001",
        title="Confidential: Q3 Capital Adequacy & Risk Exposure Assessment",
        body="<p>Confidential capital adequacy modeling for Nexus Financial Group executive committee only.</p>",
        priority="High",
        status="Approved",
        current_step_index=1,
        final_approver_id=u_nexus_admin.id,
        final_approved_at=now,
        submitted_at=now - datetime.timedelta(days=1),
        created_at=now - datetime.timedelta(days=1)
    )
    db.add(memo_nexus1)
    db.commit()
    db.refresh(memo_nexus1)

    nexus_s0 = models.MemoWorkflowStep(memo_id=memo_nexus1.id, step_index=0, step_type="author", role_name="Author", assigned_user_id=u_nexus_lead.id, status="completed", action_taken="submitted", action_by_user_id=u_nexus_lead.id, is_current=False)
    nexus_s1 = models.MemoWorkflowStep(memo_id=memo_nexus1.id, step_index=1, step_type="final_approval", role_name="Chief Risk Officer", assigned_user_id=u_nexus_admin.id, status="completed", action_taken="approved", action_by_user_id=u_nexus_admin.id, is_current=False)
    db.add_all([nexus_s0, nexus_s1])

    audit_service.log_event(db, org_acme.id, u_admin.id, "SYSTEM_INIT", "System", "1", "Acme Corporation enterprise tenant initialized with standard departments and approval workflows")
    audit_service.log_event(db, org_nexus.id, u_nexus_admin.id, "SYSTEM_INIT", "System", "2", "Nexus Financial Group tenant initialized under strict multi-tenant isolation")

    db.commit()
    db.close()
    print("Generic enterprise multi-tenant database successfully seeded!")

if __name__ == "__main__":
    seed_database()
