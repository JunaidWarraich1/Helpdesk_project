from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.ticket import (
    Ticket,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from app.models.user import User, UserRole
from app.schemas.ticket import (
    TicketAssign,
    TicketCreate,
    TicketStatusUpdate,
    TicketUpdate,
)
from app.schemas.dashboard import DashboardSummary

ALLOWED_TRANSITIONS: dict[TicketStatus, list[TicketStatus]] = {
    TicketStatus.OPEN: [TicketStatus.IN_PROGRESS],
    TicketStatus.IN_PROGRESS: [TicketStatus.RESOLVED],
    TicketStatus.RESOLVED: [TicketStatus.CLOSED],
    TicketStatus.CLOSED: [],
}


def create_ticket(db: Session, ticket_in: TicketCreate, user_id: int) -> Ticket:
    """Create a new ticket. Creator is current user, assigned_to is strictly None on creation."""
    new_ticket = Ticket(
        title=ticket_in.title,
        description=ticket_in.description,
        category=ticket_in.category,
        priority=ticket_in.priority,
        status=TicketStatus.OPEN,
        created_by=user_id,
        assigned_to=None,
    )
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    return new_ticket


def list_tickets(
    db: Session,
    current_user: User,
    status_filter: Optional[TicketStatus] = None,
    priority_filter: Optional[TicketPriority] = None,
    category_filter: Optional[TicketCategory] = None,
    assigned_to: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Ticket], int]:
    """List tickets with role scoping, typed enum filters, escaped search, and pagination."""
    query = db.query(Ticket)

    # Role scoping
    if current_user.role == UserRole.EMPLOYEE:
        query = query.filter(Ticket.created_by == current_user.id)
    elif current_user.role == UserRole.AGENT:
        query = query.filter(Ticket.assigned_to == current_user.id)

    # Filtering
    if status_filter is not None:
        query = query.filter(Ticket.status == status_filter)
    if priority_filter is not None:
        query = query.filter(Ticket.priority == priority_filter)
    if category_filter is not None:
        query = query.filter(Ticket.category == category_filter)
    if assigned_to is not None:
        query = query.filter(Ticket.assigned_to == assigned_to)
    if search:
        # Escape wildcard characters to prevent SQL LIKE injection
        escaped_search = (
            search.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        query = query.filter(Ticket.title.ilike(f"%{escaped_search}%", escape="\\"))

    total = query.count()
    tickets = (
        query.order_by(Ticket.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return tickets, total


def get_ticket(db: Session, ticket_id: int, current_user: User) -> Ticket:
    """Get single ticket with role-based access check."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    if current_user.role == UserRole.EMPLOYEE and ticket.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    if current_user.role == UserRole.AGENT and ticket.assigned_to != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return ticket


def update_ticket(
    db: Session, ticket_id: int, update_in: TicketUpdate, current_user: User
) -> Ticket:
    """Update ticket fields. Closed tickets cannot be updated."""
    ticket = get_ticket(db, ticket_id, current_user)

    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Closed tickets are read-only and cannot be updated",
        )

    update_data = update_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ticket, field, value)

    db.commit()
    db.refresh(ticket)
    return ticket


def delete_ticket(db: Session, ticket_id: int, current_user: User) -> None:
    """Delete a ticket. Closed tickets cannot be deleted (returns 400)."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # Closed tickets are read-only and cannot be deleted
    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Closed tickets cannot be deleted",
        )

    # Permission check: Admin or creator only
    if current_user.role != UserRole.ADMIN and ticket.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or the creator can delete this ticket",
        )

    db.delete(ticket)
    db.commit()


def assign_ticket(
    db: Session, ticket_id: int, assign_in: TicketAssign, current_user: User
) -> Ticket:
    """Assign ticket to an agent (Admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can assign tickets",
        )

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign a closed ticket",
        )

    agent = db.query(User).filter(User.id == assign_in.agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    if agent.role != UserRole.AGENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tickets can only be assigned to users with the AGENT role",
        )

    ticket.assigned_to = assign_in.agent_id
    db.commit()
    db.refresh(ticket)
    return ticket


def update_ticket_status(
    db: Session, ticket_id: int, status_in: TicketStatusUpdate, current_user: User
) -> Ticket:
    """Transition ticket status according to business state machine rules."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    if current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees cannot change ticket status",
        )

    if current_user.role == UserRole.AGENT and ticket.assigned_to != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Closed tickets are read-only",
        )

    if status_in.status not in ALLOWED_TRANSITIONS.get(ticket.status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid status transition from {ticket.status.value} to"
                f" {status_in.status.value}"
            ),
        )

    if (
        status_in.status == TicketStatus.IN_PROGRESS
        and ticket.assigned_to is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot move ticket to IN_PROGRESS without an assigned agent",
        )

    ticket.status = status_in.status
    db.commit()
    db.refresh(ticket)
    return ticket


def get_dashboard_summary(db: Session, current_user: User) -> DashboardSummary:
    """Aggregate dashboard metrics scoped by the caller's role."""
    by_status = {s.value: 0 for s in TicketStatus}
    by_priority = {p.value: 0 for p in TicketPriority}
    assigned_to_me: Optional[int] = None

    if current_user.role == UserRole.EMPLOYEE:
        # Employee only sees tickets they created
        base_query = db.query(Ticket).filter(Ticket.created_by == current_user.id)
        total = base_query.count()

        status_counts = (
            db.query(Ticket.status, func.count(Ticket.id))
            .filter(Ticket.created_by == current_user.id)
            .group_by(Ticket.status)
            .all()
        )
        for s, count in status_counts:
            val = s.value if hasattr(s, "value") else str(s)
            by_status[val] = count

        priority_counts = (
            db.query(Ticket.priority, func.count(Ticket.id))
            .filter(Ticket.created_by == current_user.id)
            .group_by(Ticket.priority)
            .all()
        )
        for p, count in priority_counts:
            val = p.value if hasattr(p, "value") else str(p)
            by_priority[val] = count

        assigned_to_me = None

    elif current_user.role == UserRole.AGENT:
        # Agent sees metrics for tickets assigned to them
        base_query = db.query(Ticket).filter(Ticket.assigned_to == current_user.id)
        total = base_query.count()

        status_counts = (
            db.query(Ticket.status, func.count(Ticket.id))
            .filter(Ticket.assigned_to == current_user.id)
            .group_by(Ticket.status)
            .all()
        )
        for s, count in status_counts:
            val = s.value if hasattr(s, "value") else str(s)
            by_status[val] = count

        priority_counts = (
            db.query(Ticket.priority, func.count(Ticket.id))
            .filter(Ticket.assigned_to == current_user.id)
            .group_by(Ticket.priority)
            .all()
        )
        for p, count in priority_counts:
            val = p.value if hasattr(p, "value") else str(p)
            by_priority[val] = count

        assigned_to_me = total

    else:
        # Admin sees global system metrics
        total = db.query(func.count(Ticket.id)).scalar() or 0

        status_counts = (
            db.query(Ticket.status, func.count(Ticket.id))
            .group_by(Ticket.status)
            .all()
        )
        for s, count in status_counts:
            val = s.value if hasattr(s, "value") else str(s)
            by_status[val] = count

        priority_counts = (
            db.query(Ticket.priority, func.count(Ticket.id))
            .group_by(Ticket.priority)
            .all()
        )
        for p, count in priority_counts:
            val = p.value if hasattr(p, "value") else str(p)
            by_priority[val] = count

        assigned_to_me = (
            db.query(func.count(Ticket.id))
            .filter(Ticket.assigned_to == current_user.id)
            .scalar()
            or 0
        )

    return DashboardSummary(
        total_tickets=total,
        by_status=by_status,
        by_priority=by_priority,
        assigned_to_me=assigned_to_me,
    )
