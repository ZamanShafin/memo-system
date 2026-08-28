# Evaluator Demonstration Walkthrough Guide (Section 28 Compliance)

**Course:** CSE226 Foundations of Vibe Coding  
**Live System URL:** https://memo-system-pjbj.vercel.app  
**Universal Demo Password:** password123  
**Active Organization:** acme  

---

## 14-Step Comprehensive Demonstration Guide

### Scenario 1: Create an Organization (Multi-Tenant Registration)
1. Navigate to https://memo-system-pjbj.vercel.app
2. Click **Register Organization**.
3. Fill in Organization Name, Unique Tenant Code, Administrator Email, and Password.
4. Submit and verify automated login into the newly provisioned workspace.

### Scenario 2: Create Multiple Users Belonging to That Organization
1. From the top navigation bar, navigate to **Org Admin -> User Management**.
2. Click **+ Add User** and create staff members with specific roles and designations.
3. Verify they appear in the organization user table.

### Scenario 3: Create a Memorandum
1. Switch to **Alex Morgan** (alex.morgan@acmecorp.com) via the top **Demo Switcher**.
2. Click **New Memo**.
3. Enter title, category (*Procurement*), priority (*Urgent*), and rich text body in the Quill.js editor.

### Scenario 4: Define a Sequential Workflow Involving Multiple Users
1. Select the 5-tier standard approval chain: *Requester -> Dept Head -> Finance -> Director -> CEO*.
2. Verify step order and assigned turn holders.

### Scenario 5: Submit the Memo into the Workflow
1. Click **Submit to Workflow**.
2. System assigns a sequential identifier (MEMO-ACME-2026-XXXX) and notifies the department head.

### Scenario 6: Log In as the First Workflow Participant
1. Switch to **David Vance (VP of Engineering)** via the Demo Switcher.
2. Open **Action Inbox** and locate the urgent review item.

### Scenario 7: Comment, Approve, Reject, or Request Changes
1. Open the memo detail view.
2. Click **Approve Step** and enter rationale comment: Technical compute requirements approved.

### Scenario 8: Demonstrate Memo Moving to the Next Participant
1. Switch to **Rachel Green (Finance Manager)**.
2. Verify the memo is now in Rachel's Action Inbox awaiting financial authorization.

### Scenario 9: Demonstrate Complete Workflow History & Visual Timeline
1. Inspect the visual timeline displaying completed checks, comments, and the pulsing active turn indicator.

### Scenario 10: Demonstrate Final Approval and PDF Generation
1. Switch to **Eleanor Vance (CEO)** and click **Approve Step**.
2. Memo transitions to **Approved**. Click **Download Corporate PDF** to inspect the sealed document with signatures and QR verification.

### Scenario 11: Demonstrate In-App Notifications
1. Switch back to **Alex Morgan** and click the **Notification Bell** in the header to inspect real-time alerts.

### Scenario 12: Demonstrate Search & Faceted Filtering
1. Go to **Search & Filter**, filter by keyword query, status, and category.

### Scenario 13: Demonstrate Administrative Functionality
1. Switch to **Sarah Jenkins (Admin)**.
2. Manage departments, users (self-protection enabled), templates, and inspect audit logs.

### Scenario 14: Demonstrate Cross-Tenant Isolation
1. Log in under any other organization code.
2. Verify zero access to Acme memos with strict 404/403 data perimeter protection.
