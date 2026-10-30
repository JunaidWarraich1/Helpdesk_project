from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.core.security import create_access_token
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers an employee user. Roles cannot be escalated during registration.",
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register user with role forced to EMPLOYEE."""
    return user_service.create_user(db=db, user_in=user_data)


@router.post(
    "/login",
    response_model=Token,
    summary="User login",
    description="Authenticate with email and password to receive a bearer JWT token.",
)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate credentials and generate JWT."""
    user = user_service.authenticate_user(db=db, login_data=login_data)
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")
