from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.booking import (
    BookingCreate,
    BookingResponse,
    BulkCancelRequest,
    BulkCancelResponse,
)
from app.services.booking_service import cancel_bookings, create_booking

router = APIRouter(prefix="/api/v1/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def book_seats(payload: BookingCreate, db: Session = Depends(get_db)):
    return create_booking(
        db=db,
        customer_id=payload.customer_id,
        event_id=payload.event_id,
        seat_ids=payload.seat_ids,
    )


@router.post("/cancel", response_model=BulkCancelResponse)
def bulk_cancel_bookings(payload: BulkCancelRequest, db: Session = Depends(get_db)):
    return cancel_bookings(db=db, booking_ids=payload.booking_ids)
