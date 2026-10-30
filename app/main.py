from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    """Application factory for Helpdesk Ticket Management API."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
    )

    @application.get("/", tags=["Health"])
    def root():
        return {
            "message": "Helpdesk API is running",
            "version": settings.VERSION,
        }

    # Mount routes at root and versioned path for universal compatibility
    application.include_router(api_router)
    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
