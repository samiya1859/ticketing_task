import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import get_db
from app.main import app
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

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def seed_test_data():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        venue = Venue(name="Test Venue", address="123 Test Street")
        other_venue = Venue(name="Other Venue", address="999 Elsewhere")
        db.add_all([venue, other_venue])
        db.flush()

        event = Event(
            name="Rock Festival 2025",
            venue_id=venue.id,
            event_date=datetime.now(timezone.utc) + timedelta(days=7),
            status=EventStatus.UPCOMING,
        )
        completed_event = Event(
            name="Completed Event",
            venue_id=venue.id,
            event_date=datetime.now(timezone.utc) - timedelta(days=1),
            status=EventStatus.COMPLETED,
        )
        db.add_all([event, completed_event])
        db.flush()

        seats = [
            Seat(
                venue_id=venue.id,
                section="A",
                row_number=1,
                seat_number=number,
                price=Decimal("50.00"),
            )
            for number in range(1, 4)
        ]
        other_seat = Seat(
            venue_id=other_venue.id,
            section="B",
            row_number=1,
            seat_number=1,
            price=Decimal("75.00"),
        )
        db.add_all([*seats, other_seat])

        customer = Customer(name="Customer One", email="one@example.com")
        low_balance_customer = Customer(name="Customer Two", email="two@example.com")
        db.add_all([customer, low_balance_customer])
        db.flush()

        db.add_all(
            [
                Wallet(customer_id=customer.id, balance=Decimal("500.00")),
                Wallet(customer_id=low_balance_customer.id, balance=Decimal("10.00")),
            ]
        )

        existing_booking = Booking(
            customer_id=customer.id,
            event_id=completed_event.id,
            status=BookingStatus.CONFIRMED,
            total_amount=Decimal("50.00"),
            booking_seats=[
                BookingSeat(
                    event_id=completed_event.id,
                    seat_id=seats[0].id,
                    price_paid=Decimal("50.00"),
                )
            ],
        )
        db.add(existing_booking)
        db.commit()


def test_create_booking_charges_wallet_and_formats_money():
    seed_test_data()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/bookings",
            json={"customer_id": 1, "event_id": 1, "seat_ids": [2, 3]},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "confirmed"
    assert data["total_amount"] == "100.00"
    assert data["seats"][0]["price_paid"] == "50.00"

    with TestingSessionLocal() as db:
        wallet = db.scalar(select(Wallet).where(Wallet.customer_id == 1))
        assert wallet.balance == Decimal("400.00")


def test_create_booking_rejects_duplicate_selection():
    seed_test_data()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/bookings",
            json={"customer_id": 1, "event_id": 1, "seat_ids": [2, 2]},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Duplicate seats in selection"}


def test_create_booking_rejects_insufficient_balance():
    seed_test_data()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/bookings",
            json={"customer_id": 2, "event_id": 1, "seat_ids": [2]},
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Insufficient balance: required 50.00, available 10.00"
    }


def test_cancel_booking_refunds_and_releases_seat():
    seed_test_data()

    with TestClient(app) as client:
        cancel_response = client.post(
            "/api/v1/bookings/cancel",
            json={"booking_ids": [1]},
        )

    assert cancel_response.status_code == 200
    data = cancel_response.json()
    assert data["successful"] == 0
    assert data["results"][0]["message"] == "Event already completed"

    with TestClient(app) as client:
        booking_response = client.post(
            "/api/v1/bookings",
            json={"customer_id": 1, "event_id": 1, "seat_ids": [2]},
        )
        cancel_response = client.post(
            "/api/v1/bookings/cancel",
            json={"booking_ids": [2]},
        )
        rebook_response = client.post(
            "/api/v1/bookings",
            json={"customer_id": 1, "event_id": 1, "seat_ids": [2]},
        )

    assert booking_response.status_code == 201
    assert cancel_response.status_code == 200
    assert cancel_response.json()["results"][0]["refund_amount"] == "50.00"
    assert rebook_response.status_code == 201
