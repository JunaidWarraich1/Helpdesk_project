import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # Ensures all models are registered on Base.metadata
from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.main import app
from app.models.user import User, UserRole

# Isolated SQLite in-memory test database with StaticPool
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine
)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create fresh database tables before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(setup_test_db):
    """Provide an isolated database session for direct inspection in tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(setup_test_db):
    """FastAPI TestClient with isolated test database dependency override."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_test_user(
    db, email: str, role: UserRole, full_name: str, password: str = "testpassword123"
) -> User:
    """Helper to seed test users directly into the isolated database."""
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def employee_user(db_session):
    return create_test_user(
        db_session, "emp@company.com", UserRole.EMPLOYEE, "Employee Tester"
    )


@pytest.fixture
def agent_user(db_session):
    return create_test_user(
        db_session, "agent@company.com", UserRole.AGENT, "Agent Tester"
    )


@pytest.fixture
def admin_user(db_session):
    return create_test_user(
        db_session, "admin@company.com", UserRole.ADMIN, "Admin Tester"
    )


@pytest.fixture
def employee_headers(employee_user):
    token = create_access_token(data={"sub": str(employee_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def agent_headers(agent_user):
    token = create_access_token(data={"sub": str(agent_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token(data={"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}
