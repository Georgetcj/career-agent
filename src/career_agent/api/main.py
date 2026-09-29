"""FastAPI application entry point."""

from typing import Literal

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from career_agent.api.routers.candidates import router as candidates_router
from career_agent.api.routers.knowledge import router as knowledge_router
from career_agent.infrastructure.database import check_database_connection

app = FastAPI(
    title="Career Agent API",
    version="0.1.0",
    description="API for the Career Agent job-search assistant.",
)
app.include_router(candidates_router)
app.include_router(knowledge_router)


class HealthResponse(BaseModel):
    """Successful dependency health status."""

    status: Literal["ok"]
    database: Literal["available"]


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Confirm that the API and its PostgreSQL dependency are usable."""

    try:
        check_database_connection()
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from error

    return HealthResponse(status="ok", database="available")
