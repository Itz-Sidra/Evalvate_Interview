"""
Database layer — PostgreSQL via SQLAlchemy async + asyncpg.

Replaces the Motor/PyMongo mongodb.py. Import `get_db` in your
FastAPI route dependencies instead of `get_database`.
"""

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Add it to backend/.env as:\n"
        "  DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname?sslmode=require"
    )

# NeonDB 
# pool_pre_ping=True drops stale connections silently.
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=os.getenv("ENVIRONMENT", "development") == "development",
)

# Session factory — used by get_db() dependency
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an AsyncSession per request.

    Usage in routes:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Startup / shutdown ────────────────────────────────────────────────────────

async def connect_to_postgres() -> None:
    """Called from app startup. Verifies the connection is healthy."""
    print("Connecting to PostgreSQL (NeonDB)...")
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        print("[OK] Connected to PostgreSQL successfully!")
    except Exception as exc:
        print(f"[FAIL] PostgreSQL connection failed: {exc}")
        raise


async def close_postgres_connection() -> None:
    """Called from app shutdown."""
    print("Closing PostgreSQL connection pool...")
    await engine.dispose()
    print("PostgreSQL connection pool closed.")


# ── Legacy compatibility shim ─────────────────────────────────────────────────
# Keeps old imports working during incremental migration.
# Remove once all callers use get_db().

class _LegacyDB:
    """
    Drop-in shim so code that imported `mongodb.db` doesn't crash immediately.
    Will raise a clear error instead of a confusing AttributeError.
    """
    def __getattr__(self, name: str):
        raise RuntimeError(
            f"Attempted to use legacy MongoDB attribute '{name}'. "
            "This has been migrated to PostgreSQL. Use `get_db()` instead."
        )


mongodb = _LegacyDB()  # keeps `from app.db import mongodb` from crashing at import time


def get_database():
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="get_database() is removed. Inject `AsyncSession` via Depends(get_db).",
    )


def get_sync_database():
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="get_sync_database() is removed. All DB access is now async via get_db().",
    )