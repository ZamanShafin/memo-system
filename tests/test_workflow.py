import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_auth(email: str, org_code: str = "acme"):
    res = client.post("/api/v1/auth/login", json={
        "org_code": org_code,
        "email": email,
        "password": "password123"
    })
    data = res.json()
    return data["access_token"], data["user"]

def test_sequential_workflow_creation_and_approval():
    employee_token, employee_user = get_auth("alex.morgan@acmecorp.com")
    head_token, head_user = get_auth("head.eng@acmecorp.com")
    finance_token, finance_user = get_auth("finance.mgr@acmecorp.com")
    director_token, director_user = get_auth("director@acmecorp.com")

    # 1. Employee creates memo with sequential workflow
    create_res = client.post("/api/v1/memos", headers={"Authorization": f"Bearer {employee_token}"}, json={
        "title": "Test Cloud Compute Capacity Reservation",
        "body": "<p>Request for cloud compute capacity</p>",
        "priority": "High",
        "is_draft": False,
        "workflow_steps": [
            {"role_name": "Department Head", "step_type": "approval", "assigned_user_id": head_user["id"]},
            {"role_name": "Finance Manager", "step_type": "approval", "assigned_user_id": finance_user["id"]},
            {"role_name": "Director of Operations", "step_type": "final_approval", "assigned_user_id": director_user["id"]}
        ]
    })
    assert create_res.status_code == 200
    memo = create_res.json()
    memo_id = memo["id"]
    assert memo["status"] == "Pending Approval"
    assert memo["current_step_index"] == 1

    # 2. Out-of-order security check: Director (Step 3) tries to approve while at Step 1 (Dept Head)
    bad_res = client.post(f"/api/v1/workflow/{memo_id}/action", headers={"Authorization": f"Bearer {director_token}"}, json={
        "action": "approve",
        "comment": "Attempting to skip sequence"
    })
    assert bad_res.status_code == 403  # Strictly blocked!

    # 3. Dept Head approves Step 1
    s1_res = client.post(f"/api/v1/workflow/{memo_id}/action", headers={"Authorization": f"Bearer {head_token}"}, json={
        "action": "approve",
        "comment": "Endorsed by Engineering Head"
    })
    assert s1_res.status_code == 200
    m_after_s1 = s1_res.json()
    assert m_after_s1["current_step_index"] == 2
    assert m_after_s1["status"] == "Pending Approval"

    # 4. Finance approves Step 2
    s2_res = client.post(f"/api/v1/workflow/{memo_id}/action", headers={"Authorization": f"Bearer {finance_token}"}, json={
        "action": "approve",
        "comment": "Budget allocation confirmed"
    })
    assert s2_res.status_code == 200
    m_after_s2 = s2_res.json()
    assert m_after_s2["current_step_index"] == 3

    # 5. Director gives Final Approval
    s3_res = client.post(f"/api/v1/workflow/{memo_id}/action", headers={"Authorization": f"Bearer {director_token}"}, json={
        "action": "approve",
        "comment": "Final operational sign-off completed"
    })
    assert s3_res.status_code == 200
    final_memo = s3_res.json()
    assert final_memo["status"] == "Approved"
    assert final_memo["final_approver_id"] is not None

def test_rejection_requires_comment():
    employee_token, employee_user = get_auth("alex.morgan@acmecorp.com")
    head_token, head_user = get_auth("head.eng@acmecorp.com")

    # Create memo
    create_res = client.post("/api/v1/memos", headers={"Authorization": f"Bearer {employee_token}"}, json={
        "title": "Test Rejection Memo",
        "body": "<p>Content</p>",
        "priority": "Normal",
        "is_draft": False,
        "workflow_steps": [
            {"role_name": "Department Head", "step_type": "approval", "assigned_user_id": head_user["id"]}
        ]
    })
    assert create_res.status_code == 200
    memo_id = create_res.json()["id"]

    # Try rejecting without reason -> 400 Bad Request
    fail_res = client.post(f"/api/v1/workflow/{memo_id}/action", headers={"Authorization": f"Bearer {head_token}"}, json={
        "action": "reject",
        "comment": ""
    })
    assert fail_res.status_code == 400

    # Reject with proper reason
    ok_res = client.post(f"/api/v1/workflow/{memo_id}/action", headers={"Authorization": f"Bearer {head_token}"}, json={
        "action": "reject",
        "comment": "Exceeds annual quarterly discretionary allocation limits."
    })
    assert ok_res.status_code == 200
    assert ok_res.json()["status"] == "Rejected"


def test_decline_and_reassign_workflow_step():
    employee_token, employee_user = get_auth("alex.morgan@acmecorp.com")
    head_token, head_user = get_auth("head.eng@acmecorp.com")
    qa_token, qa_user = get_auth("jessica.taylor@acmecorp.com")

    # 1. Author submits memo to Dept Head
    create_res = client.post("/api/v1/memos", headers={"Authorization": f"Bearer {employee_token}"}, json={
        "title": "Hardware Upgrade Request",
        "body": "<p>Hardware upgrade details</p>",
        "priority": "Normal",
        "is_draft": False,
        "workflow_steps": [
            {"role_name": "Technical Reviewer", "step_type": "approval", "assigned_user_id": head_user["id"]}
        ]
    })
    assert create_res.status_code == 200
    memo_id = create_res.json()["id"]

    # 2. Dept Head declines and reroutes to QA Specialist (Jessica)
    reassign_res = client.post(f"/api/v1/workflow/{memo_id}/action", headers={"Authorization": f"Bearer {head_token}"}, json={
        "action": "reassign",
        "comment": "Not in my current domain, rerouting to QA Specialist Jessica.",
        "reassign_to_user_id": qa_user["id"]
    })
    assert reassign_res.status_code == 200
    updated_memo = reassign_res.json()
    assert updated_memo["current_assignee_id"] == qa_user["id"]

    # 3. QA Specialist approves
    qa_res = client.post(f"/api/v1/workflow/{memo_id}/action", headers={"Authorization": f"Bearer {qa_token}"}, json={
        "action": "approve",
        "comment": "Approved by QA Specialist."
    })
    assert qa_res.status_code == 200
    assert qa_res.json()["status"] == "Approved"


def test_approve_and_insert_intermediate_reviewer():
    employee_token, employee_user = get_auth("alex.morgan@acmecorp.com")
    head_token, head_user = get_auth("head.eng@acmecorp.com")
    finance_token, finance_user = get_auth("finance.mgr@acmecorp.com")

    # 1. Author submits memo with Dept Head as Step 1
    create_res = client.post("/api/v1/memos", headers={"Authorization": f"Bearer {employee_token}"}, json={
        "title": "Ad-Hoc Budget Allocation",
        "body": "<p>Budget request</p>",
        "priority": "High",
        "is_draft": False,
        "workflow_steps": [
            {"role_name": "Dept Head", "step_type": "approval", "assigned_user_id": head_user["id"]}
        ]
    })
    assert create_res.status_code == 200
    memo_id = create_res.json()["id"]

    # 2. Dept Head approves but inserts Finance Manager before finalizing
    insert_res = client.post(f"/api/v1/workflow/{memo_id}/action", headers={"Authorization": f"Bearer {head_token}"}, json={
        "action": "approve_insert",
        "comment": "Endorsed, but requires Finance Manager cost sign-off.",
        "insert_step": {
            "role_name": "Finance Reviewer",
            "step_type": "approval",
            "assigned_user_id": finance_user["id"]
        }
    })
    assert insert_res.status_code == 200
    m_inserted = insert_res.json()
    assert m_inserted["current_assignee_id"] == finance_user["id"]
    assert m_inserted["status"] == "Pending Approval"
    assert len(m_inserted["workflow_steps"]) == 3  # Author (0) + Dept Head (1) + Finance (2)

    # 3. Finance Manager approves and finalizes
    fin_res = client.post(f"/api/v1/workflow/{memo_id}/action", headers={"Authorization": f"Bearer {finance_token}"}, json={
        "action": "approve",
        "comment": "Budget approved."
    })
    assert fin_res.status_code == 200
    assert fin_res.json()["status"] == "Approved"


def test_modify_downstream_workflow_steps():
    employee_token, employee_user = get_auth("alex.morgan@acmecorp.com")
    head_token, head_user = get_auth("head.eng@acmecorp.com")
    director_token, director_user = get_auth("director@acmecorp.com")
    ceo_token, ceo_user = get_auth("ceo@acmecorp.com")

    # 1. Author submits memo with 2 steps (Dept Head -> Director)
    create_res = client.post("/api/v1/memos", headers={"Authorization": f"Bearer {employee_token}"}, json={
        "title": "Strategic Roadmap Document",
        "body": "<p>Roadmap content</p>",
        "priority": "Normal",
        "is_draft": False,
        "workflow_steps": [
            {"role_name": "Dept Head", "step_type": "approval", "assigned_user_id": head_user["id"]},
            {"role_name": "Director", "step_type": "approval", "assigned_user_id": director_user["id"]}
        ]
    })
    assert create_res.status_code == 200
    memo_id = create_res.json()["id"]

    # 2. Dept Head updates downstream steps to replace Director with CEO directly
    modify_res = client.put(f"/api/v1/workflow/{memo_id}/steps", headers={"Authorization": f"Bearer {head_token}"}, json={
        "steps": [
            {"role_name": "Executive Sign-off", "step_type": "final_approval", "assigned_user_id": ceo_user["id"]}
        ]
    })
    assert modify_res.status_code == 200
    m_mod = modify_res.json()
    downstream_roles = [s["role_name"] for s in m_mod["workflow_steps"] if s["step_index"] > m_mod["current_step_index"]]
    assert downstream_roles == ["Executive Sign-off"]
