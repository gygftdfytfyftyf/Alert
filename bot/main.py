from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.bootstrap import setup_bot
from bot.config import get_settings
from bot.database.session import init_db
from bot.handlers import activity, callbacks, commands, fsm_handlers, members, migration, quick_buttons
from bot.middlewares.deps import DependenciesMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    logging.getLogger().setLevel(settings.log_level)

    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    me = await bot.get_me()
    await setup_bot(bot)
    logger.info("Bot @%s is ready for groups", me.username)

    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.middleware(DependenciesMiddleware(settings.locale))

    dispatcher.include_router(commands.router)
    dispatcher.include_router(migration.router)
    dispatcher.include_router(callbacks.router)
    dispatcher.include_router(fsm_handlers.router)
    dispatcher.include_router(quick_buttons.router)
    dispatcher.include_router(members.router)
    dispatcher.include_router(activity.router)

    logger.info("Polling started")
    await dispatcher.start_polling(
        bot,
        allowed_updates=["message", "callback_query", "my_chat_member", "chat_member"],
    )


if __name__ == "__main__":
    asyncio.run(main())
