from __future__ import annotations

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Group
from bot.keyboards.builders import main_menu_keyboard, tag_list_keyboard
from bot.services.group_migration import merge_groups_by_chat_id
from bot.services.permissions import get_or_create_group, get_user_access
from bot.services.quick_panel import send_quick_panel
from bot.services.tags import list_tags
from bot.utils.text import Locale


def is_group_chat(message_or_chat) -> bool:
    chat = message_or_chat.chat if hasattr(message_or_chat, "chat") else message_or_chat
    return chat.type in {"group", "supergroup"}


async def ensure_group(
    event: Message | CallbackQuery,
    session: AsyncSession,
    locale: Locale,
) -> Group | None:
    message = event if isinstance(event, Message) else event.message
    if message is None or not is_group_chat(message):
        text = locale.get("group_only")
        if isinstance(event, Message):
            await event.answer(text)
        else:
            await event.answer(text, show_alert=True)
        return None

    chat_id = message.chat.id
    if getattr(message, "migrate_from_chat_id", None):
        group = await merge_groups_by_chat_id(
            session,
            message.migrate_from_chat_id,
            chat_id,
        )
        if message.chat.title:
            group.title = message.chat.title
            await session.commit()
        return group

    return await get_or_create_group(
        session,
        telegram_group_id=chat_id,
        title=message.chat.title or "",
    )


async def send_user_interface(
    bot: Bot,
    session: AsyncSession,
    locale: Locale,
    chat_id: int,
    user_id: int,
    group: Group,
    *,
    edit_message_id: int | None = None,
) -> None:
    access = await get_user_access(bot, session, group, user_id)

    if access.can_manage:
        await send_admin_panel(
            bot,
            session,
            locale,
            chat_id,
            user_id,
            group,
            edit_message_id=edit_message_id,
        )
        return

    if edit_message_id is not None:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=edit_message_id,
                text=locale.get("commands.use_quick_buttons_only"),
                reply_markup=None,
            )
        except Exception:
            pass
        return

    if access.can_call_tags:
        await send_quick_panel(
            bot,
            session,
            group,
            locale,
            chat_id,
            clear_reply_keyboard=True,
        )
        return

    await bot.send_message(chat_id, locale.get("no_permission"))


async def send_admin_panel(
    bot: Bot,
    session: AsyncSession,
    locale: Locale,
    chat_id: int,
    user_id: int,
    group: Group,
    *,
    edit_message_id: int | None = None,
) -> None:
    access = await get_user_access(bot, session, group, user_id)
    if not access.can_manage:
        await send_user_interface(
            bot,
            session,
            locale,
            chat_id,
            user_id,
            group,
            edit_message_id=edit_message_id,
        )
        return

    text = locale.get("commands.menu_title_manage")
    keyboard = main_menu_keyboard(locale, can_assign_editors=access.can_assign_editors)

    if edit_message_id is not None:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=edit_message_id,
            reply_markup=keyboard,
        )
    else:
        await bot.send_message(chat_id, text, reply_markup=keyboard)


# Обратная совместимость для существующих импортов
send_main_menu = send_admin_panel


async def send_tag_list(
    bot: Bot,
    session: AsyncSession,
    locale: Locale,
    chat_id: int,
    user_id: int,
    group: Group,
    *,
    edit_message_id: int | None = None,
) -> None:
    access = await get_user_access(bot, session, group, user_id)
    if not access.can_manage:
        if edit_message_id is not None:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=edit_message_id,
                    text=locale.get("commands.use_quick_buttons_only"),
                    reply_markup=None,
                )
            except Exception:
                pass
        else:
            await send_user_interface(bot, session, locale, chat_id, user_id, group)
        return

    tags = await list_tags(session, group.id)
    if not tags:
        text = locale.get("no_tags")
        keyboard = main_menu_keyboard(locale, can_assign_editors=access.can_assign_editors)
    else:
        text = locale.get("commands.tags_title")
        keyboard = tag_list_keyboard(locale, tags, for_call=False)

    if edit_message_id is not None:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=edit_message_id,
            reply_markup=keyboard,
        )
    else:
        await bot.send_message(chat_id, text, reply_markup=keyboard)
