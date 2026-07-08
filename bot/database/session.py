from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import get_settings
from bot.database.models import Base


def create_engine():
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False)


engine = create_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def _apply_migrations(connection) -> None:
    inspector = inspect(connection)
    if not inspector.has_table("groups"):
        return
    columns = {column["name"] for column in inspector.get_columns("groups")}
    if "enable_quick_buttons" not in columns:
        connection.execute(
            text("ALTER TABLE groups ADD COLUMN enable_quick_buttons BOOLEAN DEFAULT 1 NOT NULL")
        )


async def init_db() -> None:
    if engine.url.get_backend_name() == "sqlite":
        db_path = engine.url.database
        if db_path and db_path != ":memory:":
            from pathlib import Path

            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_apply_migrations)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
