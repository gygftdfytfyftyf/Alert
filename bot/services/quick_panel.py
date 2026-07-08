from __future__ import annotations

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Group
from bot.keyboards.reply_builders import quick_tags_reply_keyboard, remove_reply_keyboard
from bot.services.tags import list_tags
from bot.utils.text import Locale


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

    # Сбрасываем старую клавиатуру (в т.ч. с кнопкой «Меню»)
    await bot.send_message(
        chat_id,
        locale.get("commands.quick_panel_refresh"),
        reply_markup=remove_reply_keyboard(),
    )
    await bot.send_message(
        chat_id,
        text,
        reply_markup=quick_tags_reply_keyboard(locale, tags),
    )


async def hide_quick_panel(bot: Bot, locale: Locale, chat_id: int) -> None:
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
        return
    await send_quick_panel(bot, session, group, locale, chat_id, updated=True)
