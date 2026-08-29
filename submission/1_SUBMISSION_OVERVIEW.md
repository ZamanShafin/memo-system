# CSE226 Fundamentals of Vibe Coding — Final Project Submission

## Project Title: Multi-Tenant Inter-Office Memo Management System
**Course:** CSE226 Fundamentals of Vibe Coding  
**Institution:** North South University  
**Student / Submitter:** Zaman Shafin  
**Repository:** [https://github.com/ZamanShafin/memo-system](https://github.com/ZamanShafin/memo-system)  
**Submission Date:** August 2026  

---

## 1. Key Submission Deliverables & URLs

| Requirement | Artifact / Target | Link / Location |
| :--- | :--- | :--- |
| **Section 23: Deployed System URL** | Live Production Web Application | [https://memo-system-pjbj.vercel.app](https://memo-system-pjbj.vercel.app) |
| **Section 24: Source Code Archive** | Direct Downloadable ZIP Archive | [https://github.com/ZamanShafin/memo-system/raw/main/source_code.zip](https://github.com/ZamanShafin/memo-system/raw/main/source_code.zip) |
| **Section 25: Setup Documentation** | Complete Installation & Run Guide | [3_INSTALLATION_AND_SETUP.md](./3_INSTALLATION_AND_SETUP.md) |
| **Section 26: Project Documentation** | Formal Technical Report (26.1–26.10) | [2_PROJECT_DOCUMENTATION.md](./2_PROJECT_DOCUMENTATION.md) |
| **Section 27: AI Interaction History** | Full Chronological Prompt/Response Log | [5_AI_PROMPT_AND_RESPONSE_LOG.md](./5_AI_PROMPT_AND_RESPONSE_LOG.md) |
| **Section 28: Demonstration Guide** | 14-Step Evaluator Walkthrough Guide | [4_DEMONSTRATION_WALKTHROUGH.md](./4_DEMONSTRATION_WALKTHROUGH.md) |

---

## 2. Pre-Configured Demonstration Accounts

To facilitate evaluation, the live deployment at [https://memo-system-pjbj.vercel.app](https://memo-system-pjbj.vercel.app) includes pre-configured corporate demonstration accounts across the organizational hierarchy.

> **Universal Demonstration Password:** password123  
> **Active Organization Code:** cme

| Role / Persona | Name | Email | System Role | Department / Function | Evaluation Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **System Administrator** | Sarah Jenkins | dmin@acmecorp.com | dmin | Executive Operations | User management, department creation/deletion, audit trail inspection |
| **Requester / Team Lead** | Alex Morgan | lex.morgan@acmecorp.com | user | Engineering & Technology | Authoring memos, resubmitting change requests, tracking workflows |
| **Department Head** | David Vance | head.eng@acmecorp.com | user | Engineering & Technology | Tier-1 approvals, requesting changes, assigning temporary delegations |
| **Acting Delegate** | Jessica Taylor | jessica.taylor@acmecorp.com | user | Engineering & Technology | Demonstrating active delegation sign-off on behalf of David Vance |
| **Finance Manager** | Rachel Green | inance.mgr@acmecorp.com | user | Finance & Accounts | Tier-2 budget approvals, financial reviews, rejection flows |
| **Director of Operations** | Marcus Sterling | director@acmecorp.com | user | Procurement & Operations | Tier-3 operational endorsements, dynamic mid-stream reviewer injection |
| **Chief Executive Officer** | Eleanor Vance | ceo@acmecorp.com | user | Executive Office | Final executive sign-off, PDF seal generation, workflow closure |

> **Note on 1-Click Fast Switcher:** A built-in **Demo Switcher** dropdown is accessible in the top navigation bar of the application, allowing evaluators to switch between personas with a single click without manually re-typing credentials.

---

## 3. Submission Package Contents

This submission/ folder contains everything required for assessment:

1. 1_SUBMISSION_OVERVIEW.md — This master executive summary and reference card.
2. 2_PROJECT_DOCUMENTATION.md — The technical specification document covering system architecture, ER diagrams, sequential approval mechanics, multi-tenant isolation, security policies, vibe-coding process, and requirements compliance.
3. 3_INSTALLATION_AND_SETUP.md — Complete instructions for reproducing, installing, configuring, testing, and running the system in any local or cloud environment.
4. 4_DEMONSTRATION_WALKTHROUGH.md — A structured, step-by-step evaluator script demonstrating all 14 grading scenarios required by Section 28.
5. 5_AI_PROMPT_AND_RESPONSE_LOG.md — The full transcript of all AI prompts, generated code, debugging sessions, and iterative refinements.
6. source_code.zip — Complete source code archive.
