from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.roles import MANAGEMENT
from app.schemas.depot import DepotCreate, DepotRead, DepotUpdate
from app.services import depot_service

router = APIRouter()


@router.get("/", response_model=list[DepotRead])
async def list_depots(db: Session = Depends(get_db)) -> list[DepotRead]:
    return depot_service.list_depots(db)


@router.post(
    "/",
    response_model=DepotRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*MANAGEMENT))],
)
async def create_depot(payload: DepotCreate, db: Session = Depends(get_db)) -> DepotRead:
    return depot_service.create_depot(db, payload)


@router.get("/{depot_id}", response_model=DepotRead)
async def get_depot(depot_id: int, db: Session = Depends(get_db)) -> DepotRead:
    depot = depot_service.get_depot(db, depot_id)
    if depot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Depot not found")
    return depot


@router.patch(
    "/{depot_id}",
    response_model=DepotRead,
    dependencies=[Depends(require_roles(*MANAGEMENT))],
)
async def update_depot(
    depot_id: int,
    payload: DepotUpdate,
    db: Session = Depends(get_db),
) -> DepotRead:
    depot = depot_service.update_depot(db, depot_id, payload)
    if depot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Depot not found")
    return depot


@router.delete(
    "/{depot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*MANAGEMENT))],
)
async def delete_depot(depot_id: int, db: Session = Depends(get_db)) -> None:
    deleted = depot_service.delete_depot(db, depot_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Depot not found")
