"""
Pytest fixtures for unit and integration tests.

All integration tests use a fully mocked AsyncSession so no real database
connection is required. The lifespan engine calls in app.main are also
patched so the app starts cleanly without Neon credentials.
"""

import os

# Must be set before any app module is imported so pydantic-settings picks
# them up at class-definition time.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("JWT_SECRET", "test-only-secret-key-min-32-characters-long")

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def mock_db():
    """
    Async session mock that simulates an empty database by default.

    Tests can override mock_db.execute.return_value or use side_effect to
    control what specific queries return.
    """
    session = AsyncMock()

    # Default result: no rows found
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalar_one.return_value = 0
    result.scalars.return_value.all.return_value = []
    result.all.return_value = []

    session.execute.return_value = result

    # Simulate DB refresh by populating server-generated fields
    async def _refresh(obj):
        if not getattr(obj, "id", None):
            obj.id = uuid.uuid4()
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)
        # server_default fields that have no Python-level default
        if getattr(obj, "is_host", None) is None:
            obj.is_host = False
        if not hasattr(obj, "avatar_url"):
            obj.avatar_url = None

    session.refresh.side_effect = _refresh

    return session


@pytest_asyncio.fixture
async def client(mock_db):
    """
    httpx AsyncClient wired to the FastAPI app with:
    - get_db overridden to yield mock_db
    - app.main.engine patched so the lifespan SELECT 1 and /health endpoint
      do not require a real database.
    """
    from app.database import get_db
    from app.main import app

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db

    mock_engine = AsyncMock()

    with patch("app.main.engine", mock_engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


def make_fake_user(**kwargs) -> MagicMock:
    """Build a fake User-like object with sensible defaults."""
    user = MagicMock()
    user.id = kwargs.get("id", uuid.uuid4())
    user.email = kwargs.get("email", "user@example.com")
    user.password_hash = kwargs.get("password_hash", "irrelevant")
    user.full_name = kwargs.get("full_name", "Test User")
    user.phone = kwargs.get("phone", None)
    user.avatar_url = kwargs.get("avatar_url", None)
    user.is_host = kwargs.get("is_host", False)
    user.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    user.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    return user
