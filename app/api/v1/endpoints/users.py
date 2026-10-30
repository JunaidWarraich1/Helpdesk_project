from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db, require_role
from app.models.user import User, UserRole
from app.schemas.user import UserResponse, UserRoleUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return profile of the authenticated user."""
    return current_user


@router.patch(
    "/{id}/role",
    response_model=UserResponse,
    summary="Update user role (Admin only)",
    description="Allows administrators to change a user's role to EMPLOYEE, AGENT, or ADMIN.",
)
def update_user_role(
    id: int,
    role_data: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Update role for specified user ID (strictly restricted to administrators)."""
    return user_service.update_user_role(db=db, user_id=id, new_role=role_data.role)
