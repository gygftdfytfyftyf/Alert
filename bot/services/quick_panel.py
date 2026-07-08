from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Group
from bot.keyboards.builders import tag_list_keyboard
from bot.keyboards.reply_builders import quick_tags_reply_keyboard, remove_reply_keyboard
from bot.services.tags import list_tags
from bot.utils.text import Locale

logger = logging.getLogger(__name__)


async def _upsert_pinned_inline_panel(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    locale: Locale,
    chat_id: int,
    tags: list,
) -> None:
    text = locale.get("commands.quick_panel_inline")
    keyboard = tag_list_keyboard(locale, tags, for_call=True)

    if group.quick_panel_message_id:
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=group.quick_panel_message_id,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            return
        except TelegramBadRequest:
            group.quick_panel_message_id = None
            await session.commit()

    message = await bot.send_message(
        chat_id,
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    group.quick_panel_message_id = message.message_id
    await session.commit()

    try:
        await bot.pin_chat_message(chat_id, message.message_id, disable_notification=True)
    except TelegramBadRequest:
        logger.warning("Could not pin quick panel in chat %s", chat_id)


async def _remove_pinned_inline_panel(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    chat_id: int,
) -> None:
    if not group.quick_panel_message_id:
        return

    message_id = group.quick_panel_message_id
    group.quick_panel_message_id = None
    await session.commit()

    try:
        await bot.unpin_chat_message(chat_id, message_id=message_id)
    except TelegramBadRequest:
        pass
    except Exception:
        logger.warning("Failed to unpin quick panel %s in chat %s", message_id, chat_id, exc_info=True)

    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass


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

    text = (
        locale.get("commands.quick_panel_updated")
        if updated
        else locale.get("commands.quick_panel_on")
    )
    reply_keyboard = quick_tags_reply_keyboard(locale, tags)

    try:
        await _upsert_pinned_inline_panel(bot, session, group, locale, chat_id, tags)
    except Exception:
        logger.exception("Failed to update pinned inline quick panel in chat %s", chat_id)

    await bot.send_message(
        chat_id,
        text,
        reply_markup=reply_keyboard,
        parse_mode="HTML",
    )


async def hide_quick_panel(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    locale: Locale,
    chat_id: int,
) -> None:
    await _remove_pinned_inline_panel(bot, session, group, chat_id)
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

    try:
        await _upsert_pinned_inline_panel(bot, session, group, locale, chat_id, tags)
    except Exception:
        logger.exception("Failed to refresh pinned inline quick panel in chat %s", chat_id)

    await bot.send_message(
        chat_id,
        locale.get("commands.quick_panel_updated"),
        reply_markup=quick_tags_reply_keyboard(locale, tags),
        parse_mode="HTML",
    )
