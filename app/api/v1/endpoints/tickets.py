from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.ticket import TicketCategory, TicketPriority, TicketStatus
from app.models.user import User
from app.schemas.ticket import (
    TicketAssign,
    TicketCreate,
    TicketListResponse,
    TicketResponse,
    TicketStatusUpdate,
    TicketUpdate,
)
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ticket",
)
def create_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new ticket with status OPEN and assigned_to None."""
    return ticket_service.create_ticket(
        db=db, ticket_in=ticket_data, user_id=current_user.id
    )


@router.get(
    "",
    response_model=TicketListResponse,
    summary="List tickets",
    description="List tickets with typed enum filters, escaping, and role-based scoping.",
)
def list_tickets(
    status: Optional[TicketStatus] = Query(None, description="Filter by status enum"),
    priority: Optional[TicketPriority] = Query(None, description="Filter by priority enum"),
    category: Optional[TicketCategory] = Query(None, description="Filter by category enum"),
    assigned_to: Optional[int] = Query(None, description="Filter by assigned user ID"),
    search: Optional[str] = Query(None, description="Search substring in ticket title"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List tickets with strict enum typing (returns 422 if invalid enum supplied)."""
    tickets, total = ticket_service.list_tickets(
        db=db,
        current_user=current_user,
        status_filter=status,
        priority_filter=priority,
        category_filter=category,
        assigned_to=assigned_to,
        search=search,
        limit=limit,
        offset=offset,
    )
    return TicketListResponse(
        tickets=tickets, total=total, limit=limit, offset=offset
    )


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Get ticket details",
)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve ticket details with role verification."""
    return ticket_service.get_ticket(
        db=db, ticket_id=ticket_id, current_user=current_user
    )


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Update ticket",
)
def update_ticket(
    ticket_id: int,
    update_data: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update ticket fields. Rejects nulls, blank strings, or edits to closed tickets."""
    return ticket_service.update_ticket(
        db=db,
        ticket_id=ticket_id,
        update_in=update_data,
        current_user=current_user,
    )


@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete ticket",
)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete ticket. Fails with 400 if ticket is closed."""
    ticket_service.delete_ticket(
        db=db, ticket_id=ticket_id, current_user=current_user
    )


@router.patch(
    "/{ticket_id}/assign",
    response_model=TicketResponse,
    summary="Assign ticket to agent (Admin only)",
)
def assign_ticket(
    ticket_id: int,
    assign_data: TicketAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign ticket to an agent user (Admin action)."""
    return ticket_service.assign_ticket(
        db=db,
        ticket_id=ticket_id,
        assign_in=assign_data,
        current_user=current_user,
    )


@router.patch(
    "/{ticket_id}/status",
    response_model=TicketResponse,
    summary="Update ticket status",
)
def update_ticket_status(
    ticket_id: int,
    status_data: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Advance ticket through allowed lifecycle state transitions."""
    return ticket_service.update_ticket_status(
        db=db,
        ticket_id=ticket_id,
        status_in=status_data,
        current_user=current_user,
    )
