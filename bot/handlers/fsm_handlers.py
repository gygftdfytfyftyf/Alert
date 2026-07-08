from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.helpers import ensure_group, send_main_menu
from bot.handlers.states import CreateTagState, RenameTagState
from bot.keyboards.builders import tag_detail_keyboard
from bot.services.quick_panel import refresh_quick_panel, send_quick_panel
from bot.services.tags import create_tag, get_tag, rename_tag, tag_name_exists
from bot.utils.text import Locale

logger = logging.getLogger(__name__)
router = Router(name="fsm")


@router.message(CreateTagState.waiting_name, F.text)
async def create_tag_name(message: Message, state: FSMContext, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(message, session, locale)
    if group is None:
        return
    name = message.text or ""
    if not name.strip() or len(name.strip()) > 100:
        await message.answer(locale.get("commands.invalid_tag_name"))
        return
    if await tag_name_exists(session, group.id, name):
        await message.answer(locale.get("commands.tag_exists"))
        return
    tag = await create_tag(session, group, name, message.from_user.id)
    data = await state.get_data()
    await state.clear()
    await message.answer(locale.get("commands.tag_created", name=tag.name))
    if group.enable_quick_buttons:
        await send_quick_panel(message.bot, session, group, locale, message.chat.id, updated=True)
    menu_message_id = data.get("menu_message_id")
    if menu_message_id:
        await message.bot.edit_message_text(
            f"<b>{tag.name}</b>",
            chat_id=message.chat.id,
            message_id=menu_message_id,
            reply_markup=tag_detail_keyboard(locale, tag.id),
        )
    else:
        await send_main_menu(
            message.bot,
            session,
            locale,
            message.chat.id,
            message.from_user.id,
            group,
        )


@router.message(RenameTagState.waiting_name, F.text)
async def rename_tag_name(message: Message, state: FSMContext, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(message, session, locale)
    if group is None:
        return
    data = await state.get_data()
    tag_id = data.get("tag_id")
    if tag_id is None:
        await state.clear()
        return
    name = message.text or ""
    if not name.strip() or len(name.strip()) > 100:
        await message.answer(locale.get("commands.invalid_tag_name"))
        return
    if await tag_name_exists(session, group.id, name, exclude_id=tag_id):
        await message.answer(locale.get("commands.tag_exists"))
        return
    tag = await get_tag(session, group.id, tag_id)
    if tag is None:
        await message.answer(locale.get("commands.tag_not_found"))
        await state.clear()
        return
    tag = await rename_tag(session, group, tag, name, message.from_user.id)
    await state.clear()
    await message.answer(locale.get("commands.tag_renamed", name=tag.name))
    await refresh_quick_panel(message.bot, session, group, locale, message.chat.id)
    menu_message_id = data.get("menu_message_id")
    if menu_message_id:
        await message.bot.edit_message_text(
            f"<b>{tag.name}</b>",
            chat_id=message.chat.id,
            message_id=menu_message_id,
            reply_markup=tag_detail_keyboard(locale, tag.id),
        )
