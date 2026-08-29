# CSE226 Final Project Technical Documentation

**Course:** CSE226 Foundations of Vibe Coding  
**Institution:** North South University  
**Student / Author:** Zaman Shafin  
**Deployed Application:** [https://memo-system-pjbj.vercel.app](https://memo-system-pjbj.vercel.app)  
**Source Code Archive:** [https://github.com/ZamanShafin/memo-system/raw/main/source_code.zip](https://github.com/ZamanShafin/memo-system/raw/main/source_code.zip)  
**GitHub Repository:** [https://github.com/ZamanShafin/memo-system](https://github.com/ZamanShafin/memo-system)  

---

## 1. System Overview & Core Capabilities

The **Inter-Office Memo Management System** is a full-stack, cloud-native, multi-tenant SaaS application designed to digitize, govern, and audit corporate memorandum workflows.

### Key Capabilities:
- **Strict Multi-Tenancy:** Complete logical data partitioning with org_id foreign-key scoping on every table and query.
- **Deterministic Turn-Based Workflow:** Memos advance in linear sequential order (*Requester -> Dept Head -> Finance -> Director -> CEO*). Later participants are physically blocked from acting early.
- **Dynamic Reviewer Insertion:** Active turn holders can insert ad-hoc intermediate reviewers (*Approve & Add Reviewer*) mid-stream.
- **Date-Bounded Delegation:** Officers on official leave can delegate temporary approval authority.
- **Immutable Versioning:** Change requests return memos to the author; editing creates historical snapshots before resubmission.
- **Cryptographic PDF Seals:** Official signed PDFs with QR code verification and signature matrices.

---

## 2. Requirements Implemented (Compliance Matrix)

| Ref # | Requirement Area | Status | Implementation Summary |
| :--- | :--- | :---: | :--- |
| **Req 1-4** | Multi-Tenancy & RBAC | **COMPLETE** | Universal org_id data perimeters, Admin/User roles, department management. |
| **Req 5-7** | Auth & Memo Authoring | **COMPLETE** | JWT tokens, password reset, Quill.js rich text editor, priority tags, file attachments. |
| **Req 8-10** | Sequential Workflow Engine | **COMPLETE** | Strict linear turn execution, templates, dynamic mid-stream reviewer insertion. |
| **Req 11-13** | Decisions & Delegation | **COMPLETE** | Approve, Reject, Request Changes with audit notes; date-bounded delegation. |
| **Req 14-17** | PDFs, Alerts & Versions | **COMPLETE** | Cryptographic PDF seal generation, notification tray, immutable version snapshots. |
| **Req 18-22** | Audit & Security | **COMPLETE** | Append-only audit logs, turnaround charts, admin self-deactivation protection. |
| **Req 23-30** | Deployment & Testing | **COMPLETE** | Live on Vercel, sanitized source ZIP, 20/20 passing pytest suite, full prompt log. |

---

## 3. Technology Stack

- **Backend API:** FastAPI (Asynchronous Python 3.10+ REST API)
- **Database & ORM:** PostgreSQL 16 (Neon Cloud) + SQLAlchemy 2.0 ORM (Connection Pooling & SSL)
- **Authentication:** Stateless JWT (PyJWT) + Passlib (PBKDF2-SHA256 & Bcrypt password hashing)
- **Frontend SPA:** Lightweight Vanilla JavaScript Single-Page App (pp.js) with zero build steps
- **Design & UI:** Tailwind CSS utility framework + Lucide Icons + Google Fonts
- **Rich Text & Charts:** Quill.js WYSIWYG editor + Chart.js analytics engine
- **PDF Generation:** ReportLab & xhtml2pdf with embedded signature stamps and QR codes
- **Hosting & CI/CD:** Vercel Serverless Functions with automated Git integration

---

## 4. System Architecture & Diagram

### 4.1 High-Level Architecture Topology

`
+-----------------------------------------------------------------------------+
|                            CLIENT TIER (Browser / Mobile)                   |
|  - Vanilla JS SPA Router (showView)           - Tailwind Responsive Layout  |
|  - Reactive State Store (appState)            - Quill.js WYSIWYG Editor     |
|  - Interactive Chart.js Visualizations        - Lucide Icon System          |
+--------------------------------------+--------------------------------------+
                                       | HTTP REST / Bearer JWT
                                       v
+-----------------------------------------------------------------------------+
|                     APPLICATION & REST API TIER (FastAPI)                   |
|  +-------------------+  +--------------------+  +------------------------+  |
|  |   /auth Router    |  |   /memos Router    |  |   /workflow Router     |  |
|  | - JWT Auth & Reset|  | - CRUD & Attachments| | - Action & Turn Engine |  |
|  +-------------------+  +--------------------+  +------------------------+  |
|  +-------------------+  +--------------------+  +------------------------+  |
|  |   /admin Router   |  |   /reports Router  |  |  /delegations Router   |  |
|  | - Users & Depts   |  | - Analytics Stats  |  | - Date-Bounded Rules   |  |
|  +-------------------+  +--------------------+  +------------------------+  |
+--------------------------------------+--------------------------------------+
                                       | Internal Service Invocations
                                       v
+-----------------------------------------------------------------------------+
|                        CORE BUSINESS LOGIC SERVICES                         |
|  - Workflow State Machine        - Immutable Version Snapshotting           |
|  - Cryptographic PDF & QR Engine - Real-Time In-App Notification Dispatcher |
|  - Append-Only Audit Logger      - Role-Based Access Control (RBAC) Guard   |
+--------------------------------------+--------------------------------------+
                                       | SQLAlchemy 2.0 (SSL / Connection Pool)
                                       v
+-----------------------------------------------------------------------------+
|                     DATA & STORAGE TIER (Neon PostgreSQL)                   |
|  [organizations]  [users]        [departments]  [memo_categories]           |
|  [memos]          [memo_steps]   [memo_versions][workflow_delegations]      |
|  [memo_comments]  [attachments]  [audit_logs]   [notifications]             |
+-----------------------------------------------------------------------------+
`

---

## 5. Database Design & Multi-Tenancy Enforcement

### 5.1 Multi-Tenancy Data Perimeter Guard
1. **Foreign-Key Scoping:** All principal entities (users, departments, memos, memo_workflow_steps, workflow_delegations, udit_logs, 
otifications) include a mandatory org_id column.
2. **Server-Side Filtering:** Every query automatically applies models.Entity.org_id == current_user.org_id.
3. **Cross-Tenant Guard:** Direct object access (e.g. GET /api/v1/memos/{id}) verifies memo.org_id == current_user.org_id or rejects with HTTP 404/403.

### 5.2 Entity-Relationship Diagram

`
+-------------------+        +-------------------+        +----------------------+
|   ORGANIZATION    | 1    * |       USER        | 1    * |         MEMO         |
|-------------------|--------|-------------------|--------|----------------------|
| id (PK)           |        | id (PK)           |        | id (PK)              |
| name, code        |        | org_id (FK)       |        | org_id (FK)          |
| contact_email     |        | department_id(FK) |        | memo_number, title   |
+-------------------+        | full_name, email  |        | body_html, priority  |
                             | role, is_active   |        | status, author_id    |
                             +-------------------+        | current_assignee_id  |
                                                          +----------+-----------+
                                                                     | 1
                                                                     | *
+-----------------------+    +-----------------------+    +----------v-----------+
|    MEMO_VERSION       |    |   WORKFLOW_DELEGATION |    |  MEMO_WORKFLOW_STEP  |
|-----------------------|    |-----------------------|    |----------------------|
| id (PK), memo_id (FK) |    | id (PK), org_id (FK)  |    | id (PK), memo_id(FK) |
| version_num, body_html|    | delegator_id (FK)     |    | step_index, role_name|
| change_summary        |    | delegatee_id (FK)     |    | assigned_user_id (FK)|
| created_by, created_at|    | start_date, end_date  |    | status, decision     |
+-----------------------+    +-----------------------+    +----------------------+
`

---

## 6. Sequential Workflow & Delegation Design

### 6.1 State Transition Diagram

`
    [ Author Creates Memo ] 
               |
               v
         [ DRAFT STATE ]  <====================================+
               |                                               |
        Author Submits                                         |
               v                                               |
     +-------------------------------------------------------+ |
     |           PENDING APPROVAL / REVIEW STATE             | |
     |                                                       | |
     |  Step 1: Dept Head  ===> Approve ===> Step 2          | |
     |  Step 2: Finance    ===> Approve ===> Step 3          | |
     |  Step 3: Director   ===> Approve ===> Step 4          | |
     |  Step 4: CEO        ===> Approve ===> [ APPROVED ]    | |
     +---------+--------------------+------------------------+ |
               |                    |                          |
        Reviewer Rejects      Request Changes                  |
               |                    |                          |
               v                    +==========================+
         [ REJECTED ]              (Returns to Author for edits;
     (Workflow Terminated)          Creates immutable MemoVersion snapshot)
`

### 6.2 Workflow Governance Rules
- **Turn-Based Locks:** Step N must complete before Step N+1 can act.
- **Dynamic Reviewer Insertion:** Turn holders can select *Approve & Add Reviewer* to insert intermediate reviewers.
- **Delegation Protocol:** Designated delegates can sign off during active calendar windows with full audit attribution.
- **Changes Requested:** Returns the memo to the author for revision and records an immutable MemoVersion snapshot upon resubmission.
- **Final Approval:** CEO approval locks the memo as read-only, generates digital signatures, and seals the PDF.

---

## 7. Security Architecture

- **Password Security:** PBKDF2-SHA256 and Bcrypt salting and hashing.
- **Stateless JWT:** HMAC-SHA256 signed bearer tokens with 24-hour expiration.
- **Admin Self-Protection:** Prevents administrators from deactivating or demoting themselves.
- **Injection Protections:** Parameterized SQLAlchemy ORM queries and Quill.js HTML sanitization.
- **Production SSL/TLS:** Enforced on Vercel frontend and Neon PostgreSQL connection pools.

---

## 8. Known Limitations (Documented Transparently)

1. **In-App Notification Transport:** Uses responsive client HTTP polling rather than full-duplex WebSockets.
2. **Object Storage:** Attachments are stored within the PostgreSQL database layer rather than dedicated AWS S3 buckets.
3. **Two-Factor Authentication:** MFA/TOTP is reserved for future enterprise versions.

---

## 9. Deployment Information & Evaluation Accounts

- **Live URL:** [https://memo-system-pjbj.vercel.app](https://memo-system-pjbj.vercel.app)
- **Source Code ZIP:** [https://github.com/ZamanShafin/memo-system/raw/main/source_code.zip](https://github.com/ZamanShafin/memo-system/raw/main/source_code.zip)
- **Organization Code:** cme
- **Universal Password:** password123

| Role | Email | Evaluation Persona |
| :--- | :--- | :--- |
| **Admin** | dmin@acmecorp.com | Sarah Jenkins (System Administrator) |
| **Author** | lex.morgan@acmecorp.com | Alex Morgan (Senior Engineer / Author) |
| **Dept Head** | head.eng@acmecorp.com | David Vance (VP of Engineering / Approver) |
| **Delegate** | jessica.taylor@acmecorp.com | Jessica Taylor (Acting Delegate for David) |
| **Finance** | inance.mgr@acmecorp.com | Rachel Green (Chief Financial Manager) |
| **Director** | director@acmecorp.com | Marcus Sterling (Director of Operations) |
| **CEO** | ceo@acmecorp.com | Eleanor Vance (Chief Executive Officer) |
