from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.helpers import ensure_group, is_group_chat, send_main_menu, send_tag_list
from bot.utils.text import Locale

logger = logging.getLogger(__name__)
router = Router(name="commands")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, locale: Locale) -> None:
    if is_group_chat(message):
        group = await ensure_group(message, session, locale)
        if group is None:
            return
        await message.answer(locale.get("commands.start_group"))
        await send_main_menu(
            message.bot,
            session,
            locale,
            message.chat.id,
            message.from_user.id,
            group,
        )
    else:
        await message.answer(locale.get("commands.start_private"))


@router.message(Command("help"))
async def cmd_help(message: Message, locale: Locale) -> None:
    await message.answer(locale.get("commands.help"))


@router.message(Command("menu"))
async def cmd_menu(message: Message, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(message, session, locale)
    if group is None:
        return
    await send_main_menu(
        message.bot,
        session,
        locale,
        message.chat.id,
        message.from_user.id,
        group,
    )


@router.message(Command("tags"))
async def cmd_tags(message: Message, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(message, session, locale)
    if group is None:
        return
    await send_tag_list(
        message.bot,
        session,
        locale,
        message.chat.id,
        message.from_user.id,
        group,
    )
