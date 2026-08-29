# Inter-Office Memo Management System — Technical Project Documentation

**Course:** CSE226 Foundations of Vibe Coding  
**Institution:** North South University  
**Student / Author:** Zaman Shafin  
**Deployed System URL:** [https://memo-system-pjbj.vercel.app](https://memo-system-pjbj.vercel.app)  
**Source Code Archive:** [https://github.com/ZamanShafin/memo-system/raw/main/source_code.zip](https://github.com/ZamanShafin/memo-system/raw/main/source_code.zip)  
**Repository:** [https://github.com/ZamanShafin/memo-system](https://github.com/ZamanShafin/memo-system)  

---

## 1. System Overview

The **Inter-Office Memo Management System** is a full-stack, cloud-native, multi-tenant Software-as-a-Service (SaaS) platform engineered to replace fragmented, unmonitored communication (such as unstructured email chains, chat messages, and physical paper files) with a centralized, auditable, and deterministic approval workflow engine.

### Core Value Proposition:
1. **Strict Multi-Tenancy:** Complete logical data isolation across distinct enterprise organizations within a single shared PostgreSQL database engine.
2. **Deterministic Sequential Approval:** Memos progress through strict, linear approval chains (*Requester -> Dept Head -> Finance Manager -> Director -> CEO*). Only the assigned turn holder (or active designated delegate) can approve, reject, or request changes.
3. **Dynamic Workflow Reconfigurability:** Turn holders can dynamically insert intermediate reviewers (*Approve & Add Reviewer*) or reroute assignments without breaking workflow determinism.
4. **Active Workflow Delegation:** Officers on official leave can delegate temporary approval authority with enforceable calendar date boundaries.
5. **Auditing & Immutable Versioning:** Every action creates timestamped audit entries and immutable content snapshots.
6. **Corporate PDF Engine & Digital Signatures:** Generates official memorandum PDFs complete with QR verification barcodes, signature matrices, and letterheads.

---

## 2. Requirements Implemented (Compliance Matrix)

The system satisfies 100% of the project specification requirements:

| Ref # | Requirement Area | Status | Implementation Highlights |
| :--- | :--- | :---: | :--- |
| **Req 1-4** | Multi-Tenancy & RBAC | **COMPLETE** | Universal org_id scoped data perimeters, distinct dmin and user roles with permission gates. |
| **Req 5-7** | Auth & Memo Authoring | **COMPLETE** | JWT bearer tokens, password reset, Quill.js rich text editor, priority tags, file attachments. |
| **Req 8-10** | Sequential Workflow Engine | **COMPLETE** | Step-by-step turn engine with strict state locks, templates, and dynamic mid-stream reviewer injection. |
| **Req 11-13** | Decision Governance & Delegation | **COMPLETE** | Approve, Reject, Request Changes with mandatory audit comments; date-bounded workflow delegation. |
| **Req 14-17** | PDFs, Alerts & Versioning | **COMPLETE** | Cryptographic PDF seal generation, in-app notification dropdown, immutable version history snapshots. |
| **Req 18-22** | Audit, Analytics & Security | **COMPLETE** | Immutable audit log capturing user/timestamp/IP, turnaround charts, admin self-deactivation protection. |
| **Req 23-30** | Deployment & Verification | **COMPLETE** | Live Vercel deployment, sanitized source zip, 20/20 passing pytest suite, full AI prompt log. |

---

## 3. Technology Stack

### Backend Architecture
- **Language & Runtime:** Python 3.10+ / FastAPI asynchronous framework.
- **ORM & Database Toolkit:** SQLAlchemy 2.0 with Declarative Mappings and Connection Pooling.
- **Database Engine:** PostgreSQL 16 (Neon Serverless Cloud Database with SSL/TLS).
- **Authentication & Cryptography:** Passlib (Bcrypt / PBKDF2-SHA256 password hashing) and PyJWT (JSON Web Tokens).
- **Document & PDF Engine:** ReportLab & xhtml2pdf with embedded CSS formatting and signature seals.
- **Validation & Serialization:** Pydantic v2 schemas for strict input/output contracts.

### Frontend Single Page Application (SPA)
- **Architecture:** Lightweight, zero-build-step vanilla JavaScript SPA engine (pp.js).
- **Styling & Design System:** Tailwind CSS utility framework with custom gradients, glassmorphism, and responsive breakpoints.
- **Icons & Typography:** Lucide Icons & Google Fonts (*Plus Jakarta Sans* & *JetBrains Mono*).
- **Rich Text Authoring:** Quill.js WYSIWYG editor with custom toolbar.
- **Interactive Visualizations:** Chart.js for real-time status doughnuts and analytics bars.

### Cloud Deployment & Tooling
- **Hosting Platform:** Vercel Serverless Functions (pi/index.py ASGI bridge).
- **Package Manager:** uv (ultra-fast Python package resolver) and pip.
- **AI Coding Environment:** Google Antigravity AI Pair Programming Agent.

---

## 4. System Architecture

`mermaid
graph TD
    Client[Web Browser / Mobile Client]
    
    subgraph Frontend_SPA [Frontend SPA Layer]
        Router[View Routing Engine]
        State[appState State Store]
        UI[Tailwind UI & Modals]
        Quill[Quill.js Rich Editor]
        Charts[Chart.js Visualizer]
    end

    subgraph Backend_API [FastAPI REST API Layer]
        AuthRouter[/api/v1/auth]
        MemoRouter[/api/v1/memos]
        WorkflowRouter[/api/v1/workflow]
        AdminRouter[/api/v1/admin]
        ReportsRouter[/api/v1/reports]
        DelegationRouter[/api/v1/delegations]
    end

    subgraph Core_Services [Business Logic & Service Layer]
        WorkflowEngine[Workflow State Machine]
        VersionService[Immutable Version Engine]
        AuditService[Audit Logger]
        NotificationService[Notification Dispatcher]
        PDFEngine[PDF Generation & Seal Engine]
    end

    subgraph Storage_Layer [Database & Cloud Persistence]
        NeonDB[(PostgreSQL Database - Neon Cloud)]
    end

    Client --> Router
    Router --> UI
    UI --> State
    UI --> Quill
    UI --> Charts
    
    State -- HTTP REST / Bearer JWT --> Backend_API
    Backend_API --> Core_Services
    Core_Services --> NeonDB
`

---

## 5. Database Design & Multi-Tenancy Enforcement

### Multi-Tenancy Data Perimeter Guard
1. **Foreign Key Scoping:** Every principal entity (User, Department, Memo, WorkflowTemplate, WorkflowDelegation, AuditLog, Notification) possesses a non-nullable org_id foreign key pointing to organizations.id.
2. **Backend Query Filtering:** All database queries automatically filter on models.Entity.org_id == current_user.org_id at the API/server layer, never relying on frontend-only filtering.
3. **Cross-Tenant Attack Prevention:** Direct object access (e.g. GET /api/v1/memos/42) validates memo.org_id == current_user.org_id. If IDs mismatch, an HTTP 404/403 is thrown immediately.

### Entity-Relationship Structure:
- organizations: Master tenant registry (id, 
ame, code, contact_email).
- users: User profiles with roles (id, org_id, department_id, ull_name, email, password_hash, 
ole, is_active).
- departments: Functional divisions (id, org_id, 
ame, description).
- memos: Memorandum records (id, org_id, memo_number, 	itle, ody_html, priority, status, uthor_id, current_assignee_id).
- memo_workflow_steps: Sequential stages (id, memo_id, step_number, ssigned_user_id, status, decision, comments, ction_timestamp).
- memo_versions: Historical snapshots for change requests (id, memo_id, ersion_number, 	itle, ody_html, change_summary).
- workflow_delegations: Delegation rules (id, org_id, delegator_id, delegatee_id, start_date, end_date, is_active).
- udit_logs: Tamper-evident activity logs (id, org_id, user_id, event_type, object_type, description, ip_address, created_at).

---

## 6. Sequential Workflow & Delegation Design

`mermaid
stateDiagram-v2
    [*] --> Draft : Save Initial Draft
    Draft --> Pending_Approval : Author Submits
    
    Pending_Approval --> Pending_Approval : Step Approver Approves (Moves to Step N+1)
    Pending_Approval --> Pending_Approval : Reviewer Injected (Approve & Add Reviewer)
    Pending_Approval --> Changes_Requested : Reviewer Requests Changes
    Pending_Approval --> Rejected : Reviewer Rejects (Workflow Terminated)
    
    Changes_Requested --> Pending_Approval : Author Edits & Resubmits (Snapshot Created)
    
    Pending_Approval --> Approved : Final Step Approver Approves (CEO Sign-off)
    
    Approved --> [*] : PDF Sealed & Archived
    Rejected --> [*] : Logged in Archive
`

### Key Rules Enforced:
- **Turn-Based Locks:** Only current_assignee_id (or their active delegate) can submit decisions. Downstream participants are blocked from acting early.
- **Delegation Protocol:** When David Vance delegates authority to Jessica Taylor, Jessica can approve on David's behalf with full audit logging.
- **Immutable Version History:** Change requests return the memo to the author. Editing creates a new MemoVersion entry before resubmission.

---

## 7. Security Architecture

1. **Password Security:** Salted and hashed using PBKDF2-SHA256 and Bcrypt.
2. **Stateless JWT Tokens:** Digitally signed HMAC-SHA256 tokens with 24-hour expiration.
3. **Admin Self-Deactivation Guard:** Backend rules prevent admins from deactivating or demoting themselves.
4. **Injection Protections:** Parameterized queries via SQLAlchemy prevent SQL injection; rich text HTML is sanitized to prevent XSS.
5. **Production HTTPS:** Live SSL/TLS encryption on Vercel and Neon PostgreSQL connection pooling.

---

## 8. Known Limitations (Documented Transparently)

In strict accordance with the course guideline to report genuine project boundaries rather than concealing them, the following are known technical trade-offs:
1. **In-App Notification Mechanism:** Notifications currently use responsive HTTP polling and reactive cache invalidation rather than full-duplex WebSockets.
2. **File Storage Infrastructure:** Attachments are currently stored as binary data within the database layer; integration with dedicated object storage (e.g. AWS S3 or Cloudflare R2) is reserved for future high-volume enterprise scaling.
3. **Authentication Factors:** Multi-Factor Authentication (MFA/TOTP) is not implemented in the current release; authentication relies on JWT bearer sessions and secure password resets.
