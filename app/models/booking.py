from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.event import Event
    from app.models.seat import Seat


class BookingStatus(str, PyEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(
            BookingStatus,
            name="booking_status",
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=BookingStatus.CONFIRMED,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    customer: Mapped["Customer"] = relationship(back_populates="bookings")
    event: Mapped["Event"] = relationship(back_populates="bookings")
    booking_seats: Mapped[list["BookingSeat"]] = relationship(
        back_populates="booking",
        cascade="all, delete-orphan",
    )


class BookingSeat(Base):
    __tablename__ = "booking_seats"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "seat_id",
            name="uq_event_seat",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), nullable=False)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"), nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    price_paid: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    booking: Mapped["Booking"] = relationship(back_populates="booking_seats")
    seat: Mapped["Seat"] = relationship()
    event: Mapped["Event"] = relationship()
