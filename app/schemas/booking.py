from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


def money(value: Decimal) -> str:
    return f"{value:.2f}"


class BookingCreate(BaseModel):
    customer_id: int
    event_id: int
    seat_ids: list[int]


class BookingSeatResponse(BaseModel):
    seat_id: int
    section: str
    row_number: int
    seat_number: int
    price_paid: str


class BookingResponse(BaseModel):
    id: int
    customer_id: int
    event_id: int
    event_name: str
    status: str
    seats: list[BookingSeatResponse]
    total_amount: str
    created_at: datetime


class BulkCancelRequest(BaseModel):
    booking_ids: list[int]


class CancelResult(BaseModel):
    booking_id: int
    status: str
    refund_amount: str
    message: str


class BulkCancelResponse(BaseModel):
    total_requested: int
    successful: int
    failed: int
    results: list[CancelResult]
