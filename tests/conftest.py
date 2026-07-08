import os
from pathlib import Path

TEST_DB = Path(__file__).resolve().parent.parent / "data" / "pytest.db"
TEST_DB.parent.mkdir(parents=True, exist_ok=True)
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ["BOT_TOKEN"] = "123456789:TEST_TOKEN_FOR_UNIT_TESTS"
os.environ["BOT_OWNER_IDS"] = "111222333"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB}"

import pytest

from bot.database.session import SessionLocal, init_db


@pytest.fixture
async def session():
    await init_db()
    async with SessionLocal() as db_session:
        yield db_session
