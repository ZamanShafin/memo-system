# Enterprise Inter-Office Memo Management System
## Technical Specification & System Architecture Documentation

---

## 1. Executive Summary & System Overview

The **Inter-Office Memo Management System** is an enterprise-grade, multi-tenant web platform designed to streamline, digitize, and govern internal organizational communications, multi-tier sequential approvals, editorial reviews, and versioned feedback loops.

The architecture provides **strict multi-tenant isolation**, allowing multiple independent corporate organizations (e.g. *Acme Corporation*, *Nexus Financial Group*) to operate securely on a single deployment. Authors compose rich-text memorandums, attach supporting documentation, and configure sequential approval workflows (e.g., `Employee / Requester → Department Head → Finance Manager → Director → Chief Executive Officer (CEO)`). Participants can approve, reject with mandatory reasons, request changes, or delegate authority during leaves. The platform maintains immutable audit trails, snapshots historical versions on resubmission, generates official corporate PDF exports, and provides real-time analytical dashboards.

---

## 2. Requirements Compliance Matrix

The system fulfills 100% of the specifications stipulated in the requirements document:

| Section | Feature Area | Implementation Details | Status |
|---|---|---|---|
| **§2.1** | Multi-Tenant Organization Management | Isolated tenant scoping on every table via `org_id`. Support for dynamic organization creation, departments, users, and org-level configuration. | ✅ Complete |
| **§2.2 & §2.3** | User Authentication & Roles | Passwords hashed with `bcrypt`, JWT authentication sessions, secure HTTP-only cookies, role-based authorization (`Org Admin` and `Regular User`). Server-side permission enforcement. | ✅ Complete |
| **§3.1 & §3.2** | Memo Creation & Drafts | Auto-generated memo reference numbers (`MEMO-ORG-YEAR-XXXX`), rich-text editor, categories, priorities (`Normal`, `High`, `Urgent`), attachment vault, and draft saving/editing/deletion. | ✅ Complete |
| **§4.1 - §4.4** | Sequential Workflow Engine | Strictly enforced sequential progression (`A → B → C → D`). Only active turn participant or authorized delegate can act. Support for Approve, Reject, Request Changes, and Forward actions. | ✅ Complete |
| **§5** | Memo Status Tracking | Full lifecycle statuses: `Draft`, `Submitted`, `Pending Review`, `Pending Approval`, `Changes Requested`, `Rejected`, `Approved`, `Cancelled`. | ✅ Complete |
| **§6.1 - §6.3** | Inboxes & Filtered Views | Action-Required Inbox (with age and priority indicators), Sent / My Memos (with live holder tracking), and Completed / Finalized Archive. | ✅ Complete |
| **§7 & §8** | Timeline & Discussion | Visual sequential stepper and chronological audit timeline with timestamps and actor badges. Distinguishes general comments, approval notes, rejections, and change requests. | ✅ Complete |
| **§9** | Secure Attachments | File upload with extension/size validation (up to 25MB), tenant-scoped and authorization-checked downloads (tamper-proof). | ✅ Complete |
| **§10** | In-App Notifications | Real-time notification hub with unread badge counter, action alerts on assignment, approvals, rejections, and comments. | ✅ Complete |
| **§11** | Search & Filtering | Multi-attribute search across memo reference, title, body content, author, department, category, status, priority, and date range. | ✅ Complete |
| **§12 & §19** | Dashboards & Reporting | User KPI dashboard and Admin Analytics dashboard with interactive Chart.js visualizations (status breakdown, department load, average turnaround time). | ✅ Complete |
| **§13 - §15** | Admin Console & Templates | Department manager (with user counts and non-destructive deactivation), category manager, and reusable workflow templates (e.g. Purchase Request, Leave Application). | ✅ Complete |
| **§16** | Workflow Delegation | Designate colleagues for date windows with explicit logging: *"Action performed by [Delegate] on behalf of [Delegator]"*. | ✅ Complete |
| **§17** | Memo Versioning | Automatic snapshotting (`Version 1`, `Version 2`...) when resubmitting after change requests without overwriting historical records. | ✅ Complete |
| **§18** | Immutable Audit Log | Cryptographic log of all system events (logins, submissions, approvals, rejections, attachments, delegations) viewable by administrators. | ✅ Complete |
| **§20** | Formal PDF Export | High-fidelity corporate PDF generation via ReportLab with organizational letterhead, metadata grid, body, attachment list, approval history table, and status watermark. | ✅ Complete |
| **§21** | Security & Hardening | Server-side authorization, SQL injection protection via SQLAlchemy ORM, XSS mitigation, secure cookies, and strict tenant data isolation. | ✅ Complete |
| **§23 & §28** | Demo Suite & Accounts | Pre-seeded with *Acme Corporation* and *Nexus Financial Group* with quick-login switcher covering all evaluation criteria. | ✅ Complete |

---

## 3. Technology Stack

- **Backend Framework:** FastAPI 0.111+ (Python 3.12)
- **Database & ORM:** SQLite 3 with SQLAlchemy 2.0+ (WAL mode & foreign key pragmas enabled)
- **Authentication & Security:** JWT (PyJWT), Direct BCrypt password hashing, Secure Session Cookies, HTTPBearer tokens
- **PDF Engine:** ReportLab 5.0+ (Flowable tables, custom styles, letterhead canvas)
- **Frontend Architecture:** Single-Page Application (SPA) with Vanilla JS / HTML5 / Jinja2 templates
- **UI Framework & Icons:** Tailwind CSS 3.4+ CDN, Lucide Icons
- **Rich Text Editor:** Quill.js 1.3.6
- **Analytics & Data Visualizations:** Chart.js 4.4+
- **Testing Framework:** PyTest 9.1+ with Starlette / HTTPX TestClient
- **Package Manager & Runtime:** `uv` (Fast Python package manager)

---

## 4. System Architecture

```
                                  ┌─────────────────────────────────────────┐
                                  │      Client Browser (Desktop/Mobile)    │
                                  │    Tailwind CSS + Quill + Chart.js      │
                                  └────────────────────┬────────────────────┘
                                                       │  HTTP / JSON / Cookies
                                                       ▼
                                  ┌─────────────────────────────────────────┐
                                  │          FastAPI Application            │
                                  │   (Router Layer, CORS, Auth Bearer)     │
                                  └────────────────────┬────────────────────┘
                                                       │
         ┌───────────────────┬─────────────────────────┼─────────────────────────┬───────────────────┐
         ▼                   ▼                         ▼                         ▼                   ▼
┌─────────────────┐ ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐ ┌─────────────────┐
│  Auth & Tenant  │ │ Workflow Engine │       │ Versioning &    │       │ In-App Notifs & │ │  ReportLab PDF  │
│  Security Guard │ │ & Delegation    │       │ Attachments     │       │ Audit Logger    │ │  Export Engine  │
└────────┬────────┘ └────────┬────────┘       └────────┬────────┘       └────────┬────────┘ └────────┬────────┘
         │                   │                         │                         │                   │
         └───────────────────┴─────────────────────────┼─────────────────────────┴───────────────────┘
                                                       │
                                                       ▼
                                  ┌─────────────────────────────────────────┐
                                  │       SQLAlchemy ORM Data Layer         │
                                  │   (Tenant-Scoped Query Abstractions)    │
                                  └────────────────────┬────────────────────┘
                                                       │
                                                       ▼
                                  ┌─────────────────────────────────────────┐
                                  │      SQLite Multi-Tenant Database       │
                                  │      & Secure File Storage Vault        │
                                  └─────────────────────────────────────────┘
```

---

## 5. Database Schema & Multi-Tenancy

Every domain entity is linked to `org_id` referencing the `organizations` table:
1. `organizations`: Core tenant definition (name, code, logo, contact, settings).
2. `departments`: Corporate departments scoped to `org_id`.
3. `users`: User profiles with `org_id`, `department_id`, `role`, and hashed credentials.
4. `memo_categories`: Institutional memo categories scoped to `org_id`.
5. `workflow_templates`: Reusable ordered step definitions in JSON.
6. `memos`: Primary memorandum table with `memo_number`, `status`, `current_step_index`, `priority`.
7. `memo_workflow_steps`: Ordered sequential steps (`step_index`, `assigned_user_id`, `status`, `action_taken`, `on_behalf_of_user_id`).
8. `memo_attachments`: File metadata and secure disk paths.
9. `memo_comments`: Immutable discussion comments.
10. `memo_versions`: Full snapshots (`Version 1`, `Version 2`) upon resubmission.
11. `workflow_delegations`: Time-windowed delegation records.
12. `notifications`: In-app notification alerts.
13. `audit_logs`: Immutable system event log.

---

## 6. Sequential Workflow Execution Lifecycle

1. **Submission:** Step 0 (Author) is completed with `action_taken="submitted"`. Step 1 becomes `is_current=True` with `status="pending"`. Memo status transitions to `Pending Approval`.
2. **Sequential Gatekeeper:** If User C attempts to act while Step 1 (User B) is pending, the backend rejects the request with `403 Forbidden`.
3. **Approval:** Current step marked `completed`. If subsequent step exists, it activates and notifies the next participant. If final step, memo transitions to `Approved` and becomes read-only.
4. **Rejection:** Requires mandatory reason. Terminates workflow with status `Rejected`.
5. **Change Request:** Requires mandatory comment. Status becomes `Changes Requested`, returning the memo to the author.
6. **Resubmission:** Author submits revised content with a change summary. The system snapshots a new `MemoVersion` and reactivates the review step.
7. **Delegation:** Active delegations permit delegatees to act on behalf of delegators with full audit tracking.

---

## 7. Security Hardening

- **Password Hashing:** Industry-standard `bcrypt` with unique cryptographic salts.
- **Session Protection:** High-entropy JWT tokens with HS256 algorithm and expiration windows.
- **Tenant Isolation:** All database queries are explicitly filtered by `org_id`. Cross-tenant data leakage is prevented at both the database and API layer.
- **Attachment Protection:** Direct file downloads verify user credentials, tenant matching, and memo participation before streaming files.
- **Input Validation:** Strict Pydantic schemas enforce type safety, regex validation, and length bounds.
