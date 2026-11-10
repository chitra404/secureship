from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["created", "in_transit", "out_for_delivery", "delivered"]


class ShipmentCreate(BaseModel):
    """Data the user sends to create a shipment."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    sender: str = Field(min_length=1, max_length=60)
    receiver: str = Field(min_length=1, max_length=60)
    destination: str = Field(min_length=1, max_length=100)
    item: str = Field(min_length=1, max_length=100)


class HistoryEntry(BaseModel):
    status: Status
    at: datetime


class Shipment(BaseModel):
    tracking_code: str
    sender: str
    receiver: str
    destination: str
    item: str
    status: Status
    created_at: datetime
    history: list[HistoryEntry]
