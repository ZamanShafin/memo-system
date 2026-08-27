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
