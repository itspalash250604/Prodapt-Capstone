"""API v1 router composition."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import health, intake, recommendations


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(intake.router)
api_router.include_router(recommendations.router)
