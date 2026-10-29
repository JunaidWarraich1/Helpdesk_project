# Helpdesk Ticket Management System API

A RESTful API built with FastAPI, SQLAlchemy ORM, Pydantic v2, and PostgreSQL that facilitates IT helpdesk operations across Employees, Support Agents, and Administrators.

## Tech Stack
- Framework: FastAPI (Python 3.11+)
- Database: PostgreSQL with SQLAlchemy ORM
- Authentication: JWT (JSON Web Tokens) with python-jose
- Security: Password hashing via bcrypt
- Validation: Pydantic v2
- Server: Uvicorn ASGI

## Features
- User Authentication & RBAC: Register, Login, JWT auth, and Role-Based Access Control (EMPLOYEE, AGENT, ADMIN).
- Ticket Lifecycle Engine: State machine transitions (OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED).
- Assignment Guard: Enforces that tickets cannot move to IN_PROGRESS without an assigned Agent, and only Admins can assign tickets.
- Closed Ticket Immutability: Closed tickets are strictly read-only.
- Advanced Querying: Title keyword search (case-insensitive ilike), multi-field filtering (status, priority, category, assignee), and bounded pagination (limit, offset).
- Analytics Dashboard: Real-time aggregated ticket counts by status, priority, and personal queue.

## Setup & Installation

### 1. Set Up Virtual Environment & Dependencies
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Database
In `database.py`, configure your PostgreSQL connection string:
```python
DATABASE_URL = "postgresql+psycopg2://postgres:your_password@localhost:5432/helpdesk_db"
```
Create the database in PostgreSQL / pgAdmin:
```sql
CREATE DATABASE helpdesk_db;
```

### 3. Run the API
```bash
python -m uvicorn main:app --reload
```
- Interactive Swagger UI: http://127.0.0.1:8000/docs
- Interactive ReDoc: http://127.0.0.1:8000/redoc

## API Endpoints Reference

| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | /auth/register | Register new user | Public |
| POST | /auth/login | Login and receive Bearer JWT | Public |
| GET | /users/me | Fetch authenticated user profile | Authenticated |
| POST | /tickets | Create a new ticket | Authenticated |
| GET | /tickets | List tickets (search, filter, paginate) | Role-filtered |
| GET | /tickets/{id} | Get ticket details | Authorized user |
| PATCH | /tickets/{id} | Update ticket details | Creator / Agent / Admin |
| DELETE | /tickets/{id} | Delete ticket | Creator / Admin |
| PATCH | /tickets/{id}/assign | Assign ticket to an agent | Admin only |
| PATCH | /tickets/{id}/status | Update workflow status | Agent / Admin |
| GET | /dashboard/summary | Get aggregated ticket metrics | Authenticated |

## Sample Requests

### Register User
```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "employee@test.com", "full_name": "Test Employee", "password": "password123", "role": "EMPLOYEE"}'
```

### Login
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "employee@test.com", "password": "password123"}'
```

### Create Ticket
```bash
curl -X POST http://127.0.0.1:8000/tickets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"title": "VPN connection failing", "description": "Unable to connect to internal company network", "category": "NETWORK", "priority": "HIGH"}'
```

### Assign Ticket (Admin only)
```bash
curl -X PATCH http://127.0.0.1:8000/tickets/1/assign \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"agent_id": 2}'
```

### Update Status (Agent/Admin)
```bash
curl -X PATCH http://127.0.0.1:8000/tickets/1/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <AGENT_TOKEN>" \
  -d '{"status": "IN_PROGRESS"}'
```

### Dashboard Summary
```bash
curl -X GET http://127.0.0.1:8000/dashboard/summary \
  -H "Authorization: Bearer <TOKEN>"
```

## Running Automated Tests
```bash
pytest test_app.py -v
```
