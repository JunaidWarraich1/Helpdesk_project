from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator
from app.models.ticket import TicketCategory, TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    """Schema for ticket creation. assigned_to is strictly omitted and controlled by admins."""
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority = TicketPriority.MEDIUM

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
    """Schema for updating ticket fields with strict rejection of nulls and blank strings."""
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[TicketCategory] = None
    priority: Optional[TicketPriority] = None

    @field_validator("title", "description", mode="before")
    @classmethod
    def validate_text_fields(cls, v: Any, info: ValidationInfo) -> Any:
        if v is None:
            raise ValueError(f"{info.field_name} cannot be null")
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError(f"{info.field_name} cannot be blank")
            return v_stripped
        return v

    @field_validator("category", "priority", mode="before")
    @classmethod
    def validate_enum_fields(cls, v: Any, info: ValidationInfo) -> Any:
        if v is None:
            raise ValueError(f"{info.field_name} cannot be null")
        return v


class TicketAssign(BaseModel):
    """Schema for assigning ticket to an agent."""
    agent_id: int


class TicketStatusUpdate(BaseModel):
    """Schema for updating ticket status via state machine."""
    status: TicketStatus


class TicketResponse(BaseModel):
    """Schema for ticket response details."""
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
    """Schema for paginated ticket list response."""
    tickets: list[TicketResponse]
    total: int
    limit: int
    offset: int
