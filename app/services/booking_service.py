from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.booking import Booking, BookingSeat, BookingStatus
from app.models.customer import Customer
from app.models.event import Event, EventStatus
from app.models.seat import Seat
from app.models.wallet import Wallet
from app.schemas.booking import (
    BookingResponse,
    BookingSeatResponse,
    BulkCancelResponse,
    CancelResult,
    money,
)


def _booking_response(booking: Booking) -> BookingResponse:
    return BookingResponse(
        id=booking.id,
        customer_id=booking.customer_id,
        event_id=booking.event_id,
        event_name=booking.event.name,
        status=booking.status.value,
        seats=[
            BookingSeatResponse(
                seat_id=booking_seat.seat_id,
                section=booking_seat.seat.section,
                row_number=booking_seat.seat.row_number,
                seat_number=booking_seat.seat.seat_number,
                price_paid=money(booking_seat.price_paid),
            )
            for booking_seat in booking.booking_seats
        ],
        total_amount=money(booking.total_amount),
        created_at=booking.created_at,
    )


def create_booking(
    db: Session,
    customer_id: int,
    event_id: int,
    seat_ids: list[int],
) -> BookingResponse:
    if not seat_ids:
        raise HTTPException(status_code=400, detail="At least one seat must be selected")

    if len(seat_ids) != len(set(seat_ids)):
        raise HTTPException(status_code=400, detail="Duplicate seats in selection")

    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != EventStatus.UPCOMING:
        raise HTTPException(status_code=400, detail="Event is not available for booking")

    wallet = db.scalars(
        select(Wallet)
        .where(Wallet.customer_id == customer_id)
        .with_for_update()
    ).first()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found for customer")

    seats: list[Seat] = []
    for seat_id in seat_ids:
        seat = db.get(Seat, seat_id)
        if seat is None:
            raise HTTPException(status_code=404, detail=f"Seat not found: {seat_id}")
        if seat.venue_id != event.venue_id:
            raise HTTPException(
                status_code=400,
                detail=f"Seat {seat_id} does not belong to this event's venue",
            )
        seats.append(seat)

    booked_seats = db.scalars(
        select(BookingSeat)
        .options(joinedload(BookingSeat.seat))
        .where(
            BookingSeat.event_id == event_id,
            BookingSeat.seat_id.in_(seat_ids),
        )
        .with_for_update()
    ).all()
    if booked_seats:
        booked_seat = booked_seats[0].seat
        raise HTTPException(
            status_code=409,
            detail=(
                "Seat already booked: "
                f"section {booked_seat.section}, "
                f"row {booked_seat.row_number}, "
                f"seat {booked_seat.seat_number}"
            ),
        )

    total_amount = sum((seat.price for seat in seats), Decimal("0.00"))
    if wallet.balance < total_amount:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient balance: required {money(total_amount)}, "
                f"available {money(wallet.balance)}"
            ),
        )

    booking = Booking(
        customer_id=customer_id,
        event_id=event_id,
        status=BookingStatus.CONFIRMED,
        total_amount=total_amount,
        booking_seats=[
            BookingSeat(event_id=event_id, seat_id=seat.id, price_paid=seat.price)
            for seat in seats
        ],
    )
    wallet.balance -= total_amount
    db.add(booking)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Seat already booked")

    booking = db.scalars(
        select(Booking)
        .options(
            joinedload(Booking.event),
            selectinload(Booking.booking_seats).joinedload(BookingSeat.seat),
        )
        .where(Booking.id == booking.id)
    ).one()
    return _booking_response(booking)


def cancel_bookings(db: Session, booking_ids: list[int]) -> BulkCancelResponse:
    if not booking_ids:
        raise HTTPException(status_code=400, detail="At least one booking ID is required")

    results: list[CancelResult] = []
    successful = 0

    for booking_id in booking_ids:
        booking = db.scalars(
            select(Booking)
            .options(joinedload(Booking.event))
            .where(Booking.id == booking_id)
            .with_for_update()
        ).first()

        if booking is None:
            results.append(
                CancelResult(
                    booking_id=booking_id,
                    status="failed",
                    refund_amount="0.00",
                    message="Booking not found",
                )
            )
            continue

        if booking.status == BookingStatus.CANCELLED:
            results.append(
                CancelResult(
                    booking_id=booking_id,
                    status="failed",
                    refund_amount="0.00",
                    message="Booking already cancelled",
                )
            )
            continue

        if booking.event.status == EventStatus.COMPLETED:
            results.append(
                CancelResult(
                    booking_id=booking_id,
                    status="failed",
                    refund_amount="0.00",
                    message="Event already completed",
                )
            )
            continue

        wallet = db.scalars(
            select(Wallet)
            .where(Wallet.customer_id == booking.customer_id)
            .with_for_update()
        ).first()
        if wallet is None:
            results.append(
                CancelResult(
                    booking_id=booking_id,
                    status="failed",
                    refund_amount="0.00",
                    message="Wallet not found for customer",
                )
            )
            continue

        refund_amount = booking.total_amount
        wallet.balance += refund_amount
        booking.status = BookingStatus.CANCELLED
        db.execute(delete(BookingSeat).where(BookingSeat.booking_id == booking.id))
        successful += 1
        results.append(
            CancelResult(
                booking_id=booking_id,
                status="cancelled",
                refund_amount=money(refund_amount),
                message="Booking cancelled successfully",
            )
        )

    db.commit()
    return BulkCancelResponse(
        total_requested=len(booking_ids),
        successful=successful,
        failed=len(booking_ids) - successful,
        results=results,
    )
