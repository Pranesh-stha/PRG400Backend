# Travel Booking API (Backend)

The backend service for the Travel Booking app. It is a FastAPI application that exposes a REST API for authentication, properties, bookings, and reviews, and talks to a Neon (PostgreSQL) database over an async SQLAlchemy connection.

## Tech stack

- **FastAPI** (0.115) — web framework
- **Uvicorn** — ASGI server
- **SQLAlchemy 2.0 (async)** + **asyncpg** — database access
- **Pydantic v2** + **pydantic-settings** — request/response models and config
- **bcrypt** — password hashing
- **python-jose** — JWT auth

## Project layout

```
backend/
├── app/
│   ├── auth/        # JWT + password hashing helpers
│   ├── models/      # SQLAlchemy ORM models
│   ├── routes/      # auth, properties, bookings, reviews
│   ├── schemas/     # Pydantic request/response schemas
│   ├── config.py    # settings loaded from .env
│   ├── database.py  # async engine + session
│   └── main.py      # FastAPI app + CORS + router wiring
├── requirements.txt
├── .env.example     # copy to .env and fill in values
└── .python-version
```

## How to run it

### 1. Set up Python and a virtual environment

From the `backend/` folder:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example file and fill in real values:

```bash
cp .env.example .env
```

You will need:

- `DATABASE_URL` — your Neon connection string. **Important:** replace the `postgresql://` prefix with `postgresql+asyncpg://` so SQLAlchemy uses the async driver.
- `JWT_SECRET` — a long random string. Generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
- `JWT_ALGORITHM` — defaults to `HS256`
- `JWT_EXPIRE_MINUTES` — token lifetime (default `10080` = 7 days)
- `FRONTEND_URL` — used for CORS. `http://localhost:5173` for local dev, your Vercel URL in production.

### 4. Set up the database

In the Neon SQL editor, run the SQL files from `../database/` in order:

1. `schema.sql` — creates tables, indexes, constraints
2. `seed.sql` — adds a demo host (`demo@stay.com` / `DemoHost123!`) and 8 sample properties

### 5. Start the server

```bash
uvicorn app.main:app --reload
```

The API will be available at:

- **Root:** http://localhost:8000/
- **Health check:** http://localhost:8000/health
- **Interactive docs (Swagger):** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Deploying

Designed to deploy to **Render** as a web service. Set the same environment variables in the Render dashboard (Service → Environment) instead of using a `.env` file. The start command is:

```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
