import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
from app.seed import seed_database

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield

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
    # Login as Nexus Financial User
    nexus_res = client.post("/api/v1/auth/login", json={
        "org_code": "nexus",
        "email": "lead.analyst@nexusgroup.com",
        "password": "password123"
    })
    nexus_token = nexus_res.json()["access_token"]
    
    # Nexus user requests memos
    memos_res = client.get("/api/v1/memos/all", headers={"Authorization": f"Bearer {nexus_token}"})
    assert memos_res.status_code == 200
    memos = memos_res.json()
    
    # Ensure NO Acme memos are visible to Nexus user
    for m in memos:
        assert "ACME" not in m["memo_number"]
        assert m["org_id"] == nexus_res.json()["organization"]["id"]

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

