
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tracking_code: Mapped[str] = mapped_column(
        String(11), unique=True, index=True, nullable=False
    )
    sender: Mapped[str] = mapped_column(String(60), nullable=False)
    receiver: Mapped[str] = mapped_column(String(60), nullable=False)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)
    item: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    history: Mapped[list["ShipmentHistory"]] = relationship(
        back_populates="shipment",
        cascade="all, delete-orphan",
        order_by="ShipmentHistory.id",
    )


class ShipmentHistory(Base):
    __tablename__ = "shipment_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    shipment: Mapped["Shipment"] = relationship(back_populates="history")

