# Helpdesk Ticket Management System API

A modular, production-grade RESTful API built with **FastAPI**, **SQLAlchemy 2**, **Pydantic v2**, and **PostgreSQL** that facilitates IT helpdesk operations across Employees, Support Agents, and Administrators.

---

## Architecture Overview

Built using Domain-Driven Modular Architecture:
```
backend/
├── app/
│   ├── main.py                  # App factory, lifespan, and router mounting
│   ├── core/
│   │   ├── config.py            # pydantic-settings configuration (.env)
│   │   └── security.py          # bcrypt password hashing & JWT tokens
│   ├── db/
│   │   ├── session.py           # Engine, connection pooling, and get_db dependency
│   │   └── base.py              # DeclarativeBase and metadata
│   ├── models/
│   │   ├── user.py              # User model and UserRole enum
│   │   └── ticket.py            # Ticket model and status/priority/category enums
│   ├── schemas/
│   │   ├── user.py              # User schemas (hardened UserCreate, UserRoleUpdate)
│   │   ├── ticket.py            # Ticket schemas (TicketCreate, strict TicketUpdate)
│   │   └── dashboard.py         # Role-scoped DashboardSummary
│   ├── api/
│   │   ├── deps.py              # HTTPBearer, get_current_user, require_role
│   │   └── v1/
│   │       ├── router.py        # Centralized v1 router
│   │       └── endpoints/
│   │           ├── auth.py      # /auth/register, /auth/login
│   │           ├── users.py     # /users/me, PATCH /users/{id}/role
│   │           ├── tickets.py   # Full ticket CRUD, /assign, /status
│   │           └── dashboard.py # /dashboard/summary
│   └── services/
│       ├── user_service.py      # User business logic
│       └── ticket_service.py    # Ticket state machine and workflow logic
├── tests/
│   ├── conftest.py              # TestClient with isolated in-memory test DB
│   └── test_api.py              # Comprehensive integration and security test suite
├── seed_admin.py                # CLI command to seed the initial admin account
├── requirements.txt             # Pinned production dependencies
├── .env.example                 # Environment configuration template
└── .gitignore                   # Excludes .env, caches, and test artifacts
```

---

## Security & Workflow Guardrails

- **Zero Privilege Escalation**: Public registration strictly forces the `EMPLOYEE` role. Role updates are restricted to Admins via `PATCH /users/{id}/role`.
- **Assignment Guard**: Ticket creation does not accept assignees. Only Admins can assign tickets to verified `AGENT` users via `PATCH /tickets/{id}/assign`.
- **Enforced State Workflow**: `OPEN` → `IN_PROGRESS` → `RESOLVED` → `CLOSED`. Moving to `IN_PROGRESS` strictly requires an assigned agent.
- **Closed Ticket Immutability**: Closed tickets cannot be edited, assigned, transitioned, or deleted (returns `400 Bad Request`).
- **Input Validation & 500 Immunity**:
  - Filter parameters (`status`, `priority`, `category`) use strict Enum types returning `422 Unprocessable Entity` for invalid values.
  - SQL wildcards (`%`, `_`, `\`) in search are sanitized to prevent pattern injection.
  - Ticket updates strictly reject `null` and blank whitespace strings with `422`.
  - Passwords enforce a 72-byte ceiling to prevent bcrypt truncation vulnerabilities.
- **Role-Scoped Dashboard**: Employees view only their created tickets, Agents view their assigned tickets, and Admins view enterprise-wide metrics.
- **Isolated Testing**: Automated tests run against an in-memory SQLite database via `dependency_overrides`, leaving zero trace in production databases.

---

## Setup & Installation

### 1. Set Up Virtual Environment & Dependencies
```bash
python -m venv venv

# Windows (Command Prompt / PowerShell)
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Configure your PostgreSQL connection and JWT secret in `.env`:
```env
DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/helpdesk_db
SECRET_KEY=generate-a-secure-32-byte-hex-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```
Create the database in PostgreSQL / pgAdmin:
```sql
CREATE DATABASE helpdesk_db;
```

### 3. Seed the Initial Administrator
Run the included CLI command to initialize an admin account:
```bash
python seed_admin.py --email admin@company.com --password AdminPass123! --name "System Administrator"
```

### 4. Run the API Server
```bash
python -m uvicorn app.main:app --reload
```
- Interactive Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Interactive ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## API Endpoints Reference

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `POST` | `/auth/register` | Register new employee account | Public |
| `POST` | `/auth/login` | Authenticate and obtain JWT token | Public |
| `GET` | `/users/me` | Retrieve authenticated user profile | Authenticated |
| `PATCH` | `/users/{id}/role` | Promote or change a user's role | Admin only |
| `POST` | `/tickets` | Create a new ticket (status: OPEN) | Authenticated |
| `GET` | `/tickets` | List tickets with filters and pagination | Role-filtered |
| `GET` | `/tickets/{id}` | Retrieve ticket details | Authorized user |
| `PATCH` | `/tickets/{id}` | Update ticket details | Creator / Agent / Admin |
| `DELETE` | `/tickets/{id}` | Delete ticket (closed tickets blocked) | Creator / Admin |
| `PATCH` | `/tickets/{id}/assign` | Assign ticket to an Agent | Admin only |
| `PATCH` | `/tickets/{id}/status` | Advance status through workflow | Agent / Admin |
| `GET` | `/dashboard/summary` | Get aggregated ticket metrics | Role-scoped |

---

## Sample Requests

### Register User (Always Employee)
```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "employee@test.com", "full_name": "Test Employee", "password": "password123"}'
```

### Login
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "employee@test.com", "password": "password123"}'
```

### Promote User to Agent (Admin Only)
```bash
curl -X PATCH http://127.0.0.1:8000/users/2/role \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"role": "AGENT"}'
```

### Create Ticket
```bash
curl -X POST http://127.0.0.1:8000/tickets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"title": "VPN connection failing", "description": "Unable to connect to internal company network", "category": "NETWORK", "priority": "HIGH"}'
```

### Assign Ticket (Admin Only)
```bash
curl -X PATCH http://127.0.0.1:8000/tickets/1/assign \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"agent_id": 2}'
```

### Advance Ticket Status (Agent / Admin)
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

---

## Running Automated Tests
The test suite utilizes an in-memory test database fixture:
```bash
python -m pytest tests/ -v
```
All 14 comprehensive tests execute in under 15 seconds with 100% pass rate.
