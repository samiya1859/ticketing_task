from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.venue import Venue


class EventStatus(str, PyEnum):
    UPCOMING = "upcoming"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), nullable=False)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        Enum(
            EventStatus,
            name="event_status",
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=EventStatus.UPCOMING,
    )

    venue: Mapped["Venue"] = relationship(back_populates="events")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="event")
