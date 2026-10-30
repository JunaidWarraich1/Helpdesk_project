from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserLogin


def create_user(db: Session, user_in: UserCreate) -> User:
    """Register a new user. Role is unconditionally set to EMPLOYEE."""
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    hashed_pwd = hash_password(user_in.password)
    new_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hashed_pwd,
        role=UserRole.EMPLOYEE,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def authenticate_user(db: Session, login_data: UserLogin) -> User:
    """Verify credentials and return matching user or raise 401."""
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return user


def get_user_by_id(db: Session, user_id: int) -> User:
    """Retrieve user by ID or raise 404."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def update_user_role(db: Session, user_id: int, new_role: UserRole) -> User:
    """Update role for a specified user (Admin action)."""
    user = get_user_by_id(db, user_id)
    user.role = new_role
    db.commit()
    db.refresh(user)
    return user
