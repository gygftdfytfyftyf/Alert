from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
LOCALES_DIR = Path(__file__).resolve().parent / "locales"
DEFAULT_LOCALE = "ru"


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    log_level: str
    locale: str


def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN environment variable is required")

    database_url = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'bot.db'}",
    ).strip()

    return Settings(
        bot_token=bot_token,
        database_url=database_url,
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        locale=os.getenv("LOCALE", DEFAULT_LOCALE).strip(),
    )
