from __future__ import annotations

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeDefault,
)


async def setup_bot(bot: Bot) -> None:
    admin_commands = [
        BotCommand(command="menu", description="Панель управления тегами"),
        BotCommand(command="panel", description="Опубликовать быстрые кнопки"),
        BotCommand(command="panel_hide", description="Скрыть быстрые кнопки"),
        BotCommand(command="help", description="Справка"),
    ]
    member_commands = [
        BotCommand(command="panel", description="Быстрые кнопки тегов"),
        BotCommand(command="help", description="Справка"),
    ]

    await bot.set_my_commands(admin_commands, scope=BotCommandScopeDefault())
    await bot.set_my_commands(admin_commands, scope=BotCommandScopeAllChatAdministrators())
    await bot.set_my_commands(member_commands, scope=BotCommandScopeAllGroupChats())
    await bot.set_my_description(
        "Управление тегами (ролями) участников в группах: создание тегов, "
        "назначение людей и быстрый вызов через @упоминания."
    )
    await bot.set_my_short_description("Теги и упоминания для групповых чатов")
