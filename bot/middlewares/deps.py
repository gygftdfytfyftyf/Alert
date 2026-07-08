from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import DEFAULT_LOCALE
from bot.database.session import SessionLocal
from bot.utils.text import Locale, load_locale

logger = logging.getLogger(__name__)


class DependenciesMiddleware(BaseMiddleware):
    def __init__(self, locale_name: str = DEFAULT_LOCALE) -> None:
        self.locale = load_locale(locale_name)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["locale"] = self.locale
        async with SessionLocal() as session:
            data["session"] = session
            try:
                return await handler(event, data)
            except Exception:
                logger.exception("Unhandled handler error")
                bot: Bot | None = data.get("bot")
                if bot and isinstance(event, (Message, CallbackQuery)):
                    chat_id = event.chat.id if isinstance(event, Message) else event.message.chat.id  # type: ignore[union-attr]
                    try:
                        await bot.send_message(chat_id, self.locale.get("error_generic"))
                    except Exception:
                        logger.exception("Failed to send error message")
                return None
