import io
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

def test_draft_lifecycle():
    token, user = get_auth()

    # Create Draft
    create_res = client.post("/api/v1/memos", headers={"Authorization": f"Bearer {token}"}, json={
        "title": "Draft Architecture Plan",
        "body": "<p>Initial engineering specifications...</p>",
        "is_draft": True,
        "workflow_steps": []
    })
    assert create_res.status_code == 200
    memo = create_res.json()
    assert memo["status"] == "Draft"
    memo_id = memo["id"]

    # Update Draft
    update_res = client.put(f"/api/v1/memos/{memo_id}", headers={"Authorization": f"Bearer {token}"}, json={
        "title": "Draft Architecture Plan (Revised)",
        "body": "<p>Updated engineering content with benchmarks</p>",
        "priority": "High"
    })
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Draft Architecture Plan (Revised)"

    # Delete Draft
    del_res = client.delete(f"/api/v1/memos/{memo_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200

def test_versioning_on_change_request_and_resubmit():
    employee_token, employee_user = get_auth("alex.morgan@acmecorp.com")
    head_token, head_user = get_auth("head.eng@acmecorp.com")

    # 1. Create Memo
    create_res = client.post("/api/v1/memos", headers={"Authorization": f"Bearer {employee_token}"}, json={
        "title": "Tooling Budget Request V1",
        "body": "<p>Initial tooling budget</p>",
        "is_draft": False,
        "workflow_steps": [
            {"role_name": "Department Head", "step_type": "approval", "assigned_user_id": head_user["id"]}
        ]
    })
    assert create_res.status_code == 200
    memo_id = create_res.json()["id"]

    # 2. Dept Head requests changes
    client.post(f"/api/v1/workflow/{memo_id}/action", headers={"Authorization": f"Bearer {head_token}"}, json={
        "action": "request_changes",
        "comment": "Please attach vendor quotation and per-seat metrics."
    })

    # 3. Employee resubmits with updated body & summary
    resubmit_res = client.post(f"/api/v1/memos/{memo_id}/resubmit", headers={"Authorization": f"Bearer {employee_token}"}, json={
        "title": "Tooling Budget Request V2 (With Quotation)",
        "body": "<p>Updated budget request with itemized vendor pricing and ROI analysis</p>",
        "summary_of_changes": "Attached vendor quotes and ROI projections requested by Dept Head"
    })
    assert resubmit_res.status_code == 200
    resub_memo = resubmit_res.json()
    assert resub_memo["status"] == "Pending Approval"

    # Verify versions snapshot created
    detail_res = client.get(f"/api/v1/memos/{memo_id}", headers={"Authorization": f"Bearer {employee_token}"})
    versions = detail_res.json()["versions"]
    assert len(versions) >= 2
    assert versions[-1]["version_number"] >= 2

def test_pdf_export():
    token, user = get_auth()
    memos_res = client.get("/api/v1/memos/completed", headers={"Authorization": f"Bearer {token}"})
    memos = memos_res.json()
    target_id = memos[0]["id"] if memos else 1

    res = client.get(f"/api/v1/memos/{target_id}/pdf", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert len(res.content) > 1000

def test_attachment_upload_and_download():
    token, user = get_auth()
    file_content = b"Enterprise proposal and technical benchmark attachment content"
    file_obj = io.BytesIO(file_content)

    upload_res = client.post(
        "/api/v1/memos/1/attachments",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("vendor_quote.txt", file_obj, "text/plain")}
    )
    assert upload_res.status_code == 200
    att_data = upload_res.json()
    assert att_data["original_name"] == "vendor_quote.txt"
    att_id = att_data["id"]

    # Download attachment
    dl_res = client.get(f"/api/v1/memos/1/attachments/{att_id}", headers={"Authorization": f"Bearer {token}"})
    assert dl_res.status_code == 200
    assert dl_res.content == file_content
