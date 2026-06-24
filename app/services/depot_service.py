from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.depot import Depot
from app.schemas.depot import DepotCreate, DepotUpdate


def list_depots(db: Session) -> list[Depot]:
    return list(db.scalars(select(Depot).order_by(Depot.id)))


def get_depot(db: Session, depot_id: int) -> Depot | None:
    return db.get(Depot, depot_id)


def create_depot(db: Session, payload: DepotCreate) -> Depot:
    depot = Depot(**payload.model_dump())
    db.add(depot)
    db.commit()
    db.refresh(depot)
    return depot


def update_depot(db: Session, depot_id: int, payload: DepotUpdate) -> Depot | None:
    depot = get_depot(db, depot_id)
    if depot is None:
        return None

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(depot, key, value)

    db.commit()
    db.refresh(depot)
    return depot


def delete_depot(db: Session, depot_id: int) -> bool:
    depot = get_depot(db, depot_id)
    if depot is None:
        return False

    db.delete(depot)
    db.commit()
    return True
