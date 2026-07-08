from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Group, Tag
from bot.keyboards.reply_builders import quick_tags_reply_keyboard, remove_reply_keyboard
from bot.services.tags import list_tags
from bot.utils.text import Locale

logger = logging.getLogger(__name__)


async def _cleanup_legacy_pinned_panel(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    chat_id: int,
) -> None:
    """Remove old pinned inline quick-panel messages from earlier bot versions."""
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
        logger.warning("Failed to unpin legacy panel %s in chat %s", message_id, chat_id, exc_info=True)

    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass


async def _send_group_reply_keyboard(
    bot: Bot,
    locale: Locale,
    chat_id: int,
    tags: list[Tag],
    text: str,
) -> None:
    await bot.send_message(
        chat_id,
        text,
        reply_markup=quick_tags_reply_keyboard(locale, tags),
        parse_mode="HTML",
    )


async def _send_manager_reply_keyboard(
    bot: Bot,
    locale: Locale,
    chat_id: int,
    tags: list[Tag],
    actor_user_id: int,
    *,
    reply_to_message_id: int | None = None,
) -> None:
    keyboard = quick_tags_reply_keyboard(locale, tags, show_menu_button=True, selective=True)
    text = f'<a href="tg://user?id={actor_user_id}">\u200b</a>'
    kwargs: dict = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": keyboard,
        "parse_mode": "HTML",
    }
    if reply_to_message_id is not None:
        kwargs["reply_to_message_id"] = reply_to_message_id
    try:
        message = await bot.send_message(**kwargs)
    except TelegramBadRequest:
        kwargs["text"] = locale.get("commands.quick_panel_manager_hint")
        message = await bot.send_message(**kwargs)
    try:
        await bot.delete_message(chat_id, message.message_id)
    except TelegramBadRequest:
        pass


async def _publish_reply_keyboards(
    bot: Bot,
    locale: Locale,
    chat_id: int,
    tags: list[Tag],
    text: str,
    *,
    actor_user_id: int | None = None,
    actor_can_manage: bool = False,
    reply_to_message_id: int | None = None,
) -> None:
    await _send_group_reply_keyboard(bot, locale, chat_id, tags, text)
    if actor_can_manage and actor_user_id is not None:
        await _send_manager_reply_keyboard(
            bot,
            locale,
            chat_id,
            tags,
            actor_user_id,
            reply_to_message_id=reply_to_message_id,
        )


async def send_quick_panel(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    locale: Locale,
    chat_id: int,
    *,
    updated: bool = False,
    actor_user_id: int | None = None,
    actor_can_manage: bool = False,
    reply_to_message_id: int | None = None,
) -> None:
    if not group.enable_quick_buttons:
        await bot.send_message(chat_id, locale.get("commands.quick_panel_disabled"))
        return

    tags = await list_tags(session, group.id)
    if not tags:
        await bot.send_message(chat_id, locale.get("no_tags"))
        return

    await _cleanup_legacy_pinned_panel(bot, session, group, chat_id)

    text = (
        locale.get("commands.quick_panel_updated")
        if updated
        else locale.get("commands.quick_panel_on")
    )
    await _publish_reply_keyboards(
        bot,
        locale,
        chat_id,
        tags,
        text,
        actor_user_id=actor_user_id,
        actor_can_manage=actor_can_manage,
        reply_to_message_id=reply_to_message_id,
    )


async def hide_quick_panel(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    locale: Locale,
    chat_id: int,
) -> None:
    await _cleanup_legacy_pinned_panel(bot, session, group, chat_id)
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
    *,
    actor_user_id: int | None = None,
    actor_can_manage: bool = False,
    reply_to_message_id: int | None = None,
) -> None:
    if not group.enable_quick_buttons:
        return
    tags = await list_tags(session, group.id)
    if not tags:
        await hide_quick_panel(bot, session, group, locale, chat_id)
        return

    await _publish_reply_keyboards(
        bot,
        locale,
        chat_id,
        tags,
        locale.get("commands.quick_panel_updated"),
        actor_user_id=actor_user_id,
        actor_can_manage=actor_can_manage,
        reply_to_message_id=reply_to_message_id,
    )
