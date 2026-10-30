from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.dashboard import DashboardSummary
from app.services import ticket_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get role-scoped dashboard metrics summary",
    description="Returns aggregate ticket statistics strictly scoped to the caller's role.",
)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve ticket metrics scoped to the caller's role."""
    return ticket_service.get_dashboard_summary(db=db, current_user=current_user)
