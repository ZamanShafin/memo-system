# Vibe-Coding Process & AI-Assisted Development Report

**Course:** CSE226 Foundations of Vibe Coding  
**Student / Author:** Zaman Shafin  
**Tool Used:** Google Antigravity AI Pair Programming Agent  

---

## 1. AI Tools & Environment Setup

Development was conducted entirely using the **Google Antigravity AI Pair Programming Agent**, operating in an agentic development environment equipped with direct terminal execution, file inspection, AST validation, and automated testing tools.

---

## 2. Prompting Strategy & Requirement Communication

Requirements were communicated in a structured, modular, and iterative fashion:

1. **Domain Modeling & Schema Prompting:**  
   Prompted the AI to design the foundational PostgreSQL database models with explicit foreign-key tenant scoping (org_id) across all entities.
2. **Workflow State Machine Implementation:**  
   Specified the deterministic sequential workflow transitions (*Draft → Pending Review → Pending Approval → Changes Requested → Approved / Rejected*), turn enforcement, and date-bounded delegation rules.
3. **UI / UX & Responsive Frontend Design:**  
   Instructed the AI to build a clean Single-Page Application (SPA) using Tailwind CSS, Quill.js for rich text, and Chart.js for real-time analytics, with strict responsive constraints for mobile screens (320px–390px).
4. **Security & Edge-Case Guardrails:**  
   Prompted the AI to add defensive rules such as administrator self-deactivation protection, department deletion with safe member unassignment, and parameterized SQL queries.

---

## 3. Evaluation, Debugging & Error Correction

Whenever issues arose during development, they were identified and resolved through rigorous inspection:

- **Diagnosing View Panel HTML Nesting Bug:**  
  *Issue:* When switching tabs on mobile, view panels appeared blank.  
  *Diagnosis & Fix:* Used a Python HTML AST parser to discover that an unclosed </div> in #dashboard-view was nesting all other view panels inside it. Added the missing closing tag so all 13 view panels render as top-level independent siblings.
- **Fixing Dynamic Tenant Isolation Test:**  
  *Issue:* An earlier unit test failed because it attempted to query a deleted static organization (
exus).  
  *Diagnosis & Fix:* Refactored 	est_tenant_isolation_memos in 	ests/test_auth.py to dynamically register a unique isolated organization and verify that zero memos from Acme Corporation are accessible.
- **Mobile Viewport Overflow Elimination:**  
  *Issue:* Dashboard KPI cards and header badges wrapped and caused horizontal scroll spill on mobile viewports.  
  *Diagnosis & Fix:* Sized metric card paddings (p-3.5 sm:p-5), truncated header badges, and applied overflow-x: hidden !important containment.

---

## 4. Verification & Validation Methodology

To ensure that the AI-generated system demonstrably satisfies all requirements:

1. **Automated Pytest Suite:** Created and executed a comprehensive test suite (	ests/) containing 20 tests covering authentication, RBAC, tenant perimeter security, sequential approval progression, delegation handoff, version snapshot diffing, and PDF generation. All 20 tests consistently pass (20 passed).
2. **End-to-End Persona Verification:** Verified all 14 grading scenarios using the 7 pre-configured corporate personas.
3. **Continuous Production Deployment:** Automatically built and deployed every commit to Vercel Serverless runtime (https://memo-system-pjbj.vercel.app), verifying behavior in live desktop and mobile browsers.
