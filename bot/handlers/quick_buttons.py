from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.helpers import ensure_group, is_group_chat, send_main_menu
from bot.keyboards.reply import MENU_BUTTON, parse_quick_tag_text
from bot.services.permissions import can_assign_editors, get_user_access
from bot.services.quick_panel import hide_quick_panel, send_quick_panel
from bot.services.tag_invoke import invoke_tag_by_name
from bot.utils.text import Locale

logger = logging.getLogger(__name__)
router = Router(name="quick_buttons")


@router.message(Command("panel"))
async def cmd_panel(message: Message, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(message, session, locale)
    if group is None:
        return
    access = await get_user_access(message.bot, session, group, message.from_user.id)
    if not access.can_call_tags and not access.can_manage:
        await message.answer(locale.get("no_permission"))
        return
    await send_quick_panel(message.bot, session, group, locale, message.chat.id)


@router.message(Command("panel_hide"))
async def cmd_panel_hide(message: Message, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(message, session, locale)
    if group is None:
        return
    if not await can_assign_editors(message.bot, group, message.from_user.id):
        await message.answer(locale.get("no_permission"))
        return
    await hide_quick_panel(message.bot, locale, message.chat.id)


@router.message(F.text == MENU_BUTTON, StateFilter(None))
async def quick_menu_button(message: Message, session: AsyncSession, locale: Locale) -> None:
    if not is_group_chat(message):
        return
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


@router.message(F.text.startswith("📣"), StateFilter(None))
async def quick_tag_button(message: Message, session: AsyncSession, locale: Locale) -> None:
    if not is_group_chat(message) or not message.text:
        return
    group = await ensure_group(message, session, locale)
    if group is None or not group.enable_quick_buttons:
        return

    tag_name = parse_quick_tag_text(message.text)
    if not tag_name:
        return

    result = await invoke_tag_by_name(
        message.bot,
        session,
        group,
        tag_name,
        message.from_user.id,
        locale,
    )
    if result.alert:
        await message.reply(result.alert)
        return
    if result.message:
        await message.answer(result.message, disable_web_page_preview=True)
