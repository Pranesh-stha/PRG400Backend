import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.routes import auth as auth_routes
from app.routes import bookings as booking_routes
from app.routes import properties as property_routes
from app.routes import reviews as review_routes


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        stream=sys.stdout,
    )


_setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting up — verifying database connection")
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection verified")
    yield
    logger.info("Shutting down — disposing database engine")
    await engine.dispose()


app = FastAPI(
    title="Travel Booking API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(property_routes.router)
app.include_router(booking_routes.router)
app.include_router(review_routes.router)


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"name": "Travel Booking API", "status": "ok"}


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
