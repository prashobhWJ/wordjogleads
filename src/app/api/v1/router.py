"""
Main API router for v1 endpoints
"""
from fastapi import APIRouter

from app.api.v1.endpoints import leads

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(leads.router, tags=["leads"])
