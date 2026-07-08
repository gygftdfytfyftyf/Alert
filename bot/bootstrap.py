from __future__ import annotations

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeDefault,
)


async def setup_bot(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="tags", description="Список тегов для вызова"),
        BotCommand(command="help", description="Справка"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    await bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())
    await bot.set_my_description(
        "Управление тегами (ролями) участников в группах: создание тегов, "
        "назначение людей и быстрый вызов через @упоминания."
    )
    await bot.set_my_short_description("Теги и упоминания для групповых чатов")
