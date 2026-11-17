"""
HealthBridge AI - Automated Tests for Authentication & Authorization
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.connection import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_register_and_login_flow():
    email = "testuser_phase1@example.com"
    pwd = "SecurePassword123!"

    # 1. Register
    reg_res = client.post("/auth/register", json={
        "name": "Alex Mercer",
        "email": email,
        "password": pwd,
        "confirm_password": pwd
    })
    # Could be 201 or 409 if run repeatedly
    assert reg_res.status_code in [201, 409]

    # 2. Login
    login_res = client.post("/auth/login", json={
        "email": email,
        "password": pwd
    })
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email
    assert "password_hash" not in data["user"]

    token = data["access_token"]

    # 3. Authenticated profile check
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

def test_password_mismatch():
    res = client.post("/auth/register", json={
        "name": "Mismatch User",
        "email": "mismatch@example.com",
        "password": "PasswordOne",
        "confirm_password": "PasswordTwo"
    })
    assert res.status_code == 400
    assert "Passwords do not match" in res.json()["detail"]

def test_invalid_login():
    res = client.post("/auth/login", json={
        "email": "nonexistent_hb_user@example.com",
        "password": "WrongPassword!"
    })
    assert res.status_code == 401

def test_unauthorized_access():
    res = client.get("/auth/me")
    assert res.status_code == 401
