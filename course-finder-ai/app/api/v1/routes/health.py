"""Health check routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.schemas import HealthResponse


router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="course-finder-ai",
        version="v1",
    )
