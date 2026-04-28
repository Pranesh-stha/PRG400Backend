from collections.abc import AsyncIterator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _normalize_db_url(url: str) -> str:
    """Convert a libpq-style Neon URL to one asyncpg accepts.

    Neon provides URLs like:
        postgresql://u:p@h/db?sslmode=require&channel_binding=require

    asyncpg does not understand `sslmode` or `channel_binding` query params
    (those are libpq-specific). It uses `ssl=require` instead. We also force
    the SQLAlchemy dialect prefix to `postgresql+asyncpg`.
    """
    parsed = urlparse(url)
    scheme = "postgresql+asyncpg" if parsed.scheme in ("postgres", "postgresql") else parsed.scheme

    qs = parse_qs(parsed.query)
    qs.pop("sslmode", None)
    qs.pop("channel_binding", None)
    qs["ssl"] = ["require"]

    return urlunparse(parsed._replace(scheme=scheme, query=urlencode(qs, doseq=True)))


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    _normalize_db_url(settings.DATABASE_URL),
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
