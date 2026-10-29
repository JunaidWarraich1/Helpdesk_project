from datetime import datetime
from typing import Optional
from models import UserRole, TicketCategory, TicketPriority, TicketStatus
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.EMPLOYEE

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
        return v


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TicketCreate(BaseModel):
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority = TicketPriority.MEDIUM
    assigned_to: Optional[int] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title is required and cannot be blank")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description is required and cannot be blank")
        return v


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[TicketCategory] = None
    priority: Optional[TicketPriority] = None


class TicketAssign(BaseModel):
    agent_id: int


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    created_by: int
    assigned_to: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]
    total: int
    limit: int
    offset: int


class DashboardSummary(BaseModel):
    total_tickets: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    assigned_to_me: Optional[int] = None
