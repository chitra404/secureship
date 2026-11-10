"""A tiny in-memory shipment store.

Data lives only in memory, so it is cleared whenever the app restarts. That keeps
the container simple (read-only filesystem, no database to secure) and is fine for a demo.
"""

import secrets
import threading
from datetime import datetime, timezone

from app.schemas import HistoryEntry, Shipment, ShipmentCreate

STATUS_FLOW = ["created", "in_transit", "out_for_delivery", "delivered"]
MAX_SHIPMENTS = 500  # stops anyone from filling up memory


class ShipmentNotFound(Exception):
    pass


class AlreadyDelivered(Exception):
    pass


class StoreFull(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ShipmentStore:
    def __init__(self, limit: int = MAX_SHIPMENTS) -> None:
        self._items: dict[str, Shipment] = {}
        self._limit = limit
        self._lock = threading.Lock()

    def create(self, data: ShipmentCreate) -> Shipment:
        with self._lock:
            if len(self._items) >= self._limit:
                raise StoreFull()
            code = f"SS-{secrets.token_hex(4).upper()}"
            while code in self._items:
                code = f"SS-{secrets.token_hex(4).upper()}"
            now = _now()
            shipment = Shipment(
                tracking_code=code,
                status="created",
                created_at=now,
                history=[HistoryEntry(status="created", at=now)],
                **data.model_dump(),
            )
            self._items[code] = shipment
            return shipment.model_copy(deep=True)

    def list(self) -> list[Shipment]:
        with self._lock:
            items = sorted(self._items.values(), key=lambda s: s.created_at, reverse=True)
            return [s.model_copy(deep=True) for s in items]

    def get(self, code: str) -> Shipment:
        with self._lock:
            if code not in self._items:
                raise ShipmentNotFound()
            return self._items[code].model_copy(deep=True)

    def advance(self, code: str) -> Shipment:
        with self._lock:
            if code not in self._items:
                raise ShipmentNotFound()
            shipment = self._items[code]
            index = STATUS_FLOW.index(shipment.status)
            if index == len(STATUS_FLOW) - 1:
                raise AlreadyDelivered()
            shipment.status = STATUS_FLOW[index + 1]
            shipment.history.append(HistoryEntry(status=shipment.status, at=_now()))
            return shipment.model_copy(deep=True)

    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
