import datetime
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_auth(email: str = "alex.morgan@acmecorp.com", org_code: str = "acme"):
    res = client.post("/api/v1/auth/login", json={
        "org_code": org_code,
        "email": email,
        "password": "password123"
    })
    data = res.json()
    return data["access_token"], data["user"]


def test_delegation_approval_workflow():
    head_token, head_user = get_auth("head.eng@acmecorp.com")
    alex_token, alex_user = get_auth("alex.morgan@acmecorp.com")
    jessica_token, jessica_user = get_auth("jessica.taylor@acmecorp.com")

    now = datetime.datetime.now(datetime.timezone.utc)
    start_str = (now - datetime.timedelta(hours=1)).isoformat()
    end_str = (now + datetime.timedelta(days=2)).isoformat()

    # Head delegates authority to Jessica
    del_res = client.post("/api/v1/delegations", headers={"Authorization": f"Bearer {head_token}"}, json={
        "delegatee_id": jessica_user["id"],
        "start_date": start_str,
        "end_date": end_str,
        "reason": "Annual executive leave"
    })
    assert del_res.status_code == 200
    delegation_id = del_res.json()["id"]

    # Alex creates memo assigned to Head
    create_res = client.post("/api/v1/memos", headers={"Authorization": f"Bearer {alex_token}"}, json={
        "title": "Delegated Approval Test Memo",
        "body": "<p>Requesting signoff during executive leave</p>",
        "priority": "Normal",
        "is_draft": False,
        "workflow_steps": [
            {"role_name": "Department Head", "step_type": "final_approval", "assigned_user_id": head_user["id"]}
        ]
    })
    assert create_res.status_code == 200
    memo_id = create_res.json()["id"]

    # Jessica approves ON BEHALF OF Head
    act_res = client.post(f"/api/v1/workflow/{memo_id}/action", headers={"Authorization": f"Bearer {jessica_token}"}, json={
        "action": "approve",
        "comment": "Approved on behalf of Engineering Head while on leave"
    })
    assert act_res.status_code == 200
    memo = act_res.json()
    assert memo["status"] == "Approved"

    # Verify step recorded delegation
    steps_res = client.get(f"/api/v1/workflow/{memo_id}/steps", headers={"Authorization": f"Bearer {alex_token}"})
    assert steps_res.status_code == 200
    steps = steps_res.json()
    head_step = steps[1]
    assert head_step["action_by_user_id"] == jessica_user["id"]
    assert head_step["on_behalf_of_user_id"] == head_user["id"]


def test_admin_department_and_category_management():
    admin_token, admin_user = get_auth("admin@acmecorp.com")
    ts = datetime.datetime.now().strftime("%H%M%S%f")

    # 1. Create Department
    dept_res = client.post("/api/v1/admin/departments", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "name": f"Quality Assurance {ts}",
        "description": "QA, Security auditing and automated testing"
    })
    assert dept_res.status_code == 200
    dept_id = dept_res.json()["id"]
    assert dept_res.json()["name"] == f"Quality Assurance {ts}"

    # 2. Update Department (deactivate non-destructively)
    up_dept = client.put(f"/api/v1/admin/departments/{dept_id}", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "name": f"QA & Systems {ts}",
        "is_active": False
    })
    assert up_dept.status_code == 200
    assert up_dept.json()["name"] == f"QA & Systems {ts}"
    assert up_dept.json()["is_active"] is False

    # 3. Create Memo Category
    cat_res = client.post("/api/v1/admin/categories", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "name": f"Vendor Contracts {ts}",
        "description": "Third party contracts and SLA agreements"
    })
    assert cat_res.status_code == 200
    cat_id = cat_res.json()["id"]
    assert cat_res.json()["name"] == f"Vendor Contracts {ts}"

    # 4. List Categories
    cats_res = client.get("/api/v1/admin/categories", headers={"Authorization": f"Bearer {admin_token}"})
    assert cats_res.status_code == 200
    cat_names = [c["name"] for c in cats_res.json()]
    assert f"Vendor Contracts {ts}" in cat_names


def test_workflow_template_crud():
    admin_token, admin_user = get_auth("admin@acmecorp.com")
    head_token, head_user = get_auth("head.eng@acmecorp.com")

    # Create Template
    create_tmpl = client.post("/api/v1/admin/templates", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "name": "Standard IT Equipment Request",
        "description": "Hardware and workstation procurement approval cycle",
        "steps": [
            {"role_name": "Line Lead", "step_type": "review", "default_user_id": None},
            {"role_name": "Department Head", "step_type": "approval", "default_user_id": head_user["id"]},
            {"role_name": "Finance Director", "step_type": "final_approval", "default_user_id": None}
        ]
    })
    assert create_tmpl.status_code == 200
    tmpl_id = create_tmpl.json()["id"]

    # List Templates
    list_tmpl = client.get("/api/v1/admin/templates", headers={"Authorization": f"Bearer {admin_token}"})
    assert list_tmpl.status_code == 200
    assert any(t["id"] == tmpl_id for t in list_tmpl.json())

    # Delete Template
    del_tmpl = client.delete(f"/api/v1/admin/templates/{tmpl_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_tmpl.status_code == 200


def test_notifications_and_unread_count():
    alex_token, alex_user = get_auth("alex.morgan@acmecorp.com")

    # Fetch notifications
    notifs_res = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {alex_token}"})
    assert notifs_res.status_code == 200
    notifs = notifs_res.json()
    assert isinstance(notifs, list)

    # Fetch unread count
    cnt_res = client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {alex_token}"})
    assert cnt_res.status_code == 200
    assert "unread_count" in cnt_res.json()

    # Mark all read
    mark_res = client.post("/api/v1/notifications/mark-all-read", headers={"Authorization": f"Bearer {alex_token}"})
    assert mark_res.status_code == 200

    # Verify unread count is 0
    cnt_res2 = client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {alex_token}"})
    assert cnt_res2.json()["unread_count"] == 0


def test_audit_logs_rbac():
    admin_token, admin_user = get_auth("admin@acmecorp.com")
    user_token, user_user = get_auth("alex.morgan@acmecorp.com")

    # Admin can view audit logs
    admin_res = client.get("/api/v1/audit/logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_res.status_code == 200
    logs = admin_res.json()
    assert len(logs) > 0
    assert logs[0]["org_id"] == admin_user["org_id"]

    # Regular user is forbidden from accessing audit logs
    user_res = client.get("/api/v1/audit/logs", headers={"Authorization": f"Bearer {user_token}"})
    assert user_res.status_code == 403


def test_reporting_statistics():
    admin_token, admin_user = get_auth("admin@acmecorp.com")

    res = client.get("/api/v1/reports/statistics", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()

    assert "total_memos" in data
    assert "pending_approvals" in data
    assert "completed_memos" in data
    assert "memos_by_status" in data
    assert "memos_by_department" in data
    assert "memos_by_category" in data
    assert data["total_users"] >= 7
