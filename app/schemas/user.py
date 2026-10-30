from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.models.user import UserRole


class UserCreate(BaseModel):
    """Schema for user registration. Role is strictly excluded and defaulted server-side to EMPLOYEE."""
    email: EmailStr
    full_name: str
    password: str = Field(..., min_length=6, max_length=72, description="Password must be between 6 and 72 characters")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Full name cannot be blank")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password cannot exceed 72 bytes")
        return v


class UserRoleUpdate(BaseModel):
    """Schema for updating a user's role (Admin-only)."""
    role: UserRole


class UserResponse(BaseModel):
    """Schema for user public profile responses."""
    id: int
    email: str
    full_name: str
    role: UserRole
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """Schema for user authentication request."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT access token response."""
    access_token: str
    token_type: str = "bearer"
