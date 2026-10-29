import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_register_and_login():
    email = "autotest_emp@company.com"
    reg_resp = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Automated Tester",
            "password": "testpassword123",
            "role": "EMPLOYEE",
        },
    )
    assert reg_resp.status_code in (201, 400)

    login_resp = client.post(
        "/auth/login",
        json={"email": email, "password": "testpassword123"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_get_profile():
    email = "autotest_profile@company.com"
    client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Profile Tester",
            "password": "testpassword123",
            "role": "EMPLOYEE",
        },
    )
    login_resp = client.post(
        "/auth/login",
        json={"email": email, "password": "testpassword123"},
    )
    token = login_resp.json()["access_token"]

    resp = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == email


def test_create_ticket():
    email = "autotest_ticket@company.com"
    client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Ticket Tester",
            "password": "testpassword123",
            "role": "EMPLOYEE",
        },
    )
    token = client.post(
        "/auth/login",
        json={"email": email, "password": "testpassword123"},
    ).json()["access_token"]

    resp = client.post(
        "/tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Monitor flickering",
            "description": "Screen blinks every few seconds",
            "category": "HARDWARE",
            "priority": "HIGH",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Monitor flickering"
    assert resp.json()["status"] == "OPEN"


def test_create_ticket_blank_title_rejected():
    email = "autotest_blank@company.com"
    client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Blank Tester",
            "password": "testpassword123",
            "role": "EMPLOYEE",
        },
    )
    token = client.post(
        "/auth/login",
        json={"email": email, "password": "testpassword123"},
    ).json()["access_token"]

    resp = client.post(
        "/tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "   ",
            "description": "Valid description",
            "category": "HARDWARE",
        },
    )
    assert resp.status_code == 422


def test_invalid_status_transition():
    admin_email = "autotest_admin@company.com"
    client.post(
        "/auth/register",
        json={
            "email": admin_email,
            "full_name": "Admin Tester",
            "password": "testpassword123",
            "role": "ADMIN",
        },
    )
    token = client.post(
        "/auth/login",
        json={"email": admin_email, "password": "testpassword123"},
    ).json()["access_token"]

    ticket_resp = client.post(
        "/tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Transition Test",
            "description": "Testing invalid jump",
            "category": "SOFTWARE",
        },
    )
    ticket_id = ticket_resp.json()["id"]

    # Try skipping OPEN -> RESOLVED (Illegal, must go to IN_PROGRESS first)
    bad_transition = client.patch(
        f"/tickets/{ticket_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "RESOLVED"},
    )
    assert bad_transition.status_code == 400


def test_cannot_move_to_in_progress_without_agent():
    admin_email = "autotest_noagent@company.com"
    client.post(
        "/auth/register",
        json={
            "email": admin_email,
            "full_name": "No Agent Admin",
            "password": "testpassword123",
            "role": "ADMIN",
        },
    )
    token = client.post(
        "/auth/login",
        json={"email": admin_email, "password": "testpassword123"},
    ).json()["access_token"]

    ticket_resp = client.post(
        "/tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "No Agent Ticket",
            "description": "Ticket without assignee",
            "category": "NETWORK",
        },
    )
    ticket_id = ticket_resp.json()["id"]

    # Try moving to IN_PROGRESS without assigning an agent first
    resp = client.patch(
        f"/tickets/{ticket_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "IN_PROGRESS"},
    )
    assert resp.status_code == 400
    assert "without an assigned agent" in resp.json()["detail"]


def test_dashboard_summary():
    admin_email = "autotest_dash@company.com"
    client.post(
        "/auth/register",
        json={
            "email": admin_email,
            "full_name": "Dash Admin",
            "password": "testpassword123",
            "role": "ADMIN",
        },
    )
    token = client.post(
        "/auth/login",
        json={"email": admin_email, "password": "testpassword123"},
    ).json()["access_token"]

    resp = client.get(
        "/dashboard/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tickets" in data
    assert "by_status" in data
    assert "by_priority" in data
