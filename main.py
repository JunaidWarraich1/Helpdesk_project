from fastapi import FastAPI, Depends, status, HTTPException, Query
from database import engine, Base, get_db
import models
from fastapi.security import OAuth2PasswordBearer
from auth import create_access_token, decode_access_token, hash_password, verify_password
from schemas import (
    DashboardSummary,
    TicketAssign,
    TicketCreate,
    TicketListResponse,
    TicketResponse,
    TicketStatusUpdate,
    TicketUpdate,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Helpdesk Ticket Management API", version="1.0.0")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@app.get("/")
def root():
    return {"message": "Helpdesk API is running", "version": "1.0.0"}


@app.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = (
        db.query(models.User).filter(models.User.email == user_data.email).first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )
    hashed_pwd = hash_password(user_data.password)
    new_user = models.User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_pwd,
        role=user_data.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = (
        db.query(models.User)
        .filter(models.User.email == login_data.email)
        .first()
    )
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if not user:
        raise credentials_exception
    return user


@app.get("/users/me", response_model=UserResponse)
def get_my_profile(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.post(
    "/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    new_ticket = models.Ticket(
        title=ticket_data.title,
        description=ticket_data.description,
        category=ticket_data.category,
        priority=ticket_data.priority,
        created_by=current_user.id,
        assigned_to=ticket_data.assigned_to,
    )
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    return new_ticket


@app.get("/tickets", response_model=TicketListResponse)
def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    assigned_to: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Ticket)

    if current_user.role == models.UserRole.EMPLOYEE:
        query = query.filter(models.Ticket.created_by == current_user.id)
    elif current_user.role == models.UserRole.AGENT:
        query = query.filter(models.Ticket.assigned_to == current_user.id)

    if status:
        query = query.filter(models.Ticket.status == status)
    if priority:
        query = query.filter(models.Ticket.priority == priority)
    if category:
        query = query.filter(models.Ticket.category == category)
    if assigned_to:
        query = query.filter(models.Ticket.assigned_to == assigned_to)
    if search:
        query = query.filter(models.Ticket.title.ilike(f"%{search}%"))

    total = query.count()
    tickets = (
        query.order_by(models.Ticket.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return TicketListResponse(
        tickets=tickets, total=total, limit=limit, offset=offset
    )


ALLOWED_TRANSITIONS = {
    models.TicketStatus.OPEN: [models.TicketStatus.IN_PROGRESS],
    models.TicketStatus.IN_PROGRESS: [models.TicketStatus.RESOLVED],
    models.TicketStatus.RESOLVED: [models.TicketStatus.CLOSED],
    models.TicketStatus.CLOSED: [],
}


@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ticket = (
        db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    )
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    if (
        current_user.role == models.UserRole.EMPLOYEE
        and ticket.created_by != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    if (
        current_user.role == models.UserRole.AGENT
        and ticket.assigned_to != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    return ticket


@app.patch("/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    update_data: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ticket = (
        db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    )
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    if ticket.status == models.TicketStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Closed tickets are read-only and cannot be updated",
        )

    if (
        current_user.role == models.UserRole.EMPLOYEE
        and ticket.created_by != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    if (
        current_user.role == models.UserRole.AGENT
        and ticket.assigned_to != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(ticket, key, value)

    db.commit()
    db.refresh(ticket)
    return ticket


@app.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ticket = (
        db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    )
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    if (
        current_user.role != models.UserRole.ADMIN
        and ticket.created_by != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or the creator can delete this ticket",
        )

    db.delete(ticket)
    db.commit()


@app.patch("/tickets/{ticket_id}/assign", response_model=TicketResponse)
def assign_ticket(
    ticket_id: int,
    assign_data: TicketAssign,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can assign tickets",
        )

    ticket = (
        db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    )
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )
    if ticket.status == models.TicketStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign a closed ticket",
        )

    agent = (
        db.query(models.User).filter(models.User.id == assign_data.agent_id).first()
    )
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )
    if agent.role != models.UserRole.AGENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tickets can only be assigned to users with the AGENT role",
        )

    ticket.assigned_to = assign_data.agent_id
    db.commit()
    db.refresh(ticket)
    return ticket


@app.patch("/tickets/{ticket_id}/status", response_model=TicketResponse)
def update_ticket_status(
    ticket_id: int,
    status_data: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ticket = (
        db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    )
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    if current_user.role == models.UserRole.EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees cannot change ticket status",
        )
    if (
        current_user.role == models.UserRole.AGENT
        and ticket.assigned_to != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    if ticket.status == models.TicketStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Closed tickets are read-only"
        )

    if status_data.status not in ALLOWED_TRANSITIONS.get(ticket.status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid status transition from {ticket.status.value} to"
                f" {status_data.status.value}"
            ),
        )

    if (
        status_data.status == models.TicketStatus.IN_PROGRESS
        and ticket.assigned_to is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot move ticket to IN_PROGRESS without an assigned agent",
        )

    ticket.status = status_data.status
    db.commit()
    db.refresh(ticket)
    return ticket


@app.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    total = db.query(func.count(models.Ticket.id)).scalar()

    status_counts = (
        db.query(models.Ticket.status, func.count(models.Ticket.id))
        .group_by(models.Ticket.status)
        .all()
    )
    by_status = {s.value: 0 for s in models.TicketStatus}
    for s, count in status_counts:
        by_status[s.value] = count

    priority_counts = (
        db.query(models.Ticket.priority, func.count(models.Ticket.id))
        .group_by(models.Ticket.priority)
        .all()
    )
    by_priority = {p.value: 0 for p in models.TicketPriority}
    for p, count in priority_counts:
        by_priority[p.value] = count

    assigned_to_me = None
    if current_user.role in (models.UserRole.AGENT, models.UserRole.ADMIN):
        assigned_to_me = (
            db.query(func.count(models.Ticket.id))
            .filter(models.Ticket.assigned_to == current_user.id)
            .scalar()
        )

    return {
        "total_tickets": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "assigned_to_me": assigned_to_me,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
