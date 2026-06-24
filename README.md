# Ticket Booking System

FastAPI + SQLAlchemy + PostgreSQL implementation for the ticket booking challenge.

## Setup

Start PostgreSQL:

```powershell
docker compose up -d
```

Install dependencies:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create tables and seed data:

```powershell
python -m app.db.init_db
```

Run the API at `http://localhost:8000`:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Run tests:

```powershell
pytest
```

## Database

Default configuration:

- Host: `localhost`
- Port: `5432`
- Database: `ticketing`
- User: `candidate`
- Password: `challenge2026`

Override with `DATABASE_URL` when needed.

## Endpoints

- `POST /api/v1/bookings`
- `POST /api/v1/bookings/cancel`
