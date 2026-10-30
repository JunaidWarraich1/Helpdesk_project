from typing import Optional
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    """Schema for role-scoped dashboard metrics summary."""
    total_tickets: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    assigned_to_me: Optional[int] = None
