from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import ChangeLog, Group
from bot.handlers.helpers import ensure_group, send_main_menu, send_tag_list
from bot.handlers.states import AssignMembersState, CreateTagState, RenameTagState
from bot.keyboards.builders import (
    assign_members_keyboard,
    cancel_keyboard,
    settings_keyboard,
    tag_detail_keyboard,
)
from bot.keyboards.inline import AssignCB, CallTagCB, MenuCB, SettingsCB, TagCB
from bot.services.permissions import is_bot_admin, is_chat_admin, log_change
from bot.services.quick_panel import refresh_quick_panel, send_quick_panel
from bot.services.tag_invoke import invoke_tag
from bot.services.tags import (
    can_use_tags,
    delete_tag,
    get_tag,
    rename_tag,
    tag_name_exists,
)
from bot.services.users import (
    format_tag_call,
    format_user_mention,
    list_active_users,
    refresh_group_members,
    set_tag_members,
)
from bot.utils.text import Locale

logger = logging.getLogger(__name__)
router = Router(name="callbacks")


@router.callback_query(MenuCB.filter(F.action == "main"))
async def menu_main(callback: CallbackQuery, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    await send_main_menu(
        callback.bot,
        session,
        locale,
        callback.message.chat.id,
        callback.from_user.id,
        group,
        edit_message_id=callback.message.message_id,
    )
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "tag_list"))
async def menu_tag_list(callback: CallbackQuery, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    is_admin = await is_chat_admin(callback.bot, group.telegram_group_id, callback.from_user.id)
    await send_tag_list(
        callback.bot,
        session,
        locale,
        callback.message.chat.id,
        callback.from_user.id,
        group,
        for_call=not is_admin,
        edit_message_id=callback.message.message_id,
    )
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "create_tag"))
async def menu_create_tag(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    locale: Locale,
) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    if not await is_chat_admin(callback.bot, group.telegram_group_id, callback.from_user.id):
        await callback.answer(locale.get("no_permission"), show_alert=True)
        return
    await state.set_state(CreateTagState.waiting_name)
    await state.update_data(group_id=group.id, menu_message_id=callback.message.message_id)
    await callback.message.edit_text(
        locale.get("commands.enter_tag_name"),
        reply_markup=cancel_keyboard(locale),
    )
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "settings"))
async def menu_settings(callback: CallbackQuery, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    if not await is_chat_admin(callback.bot, group.telegram_group_id, callback.from_user.id):
        await callback.answer(locale.get("no_permission"), show_alert=True)
        return
    await callback.message.edit_text(
        locale.get("commands.settings_title"),
        reply_markup=settings_keyboard(locale, group),
    )
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "refresh_members"))
async def menu_refresh_members(callback: CallbackQuery, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    if not await is_chat_admin(callback.bot, group.telegram_group_id, callback.from_user.id):
        await callback.answer(locale.get("no_permission"), show_alert=True)
        return
    if not await is_bot_admin(callback.bot, group.telegram_group_id):
        await callback.answer(locale.get("bot_not_admin"), show_alert=True)
        return
    try:
        count = await refresh_group_members(
            callback.bot,
            session,
            group,
            callback.from_user.id,
        )
    except Exception:
        logger.exception("Failed to refresh members")
        await callback.answer(locale.get("error_generic"), show_alert=True)
        return
    await callback.answer(locale.get("commands.members_updated", count=count), show_alert=True)


@router.callback_query(MenuCB.filter(F.action == "quick_panel"))
async def menu_quick_panel(callback: CallbackQuery, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    is_admin = await is_chat_admin(callback.bot, group.telegram_group_id, callback.from_user.id)
    if not is_admin and not await can_use_tags(callback.bot, session, group, callback.from_user.id):
        await callback.answer(locale.get("no_permission"), show_alert=True)
        return
    await send_quick_panel(callback.bot, session, group, locale, callback.message.chat.id)
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "cancel"))
async def menu_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession, locale: Locale) -> None:
    await state.clear()
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    await send_main_menu(
        callback.bot,
        session,
        locale,
        callback.message.chat.id,
        callback.from_user.id,
        group,
        edit_message_id=callback.message.message_id,
    )
    await callback.answer(locale.get("commands.operation_cancelled"))


@router.callback_query(TagCB.filter(F.action == "open"))
async def tag_open(callback: CallbackQuery, callback_data: TagCB, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    if not await is_chat_admin(callback.bot, group.telegram_group_id, callback.from_user.id):
        await callback.answer(locale.get("no_permission"), show_alert=True)
        return
    tag = await get_tag(session, group.id, callback_data.tag_id)
    if tag is None:
        await callback.answer(locale.get("commands.tag_not_found"), show_alert=True)
        return
    await callback.message.edit_text(
        f"<b>{tag.name}</b>",
        reply_markup=tag_detail_keyboard(locale, tag.id),
    )
    await callback.answer()


@router.callback_query(TagCB.filter(F.action == "rename"))
async def tag_rename_start(
    callback: CallbackQuery,
    callback_data: TagCB,
    state: FSMContext,
    session: AsyncSession,
    locale: Locale,
) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    if not await is_chat_admin(callback.bot, group.telegram_group_id, callback.from_user.id):
        await callback.answer(locale.get("no_permission"), show_alert=True)
        return
    tag = await get_tag(session, group.id, callback_data.tag_id)
    if tag is None:
        await callback.answer(locale.get("commands.tag_not_found"), show_alert=True)
        return
    await state.set_state(RenameTagState.waiting_name)
    await state.update_data(
        group_id=group.id,
        tag_id=tag.id,
        menu_message_id=callback.message.message_id,
    )
    await callback.message.edit_text(
        locale.get("commands.enter_new_tag_name"),
        reply_markup=cancel_keyboard(locale),
    )
    await callback.answer()


@router.callback_query(TagCB.filter(F.action == "delete"))
async def tag_delete(callback: CallbackQuery, callback_data: TagCB, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    if not await is_chat_admin(callback.bot, group.telegram_group_id, callback.from_user.id):
        await callback.answer(locale.get("no_permission"), show_alert=True)
        return
    tag = await get_tag(session, group.id, callback_data.tag_id)
    if tag is None:
        await callback.answer(locale.get("commands.tag_not_found"), show_alert=True)
        return
    name = tag.name
    await delete_tag(session, group, tag, callback.from_user.id)
    await callback.answer(locale.get("commands.tag_deleted", name=name))
    await refresh_quick_panel(callback.bot, session, group, locale, callback.message.chat.id)
    await send_tag_list(
        callback.bot,
        session,
        locale,
        callback.message.chat.id,
        callback.from_user.id,
        group,
        edit_message_id=callback.message.message_id,
    )


@router.callback_query(TagCB.filter(F.action == "view_members"))
async def tag_view_members(
    callback: CallbackQuery,
    callback_data: TagCB,
    session: AsyncSession,
    locale: Locale,
) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    if not await is_chat_admin(callback.bot, group.telegram_group_id, callback.from_user.id):
        await callback.answer(locale.get("no_permission"), show_alert=True)
        return
    tag = await get_tag(session, group.id, callback_data.tag_id)
    if tag is None:
        await callback.answer(locale.get("commands.tag_not_found"), show_alert=True)
        return
    if not tag.members:
        text = locale.get("commands.tag_empty", name=tag.name)
    else:
        members = "\n".join(format_user_mention(member) for member in tag.members if member.is_active)
        text = locale.get("commands.members_title", name=tag.name) + "\n\n" + members
    await callback.message.edit_text(text, reply_markup=tag_detail_keyboard(locale, tag.id))
    await callback.answer()


@router.callback_query(TagCB.filter(F.action == "assign"))
async def tag_assign_start(
    callback: CallbackQuery,
    callback_data: TagCB,
    state: FSMContext,
    session: AsyncSession,
    locale: Locale,
) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    if not await is_chat_admin(callback.bot, group.telegram_group_id, callback.from_user.id):
        await callback.answer(locale.get("no_permission"), show_alert=True)
        return
    tag = await get_tag(session, group.id, callback_data.tag_id)
    if tag is None:
        await callback.answer(locale.get("commands.tag_not_found"), show_alert=True)
        return
    selected_ids = {member.id for member in tag.members if member.is_active}
    users = await list_active_users(session, group.id)
    await state.set_state(AssignMembersState.selecting)
    await state.update_data(
        group_id=group.id,
        tag_id=tag.id,
        selected_ids=list(selected_ids),
        page=0,
        menu_message_id=callback.message.message_id,
    )
    await callback.message.edit_text(
        locale.get("buttons.assign_members") + f": <b>{tag.name}</b>",
        reply_markup=assign_members_keyboard(locale, tag.id, users, selected_ids, page=0),
    )
    await callback.answer()


@router.callback_query(AssignCB.filter(F.action == "toggle"))
async def assign_toggle(
    callback: CallbackQuery,
    callback_data: AssignCB,
    state: FSMContext,
    session: AsyncSession,
    locale: Locale,
) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    data = await state.get_data()
    selected_ids = set(data.get("selected_ids", []))
    if callback_data.user_id in selected_ids:
        selected_ids.remove(callback_data.user_id)
    else:
        selected_ids.add(callback_data.user_id)
    await state.update_data(selected_ids=list(selected_ids), page=callback_data.page)
    users = await list_active_users(session, group.id)
    await callback.message.edit_reply_markup(
        reply_markup=assign_members_keyboard(
            locale,
            callback_data.tag_id,
            users,
            selected_ids,
            page=callback_data.page,
        )
    )
    await callback.answer()


@router.callback_query(AssignCB.filter(F.action == "page"))
async def assign_page(
    callback: CallbackQuery,
    callback_data: AssignCB,
    state: FSMContext,
    session: AsyncSession,
    locale: Locale,
) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    data = await state.get_data()
    selected_ids = set(data.get("selected_ids", []))
    await state.update_data(page=callback_data.page)
    users = await list_active_users(session, group.id)
    await callback.message.edit_reply_markup(
        reply_markup=assign_members_keyboard(
            locale,
            callback_data.tag_id,
            users,
            selected_ids,
            page=callback_data.page,
        )
    )
    await callback.answer()


@router.callback_query(AssignCB.filter(F.action == "save"))
async def assign_save(
    callback: CallbackQuery,
    callback_data: AssignCB,
    state: FSMContext,
    session: AsyncSession,
    locale: Locale,
) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    if not await is_chat_admin(callback.bot, group.telegram_group_id, callback.from_user.id):
        await callback.answer(locale.get("no_permission"), show_alert=True)
        return
    tag = await get_tag(session, group.id, callback_data.tag_id)
    if tag is None:
        await callback.answer(locale.get("commands.tag_not_found"), show_alert=True)
        return
    data = await state.get_data()
    selected_ids = list(data.get("selected_ids", []))
    await set_tag_members(session, group, tag, selected_ids, callback.from_user.id)
    await state.clear()
    await callback.answer(locale.get("commands.members_saved", name=tag.name))
    tag = await get_tag(session, group.id, tag.id)
    await callback.message.edit_text(
        f"<b>{tag.name}</b>",
        reply_markup=tag_detail_keyboard(locale, tag.id),
    )
    await refresh_quick_panel(callback.bot, session, group, locale, callback.message.chat.id)


@router.callback_query(CallTagCB.filter())
async def call_tag(callback: CallbackQuery, callback_data: CallTagCB, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    tag = await get_tag(session, group.id, callback_data.tag_id)
    if tag is None:
        await callback.answer(locale.get("commands.tag_not_found"), show_alert=True)
        return
    result = await invoke_tag(
        callback.bot,
        session,
        group,
        tag,
        callback.from_user.id,
        locale,
    )
    if result.alert:
        await callback.answer(result.alert, show_alert=True)
        if result.deleted_empty_tag:
            await refresh_quick_panel(callback.bot, session, group, locale, callback.message.chat.id)
        return
    if result.message:
        await callback.message.answer(result.message, parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(SettingsCB.filter(F.action == "toggle"))
async def settings_toggle(
    callback: CallbackQuery,
    callback_data: SettingsCB,
    session: AsyncSession,
    locale: Locale,
) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    if not await is_chat_admin(callback.bot, group.telegram_group_id, callback.from_user.id):
        await callback.answer(locale.get("no_permission"), show_alert=True)
        return
    key = callback_data.key
    if key == "who_can_use_tags":
        group.who_can_use_tags = "admins" if group.who_can_use_tags == "all" else "all"
    elif key == "allow_tag_list_view":
        group.allow_tag_list_view = not group.allow_tag_list_view
    elif key == "auto_delete_empty_tags":
        group.auto_delete_empty_tags = not group.auto_delete_empty_tags
    elif key == "enable_change_log":
        group.enable_change_log = not group.enable_change_log
    elif key == "enable_quick_buttons":
        group.enable_quick_buttons = not group.enable_quick_buttons
    else:
        await callback.answer()
        return
    await session.commit()
    await log_change(
        session,
        group,
        callback.from_user.id,
        "setting_changed",
        f"{key}={getattr(group, key)}",
    )
    await callback.message.edit_text(
        locale.get("commands.settings_title"),
        reply_markup=settings_keyboard(locale, group),
    )
    await callback.answer(locale.get("commands.settings_updated"))


@router.callback_query(SettingsCB.filter(F.action == "view_log"))
async def settings_view_log(callback: CallbackQuery, session: AsyncSession, locale: Locale) -> None:
    group = await ensure_group(callback, session, locale)
    if group is None:
        return
    if not await is_chat_admin(callback.bot, group.telegram_group_id, callback.from_user.id):
        await callback.answer(locale.get("no_permission"), show_alert=True)
        return
    result = await session.execute(
        select(ChangeLog)
        .where(ChangeLog.group_id == group.id)
        .order_by(ChangeLog.created_at.desc())
        .limit(20)
    )
    logs = list(result.scalars().all())
    if not logs:
        text = locale.get("commands.change_log_empty")
    else:
        lines = [locale.get("commands.change_log_title"), ""]
        for entry in logs:
            timestamp = entry.created_at.strftime("%d.%m.%Y %H:%M")
            lines.append(f"{timestamp} — {entry.action}: {entry.details}")
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=settings_keyboard(locale, group))
    await callback.answer()
