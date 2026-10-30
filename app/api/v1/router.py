from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, tickets, dashboard

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tickets.router)
api_router.include_router(dashboard.router)
