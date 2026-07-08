from __future__ import annotations

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Group
from bot.keyboards.builders import main_menu_keyboard, tag_list_keyboard
from bot.services.permissions import get_or_create_group, get_user_access
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
    access = await get_user_access(bot, session, group, user_id)
    if not access.can_manage and not access.can_view_tags and not access.can_call_tags:
        text = locale.get("no_permission")
        keyboard = None
    else:
        text = (
            locale.get("commands.menu_title_manage")
            if access.can_manage
            else locale.get("commands.menu_title_call")
        )
        keyboard = main_menu_keyboard(
            locale,
            can_manage=access.can_manage,
            can_assign_editors=access.can_assign_editors,
            can_view_tags=access.can_view_tags,
            can_call_tags=access.can_call_tags,
        )

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
    edit_message_id: int | None = None,
) -> None:
    access = await get_user_access(bot, session, group, user_id)

    if not access.can_manage and not access.can_view_tags and not access.can_call_tags:
        await bot.send_message(chat_id, locale.get("no_permission"))
        return

    tags = await list_tags(session, group.id)
    if not tags:
        text = locale.get("no_tags")
        keyboard = main_menu_keyboard(
            locale,
            can_manage=access.can_manage,
            can_assign_editors=access.can_assign_editors,
            can_view_tags=access.can_view_tags,
            can_call_tags=access.can_call_tags,
        ) if (access.can_manage or access.can_call_tags or access.can_view_tags) else None
    elif access.can_manage:
        text = locale.get("commands.tags_title")
        keyboard = tag_list_keyboard(locale, tags, for_call=False)
    elif access.can_call_tags:
        text = locale.get("commands.tags_title_call")
        keyboard = tag_list_keyboard(locale, tags, for_call=True)
    else:
        names = "\n".join(f"• {tag.name}" for tag in tags)
        text = locale.get("commands.tags_title_view") + "\n\n" + names
        keyboard = None

    if edit_message_id is not None:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=edit_message_id,
            reply_markup=keyboard,
        )
    else:
        await bot.send_message(chat_id, text, reply_markup=keyboard)
