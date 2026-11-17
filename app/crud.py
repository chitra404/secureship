
import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Shipment, ShipmentHistory
from app.schemas import ShipmentCreate


STATUS_FLOW = [
    "created",
    "in_transit",
    "out_for_delivery",
    "delivered",
]

MAX_SHIPMENTS = 500


class ShipmentNotFound(Exception):
    pass


class AlreadyDelivered(Exception):
    pass


class StoreFull(Exception):
    pass


def create_shipment(db: Session, data: ShipmentCreate) -> Shipment:
    """Create a shipment and its initial history entry."""

    count = db.scalar(select(func.count()).select_from(Shipment))

    if count >= MAX_SHIPMENTS:
        raise StoreFull()

    code = f"SS-{secrets.token_hex(4).upper()}"

    while db.scalar(
        select(Shipment.id).where(Shipment.tracking_code == code)
    ) is not None:
        code = f"SS-{secrets.token_hex(4).upper()}"

    shipment = Shipment(
        tracking_code=code,
        status="created",
        **data.model_dump(),
    )

    shipment.history.append(
        ShipmentHistory(status="created")
    )

    db.add(shipment)
    db.commit()

    return get_shipment(db, code)


def list_shipments(db: Session) -> list[Shipment]:
    """Return all shipments, newest first."""

    statement = (
        select(Shipment)
        .options(selectinload(Shipment.history))
        .order_by(Shipment.created_at.desc())
    )

    return list(db.scalars(statement).all())


def get_shipment(db: Session, code: str) -> Shipment:
    """Retrieve one shipment with its history."""

    statement = (
        select(Shipment)
        .options(selectinload(Shipment.history))
        .where(Shipment.tracking_code == code)
    )

    shipment = db.scalar(statement)

    if shipment is None:
        raise ShipmentNotFound()

    return shipment


def advance_shipment(db: Session, code: str) -> Shipment:
    """Advance a shipment to its next status."""

    shipment = get_shipment(db, code)

    index = STATUS_FLOW.index(shipment.status)

    if index == len(STATUS_FLOW) - 1:
        raise AlreadyDelivered()

    shipment.status = STATUS_FLOW[index + 1]

    shipment.history.append(
        ShipmentHistory(status=shipment.status)
    )

    db.commit()

    return get_shipment(db, code)


def count_shipments(db: Session) -> int:
    """Return the total number of shipments."""

    return db.scalar(
        select(func.count()).select_from(Shipment)
    )

