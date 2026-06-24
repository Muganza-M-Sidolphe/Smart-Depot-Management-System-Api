from fastapi import APIRouter

from app.api.v1.endpoints import business, depots, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(depots.router, prefix="/depots", tags=["depots"])
api_router.include_router(business.router, tags=["business"])
