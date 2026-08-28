from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_success():
    res = client.post("/api/v1/auth/login", json={
        "org_code": "acme",
        "email": "alex.morgan@acmecorp.com",
        "password": "password123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alex.morgan@acmecorp.com"
    assert data["organization"]["code"] == "acme"

def test_login_invalid_password():
    res = client.post("/api/v1/auth/login", json={
        "org_code": "acme",
        "email": "alex.morgan@acmecorp.com",
        "password": "wrongpassword"
    })
    assert res.status_code == 401

def test_login_wrong_tenant():
    res = client.post("/api/v1/auth/login", json={
        "org_code": "nexus",
        "email": "alex.morgan@acmecorp.com",  # Belongs to Acme, not Nexus
        "password": "password123"
    })
    assert res.status_code == 401

def test_tenant_isolation_memos():
    import uuid
    unique_suffix = uuid.uuid4().hex[:6]
    test_code = f"iso{unique_suffix}"
    
    # Register new isolated organization
    reg_res = client.post("/api/v1/auth/register-organization", json={
        "name": f"Isolation Test {unique_suffix}",
        "code": test_code,
        "admin_name": "Iso Admin",
        "admin_email": f"admin@{test_code}.com",
        "admin_password": "password123"
    })
    assert reg_res.status_code == 200
    
    # Login as the new isolated organization admin
    login_res = client.post("/api/v1/auth/login", json={
        "org_code": test_code,
        "email": f"admin@{test_code}.com",
        "password": "password123"
    })
    assert login_res.status_code == 200
    iso_token = login_res.json()["access_token"]
    iso_org_id = login_res.json()["organization"]["id"]
    
    # Isolated user requests memos
    memos_res = client.get("/api/v1/memos/all", headers={"Authorization": f"Bearer {iso_token}"})
    assert memos_res.status_code == 200
    memos = memos_res.json()
    
    # Ensure NO Acme memos are visible to the isolated organization
    for m in memos:
        assert "ACME" not in m["memo_number"]
        assert m["org_id"] == iso_org_id

def test_forgot_password_reset():
    # 1. Reset password for Jessica
    reset_res = client.post("/api/v1/auth/reset-password", json={
        "org_code": "acme",
        "email": "jessica.taylor@acmecorp.com",
        "new_password": "newSecurePassword2026!"
    })
    assert reset_res.status_code == 200

    # 2. Login with old password -> 401 Unauthorized
    fail_res = client.post("/api/v1/auth/login", json={
        "org_code": "acme",
        "email": "jessica.taylor@acmecorp.com",
        "password": "password123"
    })
    assert fail_res.status_code == 401

    # 3. Login with new password -> 200 OK
    ok_res = client.post("/api/v1/auth/login", json={
        "org_code": "acme",
        "email": "jessica.taylor@acmecorp.com",
        "password": "newSecurePassword2026!"
    })
    assert ok_res.status_code == 200
    assert "access_token" in ok_res.json()

    # Reset back to password123 for consistent demo state
    client.post("/api/v1/auth/reset-password", json={
        "org_code": "acme",
        "email": "jessica.taylor@acmecorp.com",
        "new_password": "password123"
    })

