from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.helpers import ensure_group, send_admin_panel
from bot.handlers.states import AssignMembersState, CreateTagState, RenameTagState
from bot.keyboards.builders import assign_members_keyboard, tag_detail_keyboard
from bot.services.member_resolve import resolve_member_tokens
from bot.services.quick_panel import refresh_quick_panel, send_quick_panel
from bot.services.tag_pending import upsert_pending_member
from bot.services.tags import create_tag, get_tag, rename_tag, tag_name_exists
from bot.services.users import list_active_users
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
        await send_quick_panel(
            message.bot,
            session,
            group,
            locale,
            message.chat.id,
            updated=True,
            actor_user_id=message.from_user.id,
            actor_can_manage=True,
            reply_to_message_id=message.message_id,
        )
    menu_message_id = data.get("menu_message_id")
    if menu_message_id:
        await message.bot.edit_message_text(
            f"<b>{tag.name}</b>",
            chat_id=message.chat.id,
            message_id=menu_message_id,
            reply_markup=tag_detail_keyboard(locale, tag.id),
        )
    else:
        await send_admin_panel(
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
    await refresh_quick_panel(
        message.bot,
        session,
        group,
        locale,
        message.chat.id,
        actor_user_id=message.from_user.id,
        actor_can_manage=True,
        reply_to_message_id=message.message_id,
    )
    menu_message_id = data.get("menu_message_id")
    if menu_message_id:
        await message.bot.edit_message_text(
            f"<b>{tag.name}</b>",
            chat_id=message.chat.id,
            message_id=menu_message_id,
            reply_markup=tag_detail_keyboard(locale, tag.id),
        )


@router.message(AssignMembersState.waiting_manual, F.text)
async def assign_members_manual(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    locale: Locale,
) -> None:
    group = await ensure_group(message, session, locale)
    if group is None:
        return
    data = await state.get_data()
    tag_id = data.get("tag_id")
    menu_message_id = data.get("menu_message_id")
    if tag_id is None:
        await state.clear()
        return

    added, pending_specs, failed = await resolve_member_tokens(
        message.bot,
        session,
        group,
        message.chat.id,
        message.text or "",
    )
    selected_ids = set(data.get("selected_ids", []))
    for user in added:
        selected_ids.add(user.id)
    for spec in pending_specs:
        await upsert_pending_member(session, tag_id, spec)
    await state.update_data(selected_ids=list(selected_ids))

    lines: list[str] = []
    if added:
        labels = ", ".join(user.first_name or user.username or str(user.telegram_user_id) for user in added)
        lines.append(locale.get("commands.members_manual_added", count=len(added), names=labels))
    if pending_specs:
        labels = ", ".join(spec.label for spec in pending_specs)
        lines.append(locale.get("commands.members_manual_pending", count=len(pending_specs), names=labels))
    if failed:
        details = []
        for token, reason in failed:
            reason_text = locale.get(f"commands.members_manual_error_{reason}", token=token)
            details.append(f"• {token}: {reason_text}")
        lines.append(locale.get("commands.members_manual_failed", count=len(failed)))
        lines.extend(details)
    if not lines:
        await message.answer(locale.get("commands.members_manual_none"))
    else:
        await message.answer("\n".join(lines))

    if menu_message_id:
        tag = await get_tag(session, group.id, tag_id)
        if tag is not None:
            users = await list_active_users(session, group.id)
            page = int(data.get("page", 0))
            await state.set_state(AssignMembersState.selecting)
            await message.bot.edit_message_text(
                locale.get("buttons.assign_members") + f": <b>{tag.name}</b>",
                chat_id=message.chat.id,
                message_id=menu_message_id,
                reply_markup=assign_members_keyboard(
                    locale,
                    tag_id,
                    users,
                    selected_ids,
                    page=page,
                ),
            )
