# CSE226 Final Project Technical Documentation

### Multi-Tenant Inter-Office Memo Management System
**Deterministic Sequential Approval Workflow Engine & Document Governance SaaS**

---

| Field | Value |
| :--- | :--- |
| **Name:** | **M.N. Zaman Shafin** |
| **ID:** | **2232299030** |
| **Course & Semester:** | **CSE226 Fundamentals of Vibe Coding - Summer 2026** |
| **Deployed System URL:** | [https://memo-system-pjbj.vercel.app](https://memo-system-pjbj.vercel.app) |
| **Source Code Archive:** | [https://github.com/ZamanShafin/memo-system/raw/main/source_code.zip](https://github.com/ZamanShafin/memo-system/raw/main/source_code.zip) |
| **GitHub Repository:** | [https://github.com/ZamanShafin/memo-system](https://github.com/ZamanShafin/memo-system) |

---

## Table of content

1. [System Overview & Core Capabilities](#1-system-overview--core-capabilities) ................................................................................................. 3
2. [Requirements Implemented (Compliance Matrix)](#2-requirements-implemented-compliance-matrix) ............................................................................... 3
3. [Technology Stack](#3-technology-stack) ................................................................................................................................. 4
4. [System Architecture & Diagram](#4-system-architecture--diagram) .......................................................................................................... 6
5. [Database Design & Multi-Tenancy Enforcement](#5-database-design--multi-tenancy-enforcement) ................................................................................. 7
6. [Sequential Workflow Design & Turn Governance](#6-sequential-workflow-design--turn-governance) .............................................................................. 8
7. [Security Architecture & Access Control](#7-security-architecture--access-control) ............................................................................................ 10
8. [Known Limitations](#8-known-limitations) ............................................................................................................................. 10
9. [Deployment Information & Demonstration Accounts](#9-deployment-information--demonstration-accounts) ....................................................................... 10

---

## 1. System Overview & Core Capabilities

The **Inter-Office Memo Management System** is a full-stack, multi-tenant SaaS application built to digitize, govern, and audit corporate memorandum workflows. It eliminates fragmented email threads and physical paper slips by enforcing deterministic sequential approvals, active delegation, immutable version history, and cryptographic PDF generation.

### Key System Highlights

- **Multi-Tenant Isolation:** Logical data partitioning with non-nullable org_id scoping across every database query.
- **Strict Turn Governance:** Memos execute sequentially (*Requester -> Dept Head -> Finance -> Director -> CEO*). Later participants are physically blocked from acting early.
- **Active Delegation:** Temporary date-bounded approval authority handoffs when officers are on leave.
- **Dynamic Reviewer Injection:** Approvers can dynamically insert specialized reviewers (e.g. Legal Counsel) mid-stream.
- **Tamper-Evident Auditing:** Append-only audit logs with timestamps, actor IDs, comments, and client IPs.
- **PDF Seal Engine:** Generates official corporate PDFs complete with digital signatures and QR verification codes.

---

## 2. Requirements Implemented (Compliance Matrix)

| Ref # | Requirement Area | Implementation Highlights |
| :--- | :--- | :--- |
| **Req 1-4** | **Multi-Tenancy & RBAC** | Complete org_id data perimeters, Admin/User roles, department management. |
| **Req 5-7** | **Auth & Memo Authoring** | JWT tokens, password reset, Quill.js rich text editor, priority tags, file uploads. |
| **Req 8-10** | **Sequential Workflow Engine** | Strict linear turn execution, workflow templates, mid-stream reviewer insertion. |
| **Req 11-13** | **Decisions & Delegation** | Approve, Reject, Request Changes with audit notes; date-bounded delegation. |
| **Req 14-17** | **PDFs, Alerts & Versions** | Cryptographic PDF seal generation, notification tray, immutable version snapshots. |
| **Req 18-22** | **Audit & Security** | Append-only audit logs, turnaround charts, admin self-deactivation protection. |
| **Req 23-30** | **Deployment & Testing** | Live on Vercel, sanitized source ZIP, 20/20 passing pytest suite, full prompt log. |

---

## 3. Technology Stack

| Layer / Component | Technology & Libraries |
| :--- | :--- |
| **Backend API Framework** | **FastAPI** (Asynchronous Python 3.10+ REST framework) |
| **Database Engine & ORM** | **PostgreSQL 16** (Neon Serverless Cloud DB) + **SQLAlchemy 2.0 ORM** |
| **Authentication & Security** | **PyJWT** (JSON Web Tokens) + **Passlib** (PBKDF2-SHA256 & Bcrypt hashing) |
| **Frontend Single Page App** | **Vanilla JavaScript** SPA engine (pp.js) with zero build-step overhead |
| **Styling & Design System** | **Tailwind CSS** utility framework + **Lucide Icons** + **Google Fonts** |
| **Rich Text Authoring** | **Quill.js** WYSIWYG editor with custom toolbar & HTML sanitization |
| **Visualizations & Charts** | **Chart.js** for real-time status doughnuts and turnaround duration bars |
| **Document / PDF Engine** | **ReportLab** & **xhtml2pdf** with embedded signature stamps and QR codes |
| **Cloud Infrastructure** | **Vercel Serverless Functions** with automated CI/CD pipeline |
| **Testing & Tooling** | **Pytest** automated test harness (20/20 tests passing) + **Astral uv** |

---

## 4. System Architecture & Diagram

The application is structured into a clean 3-tier decoupled architecture comprising a Client SPA, a Stateless FastAPI REST API service layer, and a cloud-native PostgreSQL relational database.

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
*Figure: High-Level 3-Tier System Architecture Diagram*

---

## 5. Database Design & Multi-Tenancy Enforcement

Multi-tenancy is enforced through strict logical data partitioning. Every single table in the database contains a non-nullable foreign key referencing organizations.id. Multi-tenancy is guaranteed at the database and API layer through the following mechanisms:

- **Server-Side Query Scoping:** Every database query in all routers automatically includes models.Entity.org_id == current_user.org_id. Client-side filtering is never relied upon for security.
- **Direct Object Access Validation:** When accessing a resource by ID (e.g. GET /memos/10), the server verifies memo.org_id == current_user.org_id. If the tenant IDs mismatch, an immediate **HTTP 404/403** is thrown.
- **Cascade Isolation:** Deleting or modifying a department, user, or workflow step is strictly constrained to the user's organization.

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
*Figure: Entity-Relationship & Multi-Tenancy Diagram*

---

## 6. Sequential Workflow Design & Turn Governance

The sequential workflow engine operates as a deterministic finite-state machine with strict turn-based locks. Only the currently assigned participant (or their authorized active delegate) can sign off.

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
*Figure: Sequential Approval Workflow State Machine Diagram*

### Operational Behavior & Governance

| Workflow Stage / Rule | Operational Behavior & Governance |
| :--- | :--- |
| **Draft -> Submission** | Author drafts memo and defines sequence. Submitting advances turn to Step 1 and dispatches notifications. |
| **Step-by-Step Turns** | Step N must be completed before Step N+1 can act. Later approvers are physically blocked by server-side checks. |
| **Dynamic Reviewer Insertion** | Approver can select *'Approve & Add Reviewer'* to insert a specialist (e.g. Legal Counsel) before next step. |
| **Decline & Reroute** | Turn holder can reassign their active step to an eligible colleague in the same organization. |
| **Delegation Protocol** | When active date window is valid, designated delegatee can sign off on behalf of delegator with full audit attribution. |
| **Changes Requested Cycle** | Reviewer returns memo with comments. Author updates content; system creates MemoVersion snapshot before resubmission. |
| **Final Approval & Seal** | Final approver (CEO) marks workflow Approved. System locks content as read-only and generate official signed PDF. |

---

## 7. Security Architecture & Access Control

- **Cryptographic Passwords:** Passwords are salted and encrypted using PBKDF2-SHA256 and Bcrypt algorithms.
- **JWT Bearer Sessions:** Stateless tokens signed with HMAC-SHA256 with 24-hour expiration.
- **Admin Self-Protection:** Dedicated server-side rules block administrators from deactivating or demoting their own accounts.
- **Injection & XSS Defenses:** Parameterized queries via SQLAlchemy prevent SQL injection; rich text HTML is sanitized before rendering.
- **Secure Cloud Connection:** Database connection strictly requires SSL/TLS encryption (sslmode=require).

---

## 8. Known Limitations

1. **In-App Notification Transport:** Uses responsive client-side HTTP polling rather than full-duplex WebSockets.
2. **Object Storage:** File attachments are persisted within the PostgreSQL database layer rather than external AWS S3 buckets.
3. **Two-Factor Authentication:** MFA/TOTP is reserved for future enterprise roadmap versions.

---

## 9. Deployment Information & Demonstration Accounts

- **Live Deployed URL:** [https://memo-system-pjbj.vercel.app](https://memo-system-pjbj.vercel.app)
- **Source Code ZIP:** [https://github.com/ZamanShafin/memo-system/raw/main/source_code.zip](https://github.com/ZamanShafin/memo-system/raw/main/source_code.zip)
- **Active Organization Code:** cme
- **Universal Password:** password123

| Role | Login Email | Persona / Purpose |
| :--- | :--- | :--- |
| **Admin** | dmin@acmecorp.com | Sarah Jenkins (System Administrator) |
| **Author** | lex.morgan@acmecorp.com | Alex Morgan (Senior Engineer / Author) |
| **Dept Head** | head.eng@acmecorp.com | David Vance (VP of Engineering / Approver) |
| **Delegate** | jessica.taylor@acmecorp.com | Jessica Taylor (Acting Delegate for David) |
| **Finance** | inance.mgr@acmecorp.com | Rachel Green (Chief Financial Manager) |
| **Director** | director@acmecorp.com | Marcus Sterling (Director of Operations) |
| **CEO** | ceo@acmecorp.com | Eleanor Vance (Chief Executive Officer) |
