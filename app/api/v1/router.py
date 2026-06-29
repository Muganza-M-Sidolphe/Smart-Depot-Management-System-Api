from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1.endpoints import auth, business, depots, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(
    depots.router,
    prefix="/depots",
    tags=["depots"],
    dependencies=[Depends(get_current_user)],
)
api_router.include_router(
    business.router,
    tags=["business"],
    dependencies=[Depends(get_current_user)],
)
