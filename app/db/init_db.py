from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import engine
from app.models import (
    Base,
    Booking,
    BookingSeat,
    BookingStatus,
    Customer,
    Event,
    EventStatus,
    Seat,
    Venue,
    Wallet,
)


def seed() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    now = datetime.now(timezone.utc)

    with Session(engine) as db:
        venues = [
            Venue(name="Grand Arena", address="100 Main Street"),
            Venue(name="City Theater", address="200 Center Avenue"),
            Venue(name="Open Air Park", address="300 Festival Road"),
        ]
        db.add_all(venues)
        db.flush()

        prices = {
            "VIP": Decimal("150.00"),
            "A": Decimal("95.00"),
            "B": Decimal("65.00"),
        }
        for venue in venues:
            for section in ("VIP", "A", "B"):
                for row_number in range(1, 3):
                    for seat_number in range(1, 6):
                        db.add(
                            Seat(
                                venue_id=venue.id,
                                section=section,
                                row_number=row_number,
                                seat_number=seat_number,
                                price=prices[section],
                            )
                        )

        events = [
            Event(
                name="Rock Festival 2025",
                venue_id=venues[0].id,
                event_date=now + timedelta(days=30),
                status=EventStatus.UPCOMING,
            ),
            Event(
                name="Jazz Night",
                venue_id=venues[1].id,
                event_date=now + timedelta(days=20),
                status=EventStatus.UPCOMING,
            ),
            Event(
                name="Classical Evening",
                venue_id=venues[1].id,
                event_date=now + timedelta(days=10),
                status=EventStatus.UPCOMING,
            ),
            Event(
                name="Food and Music Fair",
                venue_id=venues[2].id,
                event_date=now - timedelta(days=2),
                status=EventStatus.COMPLETED,
            ),
            Event(
                name="Indie Showcase",
                venue_id=venues[0].id,
                event_date=now + timedelta(days=45),
                status=EventStatus.CANCELLED,
            ),
        ]
        db.add_all(events)

        customers = [
            Customer(name=f"Customer {index}", email=f"customer{index}@example.com")
            for index in range(1, 21)
        ]
        db.add_all(customers)
        db.flush()

        wallets = [
            Wallet(customer_id=customer.id, balance=Decimal("1000.00"))
            for customer in customers
        ]
        db.add_all(wallets)
        db.flush()

        first_event_seats = db.scalars(
            select(Seat).where(Seat.venue_id == venues[0].id).order_by(Seat.id).limit(3)
        ).all()
        second_event_seats = db.scalars(
            select(Seat).where(Seat.venue_id == venues[1].id).order_by(Seat.id).limit(2)
        ).all()

        for customer, wallet, event, seats in (
            (customers[0], wallets[0], events[0], first_event_seats[:2]),
            (customers[1], wallets[1], events[1], second_event_seats[:1]),
            (customers[2], wallets[2], events[3], second_event_seats[1:2]),
        ):
            total_amount = sum((seat.price for seat in seats), Decimal("0.00"))
            booking = Booking(
                customer_id=customer.id,
                event_id=event.id,
                status=BookingStatus.CONFIRMED,
                total_amount=total_amount,
                booking_seats=[
                    BookingSeat(
                        seat_id=seat.id,
                        event_id=event.id,
                        price_paid=seat.price,
                    )
                    for seat in seats
                ],
            )
            wallet.balance -= total_amount
            db.add(booking)

        db.commit()


if __name__ == "__main__":
    seed()
    print("Database initialized with seed data.")
