from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Group
from bot.keyboards.reply_builders import quick_tags_reply_keyboard, remove_reply_keyboard
from bot.services.tags import list_tags
from bot.utils.text import Locale

logger = logging.getLogger(__name__)


async def _remove_legacy_inline_panel(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    chat_id: int,
) -> None:
    if not group.quick_panel_message_id:
        return
    message_id = group.quick_panel_message_id
    try:
        await bot.unpin_chat_message(chat_id, message_id)
    except TelegramBadRequest:
        pass
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass
    group.quick_panel_message_id = None
    await session.commit()


async def send_quick_panel(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    locale: Locale,
    chat_id: int,
    *,
    updated: bool = False,
) -> None:
    if not group.enable_quick_buttons:
        await bot.send_message(chat_id, locale.get("commands.quick_panel_disabled"))
        return

    tags = await list_tags(session, group.id)
    if not tags:
        await bot.send_message(chat_id, locale.get("no_tags"))
        return

    await _remove_legacy_inline_panel(bot, session, group, chat_id)

    text = (
        locale.get("commands.quick_panel_updated")
        if updated
        else locale.get("commands.quick_panel_on")
    )
    keyboard = quick_tags_reply_keyboard(locale, tags)
    await bot.send_message(
        chat_id,
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def hide_quick_panel(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    locale: Locale,
    chat_id: int,
) -> None:
    await _remove_legacy_inline_panel(bot, session, group, chat_id)
    await bot.send_message(
        chat_id,
        locale.get("commands.quick_panel_hidden"),
        reply_markup=remove_reply_keyboard(),
    )


async def refresh_quick_panel(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    locale: Locale,
    chat_id: int,
) -> None:
    if not group.enable_quick_buttons:
        return
    tags = await list_tags(session, group.id)
    if not tags:
        await hide_quick_panel(bot, session, group, locale, chat_id)
        return
    await send_quick_panel(bot, session, group, locale, chat_id, updated=True)
