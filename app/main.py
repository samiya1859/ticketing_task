from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import bookings_router
from app.db.database import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Ticket Booking System", lifespan=lifespan)

app.include_router(bookings_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
