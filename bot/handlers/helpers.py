from __future__ import annotations

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Group
from bot.keyboards.builders import main_menu_keyboard, tag_list_keyboard
from bot.services.permissions import get_or_create_group, is_chat_admin
from bot.services.tags import can_use_tags, can_view_tag_list, list_tags
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

    group = await get_or_create_group(
        session,
        telegram_group_id=message.chat.id,
        title=message.chat.title or "",
    )
    return group


async def send_main_menu(
    bot: Bot,
    session: AsyncSession,
    locale: Locale,
    chat_id: int,
    user_id: int,
    group: Group,
    *,
    edit_message_id: int | None = None,
) -> None:
    is_admin = await is_chat_admin(bot, group.telegram_group_id, user_id)
    can_view = await can_view_tag_list(group, is_admin)
    can_call = is_admin or await can_use_tags(bot, session, group, user_id)
    text = locale.get("commands.menu_title")
    keyboard = main_menu_keyboard(locale, is_admin, can_view, can_call)

    if edit_message_id is not None:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=edit_message_id,
            reply_markup=keyboard,
        )
    else:
        await bot.send_message(chat_id, text, reply_markup=keyboard)


async def send_tag_list(
    bot: Bot,
    session: AsyncSession,
    locale: Locale,
    chat_id: int,
    user_id: int,
    group: Group,
    *,
    for_call: bool = False,
    edit_message_id: int | None = None,
) -> None:
    is_admin = await is_chat_admin(bot, group.telegram_group_id, user_id)
    can_view = await can_view_tag_list(group, is_admin)

    if not can_view and not for_call:
        await bot.send_message(chat_id, locale.get("no_permission"))
        return

    if for_call and not await can_use_tags(bot, session, group, user_id) and not is_admin:
        await bot.send_message(chat_id, locale.get("no_permission"))
        return

    tags = await list_tags(session, group.id)
    if not tags:
        text = locale.get("no_tags")
        can_call = is_admin or await can_use_tags(bot, session, group, user_id)
        keyboard = main_menu_keyboard(locale, is_admin, can_view, can_call)
    else:
        text = locale.get("commands.tags_title")
        keyboard = tag_list_keyboard(locale, tags, is_admin=is_admin, for_call=for_call)

    if edit_message_id is not None:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=edit_message_id,
            reply_markup=keyboard,
        )
    else:
        await bot.send_message(chat_id, text, reply_markup=keyboard)
