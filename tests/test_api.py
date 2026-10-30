import pytest
from app.core.config import settings
from app.models.ticket import Ticket, TicketCategory, TicketPriority, TicketStatus
from app.models.user import UserRole


# -----------------------------------------------------------------------------
# User Registration and Role Escalation Prevention
# -----------------------------------------------------------------------------
def test_registration_forces_employee_role(client):
    """Verify that user registration does not allow role escalation and always assigns EMPLOYEE."""
    # Attempt to inject ADMIN role in payload
    resp = client.post(
        "/auth/register",
        json={
            "email": "infiltrator@company.com",
            "full_name": "Infiltrator Admin",
            "password": "securepassword123",
            "role": "ADMIN",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "infiltrator@company.com"
    # Must be EMPLOYEE, ignoring/overriding injected ADMIN role
    assert data["role"] == "EMPLOYEE"


# -----------------------------------------------------------------------------
# Role Management (Admin-Guarded Endpoint)
# -----------------------------------------------------------------------------
def test_update_user_role_admin_only(
    client, employee_user, employee_headers, agent_headers, admin_headers
):
    """Verify that updating a user's role is strictly restricted to administrators."""
    target_id = employee_user.id

    # 1. Employee attempt -> 403 Forbidden
    resp_emp = client.patch(
        f"/users/{target_id}/role",
        headers=employee_headers,
        json={"role": "AGENT"},
    )
    assert resp_emp.status_code == 403

    # 2. Agent attempt -> 403 Forbidden
    resp_agent = client.patch(
        f"/users/{target_id}/role",
        headers=agent_headers,
        json={"role": "ADMIN"},
    )
    assert resp_agent.status_code == 403

    # 3. Unauthenticated attempt -> 401 Unauthorized
    resp_unauth = client.patch(
        f"/users/{target_id}/role",
        json={"role": "ADMIN"},
    )
    assert resp_unauth.status_code == 401

    # 4. Admin attempt -> 200 OK, role updated to AGENT
    resp_admin = client.patch(
        f"/users/{target_id}/role",
        headers=admin_headers,
        json={"role": "AGENT"},
    )
    assert resp_admin.status_code == 200
    assert resp_admin.json()["role"] == "AGENT"

    # 5. Admin updating non-existent user -> 404 Not Found
    resp_404 = client.patch(
        "/users/999999/role",
        headers=admin_headers,
        json={"role": "ADMIN"},
    )
    assert resp_404.status_code == 404


# -----------------------------------------------------------------------------
# Ticket Creation and Assignment Decoupling
# -----------------------------------------------------------------------------
def test_ticket_create_ignores_assigned_to(
    client, employee_headers, agent_user
):
    """Verify that users cannot self-assign tickets during ticket creation."""
    resp = client.post(
        "/tickets",
        headers=employee_headers,
        json={
            "title": "Printer broken",
            "description": "Paper jam on the 2nd floor printer",
            "category": "HARDWARE",
            "priority": "HIGH",
            "assigned_to": agent_user.id,  # Injected field
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Printer broken"
    assert data["assigned_to"] is None


# -----------------------------------------------------------------------------
# Configuration and Environment Settings
# -----------------------------------------------------------------------------
def test_pydantic_settings_configuration():
    """Verify that application settings are powered by pydantic-settings."""
    from pydantic_settings import BaseSettings
    from app.core.config import Settings

    assert issubclass(Settings, BaseSettings)
    assert hasattr(settings, "SECRET_KEY")
    assert hasattr(settings, "ALGORITHM")
    assert hasattr(settings, "DATABASE_URL")
    assert hasattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES")
    assert len(settings.SECRET_KEY) > 0


# -----------------------------------------------------------------------------
# Query Filtering and Enum Input Validation
# -----------------------------------------------------------------------------
def test_typed_enum_query_params_validation(client, employee_headers):
    """Verify that GET /tickets validates enum query parameters with HTTP 422."""
    # Invalid status
    resp_status = client.get(
        "/tickets?status=BOGUS_STATUS",
        headers=employee_headers,
    )
    assert resp_status.status_code == 422

    # Invalid priority
    resp_priority = client.get(
        "/tickets?priority=SUPER_URGENT",
        headers=employee_headers,
    )
    assert resp_priority.status_code == 422

    # Invalid category
    resp_category = client.get(
        "/tickets?category=CYBER_WARFARE",
        headers=employee_headers,
    )
    assert resp_category.status_code == 422

    # Valid enums return 200
    resp_valid = client.get(
        "/tickets?status=OPEN&priority=HIGH&category=HARDWARE",
        headers=employee_headers,
    )
    assert resp_valid.status_code == 200
    assert "tickets" in resp_valid.json()


def test_search_query_escaping(client, employee_headers):
    """Verify that search query handles SQL LIKE wildcards (%) without syntax errors."""
    resp = client.get(
        "/tickets?search=100%25_discount",
        headers=employee_headers,
    )
    assert resp.status_code == 200


# -----------------------------------------------------------------------------
# Ticket Partial Updates and Payload Validation
# -----------------------------------------------------------------------------
def test_ticket_update_rejects_nulls_and_blanks(client, employee_headers):
    """Verify TicketUpdate rejects null values and blank strings with 422."""
    # Create a ticket first
    create_resp = client.post(
        "/tickets",
        headers=employee_headers,
        json={
            "title": "Email server sync lag",
            "description": "Incoming emails delayed by 15 minutes",
            "category": "NETWORK",
            "priority": "MEDIUM",
        },
    )
    ticket_id = create_resp.json()["id"]

    # 1. Null title -> 422
    resp_null_title = client.patch(
        f"/tickets/{ticket_id}",
        headers=employee_headers,
        json={"title": None},
    )
    assert resp_null_title.status_code == 422

    # 2. Blank title -> 422
    resp_blank_title = client.patch(
        f"/tickets/{ticket_id}",
        headers=employee_headers,
        json={"title": "     "},
    )
    assert resp_blank_title.status_code == 422

    # 3. Null description -> 422
    resp_null_desc = client.patch(
        f"/tickets/{ticket_id}",
        headers=employee_headers,
        json={"description": None},
    )
    assert resp_null_desc.status_code == 422

    # 4. Blank description -> 422
    resp_blank_desc = client.patch(
        f"/tickets/{ticket_id}",
        headers=employee_headers,
        json={"description": "     "},
    )
    assert resp_blank_desc.status_code == 422

    # 5. Null category -> 422
    resp_null_cat = client.patch(
        f"/tickets/{ticket_id}",
        headers=employee_headers,
        json={"category": None},
    )
    assert resp_null_cat.status_code == 422

    # 6. Null priority -> 422
    resp_null_pri = client.patch(
        f"/tickets/{ticket_id}",
        headers=employee_headers,
        json={"priority": None},
    )
    assert resp_null_pri.status_code == 422

    # 7. Valid update -> 200 OK
    resp_valid = client.patch(
        f"/tickets/{ticket_id}",
        headers=employee_headers,
        json={"title": "Updated Valid Title"},
    )
    assert resp_valid.status_code == 200
    assert resp_valid.json()["title"] == "Updated Valid Title"


# -----------------------------------------------------------------------------
# Password Validation and Length Constraints
# -----------------------------------------------------------------------------
def test_password_length_limits(client):
    """Verify password max length is 72 characters (bcrypt limit) and min is 6."""
    # 73 characters -> 422
    resp_too_long = client.post(
        "/auth/register",
        json={
            "email": "toolong@company.com",
            "full_name": "Long Tester",
            "password": "A" * 73,
        },
    )
    assert resp_too_long.status_code == 422

    # Exactly 72 characters -> 201 Created
    resp_exact_72 = client.post(
        "/auth/register",
        json={
            "email": "exact72@company.com",
            "full_name": "Exact Tester",
            "password": "A" * 72,
        },
    )
    assert resp_exact_72.status_code == 201

    # Less than 6 characters -> 422
    resp_too_short = client.post(
        "/auth/register",
        json={
            "email": "short@company.com",
            "full_name": "Short Tester",
            "password": "12345",
        },
    )
    assert resp_too_short.status_code == 422


# -----------------------------------------------------------------------------
# Role-Scoped Metrics and Aggregations
# -----------------------------------------------------------------------------
def test_role_scoped_dashboard_summary(
    client, db_session, employee_user, employee_headers, agent_user, agent_headers, admin_headers
):
    """Verify /dashboard/summary returns metrics strictly scoped to user role."""
    # Create tickets directly in db for test setup
    # Ticket 1: created by employee_user, assigned to agent_user
    t1 = Ticket(
        title="T1",
        description="D1",
        category=TicketCategory.HARDWARE,
        priority=TicketPriority.HIGH,
        status=TicketStatus.OPEN,
        created_by=employee_user.id,
        assigned_to=agent_user.id,
    )
    # Ticket 2: created by employee_user, unassigned
    t2 = Ticket(
        title="T2",
        description="D2",
        category=TicketCategory.SOFTWARE,
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        created_by=employee_user.id,
        assigned_to=None,
    )
    # Ticket 3: created by another employee (represented here by agent_user for simplicity), assigned to None
    t3 = Ticket(
        title="T3",
        description="D3",
        category=TicketCategory.NETWORK,
        priority=TicketPriority.LOW,
        status=TicketStatus.RESOLVED,
        created_by=agent_user.id,
        assigned_to=None,
    )
    db_session.add_all([t1, t2, t3])
    db_session.commit()

    # 1. Employee view: sees only tickets they created (t1 and t2 = 2 tickets)
    resp_emp = client.get("/dashboard/summary", headers=employee_headers)
    assert resp_emp.status_code == 200
    data_emp = resp_emp.json()
    assert data_emp["total_tickets"] == 2
    assert data_emp["by_status"]["OPEN"] == 2
    assert data_emp["by_status"]["RESOLVED"] == 0
    assert data_emp["assigned_to_me"] is None

    # 2. Agent view: sees only tickets assigned to them (t1 = 1 ticket)
    resp_agent = client.get("/dashboard/summary", headers=agent_headers)
    assert resp_agent.status_code == 200
    data_agent = resp_agent.json()
    assert data_agent["total_tickets"] == 1
    assert data_agent["assigned_to_me"] == 1

    # 3. Admin view: sees global tickets (t1, t2, t3 = 3 tickets)
    resp_admin = client.get("/dashboard/summary", headers=admin_headers)
    assert resp_admin.status_code == 200
    data_admin = resp_admin.json()
    assert data_admin["total_tickets"] == 3
    assert data_admin["by_status"]["OPEN"] == 2
    assert data_admin["by_status"]["RESOLVED"] == 1


# -----------------------------------------------------------------------------
# Ticket Deletion Guardrails
# -----------------------------------------------------------------------------
def test_closed_tickets_cannot_be_deleted(
    client, db_session, employee_user, employee_headers, admin_headers
):
    """Verify that attempting to delete a CLOSED ticket returns HTTP 400."""
    # Create ticket in CLOSED state directly
    closed_ticket = Ticket(
        title="Closed Archive Ticket",
        description="Historical log ticket",
        category=TicketCategory.OTHER,
        priority=TicketPriority.LOW,
        status=TicketStatus.CLOSED,
        created_by=employee_user.id,
    )
    db_session.add(closed_ticket)
    db_session.commit()
    db_session.refresh(closed_ticket)

    # 1. Employee creator attempts to delete -> 400 Bad Request
    resp_emp_del = client.delete(
        f"/tickets/{closed_ticket.id}",
        headers=employee_headers,
    )
    assert resp_emp_del.status_code == 400
    assert "Closed tickets cannot be deleted" in resp_emp_del.json()["detail"]

    # 2. Admin attempts to delete -> 400 Bad Request
    resp_admin_del = client.delete(
        f"/tickets/{closed_ticket.id}",
        headers=admin_headers,
    )
    assert resp_admin_del.status_code == 400
    assert "Closed tickets cannot be deleted" in resp_admin_del.json()["detail"]

    # 3. Create an OPEN ticket and delete it successfully -> 204 No Content
    open_ticket = Ticket(
        title="Open Deletable Ticket",
        description="Temporary ticket",
        category=TicketCategory.HARDWARE,
        priority=TicketPriority.LOW,
        status=TicketStatus.OPEN,
        created_by=employee_user.id,
    )
    db_session.add(open_ticket)
    db_session.commit()
    db_session.refresh(open_ticket)

    resp_valid_del = client.delete(
        f"/tickets/{open_ticket.id}",
        headers=employee_headers,
    )
    assert resp_valid_del.status_code == 204


# -----------------------------------------------------------------------------
# Ticket Lifecycle State Machine and Access Permissions
# -----------------------------------------------------------------------------
def test_state_machine_workflow_and_guardrails(
    client, employee_headers, agent_user, agent_headers, admin_headers
):
    """Test full ticket lifecycle: OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED."""
    # 1. Employee creates ticket
    t_resp = client.post(
        "/tickets",
        headers=employee_headers,
        json={
            "title": "VPN Disconnecting",
            "description": "VPN disconnects every 10 minutes",
            "category": "NETWORK",
            "priority": "HIGH",
        },
    )
    ticket_id = t_resp.json()["id"]

    # 2. Attempt transition to IN_PROGRESS without assigned agent -> 400 Bad Request
    bad_progress = client.patch(
        f"/tickets/{ticket_id}/status",
        headers=admin_headers,
        json={"status": "IN_PROGRESS"},
    )
    assert bad_progress.status_code == 400
    assert "without an assigned agent" in bad_progress.json()["detail"]

    # 3. Admin assigns ticket to agent
    assign_resp = client.patch(
        f"/tickets/{ticket_id}/assign",
        headers=admin_headers,
        json={"agent_id": agent_user.id},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["assigned_to"] == agent_user.id

    # 4. Agent advances to IN_PROGRESS
    prog_resp = client.patch(
        f"/tickets/{ticket_id}/status",
        headers=agent_headers,
        json={"status": "IN_PROGRESS"},
    )
    assert prog_resp.status_code == 200
    assert prog_resp.json()["status"] == "IN_PROGRESS"

    # 5. Invalid transition jump: IN_PROGRESS directly to CLOSED -> 400 Bad Request
    invalid_jump = client.patch(
        f"/tickets/{ticket_id}/status",
        headers=agent_headers,
        json={"status": "CLOSED"},
    )
    assert invalid_jump.status_code == 400

    # 6. Agent advances to RESOLVED
    res_resp = client.patch(
        f"/tickets/{ticket_id}/status",
        headers=agent_headers,
        json={"status": "RESOLVED"},
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "RESOLVED"

    # 7. Agent advances to CLOSED
    close_resp = client.patch(
        f"/tickets/{ticket_id}/status",
        headers=agent_headers,
        json={"status": "CLOSED"},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "CLOSED"

    # 8. Attempt updating a closed ticket -> 400 Bad Request
    update_closed = client.patch(
        f"/tickets/{ticket_id}",
        headers=agent_headers,
        json={"title": "Change Title After Close"},
    )
    assert update_closed.status_code == 400

    # 9. Attempt assigning a closed ticket -> 400 Bad Request
    assign_closed = client.patch(
        f"/tickets/{ticket_id}/assign",
        headers=admin_headers,
        json={"agent_id": agent_user.id},
    )
    assert assign_closed.status_code == 400


def test_auth_and_profile_flow(client):
    """Test full registration, login, and get profile flow."""
    email = "integration_test@company.com"
    reg = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Integration User",
            "password": "validpassword123",
        },
    )
    assert reg.status_code == 201

    # Login
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "validpassword123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    # Profile
    profile = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["email"] == email


def test_invalid_login_credentials(client):
    """Test 401 error on invalid credentials."""
    resp = client.post(
        "/auth/login",
        json={"email": "nonexistent@company.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_duplicate_email_registration(client):
    """Test 400 error on registering an already registered email."""
    client.post(
        "/auth/register",
        json={
            "email": "duplicate@company.com",
            "full_name": "Original User",
            "password": "validpassword123",
        },
    )
    dup = client.post(
        "/auth/register",
        json={
            "email": "duplicate@company.com",
            "full_name": "Copycat User",
            "password": "validpassword123",
        },
    )
    assert dup.status_code == 400
