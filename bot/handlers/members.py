from __future__ import annotations

import logging

from aiogram import Router
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberUpdated
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.helpers import send_admin_panel
from bot.services.permissions import get_or_create_group, is_bot_admin
from bot.services.users import sync_member_from_update
from bot.utils.text import Locale

logger = logging.getLogger(__name__)
router = Router(name="members")


@router.my_chat_member()
async def on_bot_membership(
    update: ChatMemberUpdated,
    session: AsyncSession,
    locale: Locale,
) -> None:
    chat = update.chat
    if chat.type not in {"group", "supergroup"}:
        return

    old_status = update.old_chat_member.status
    new_status = update.new_chat_member.status
    was_outside = old_status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}
    is_inside = new_status in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR}

    if not (was_outside and is_inside):
        return

    group = await get_or_create_group(session, chat.id, chat.title or "")
    logger.info("Bot added to group %s (%s)", chat.id, chat.title)

    await update.bot.send_message(chat.id, locale.get("commands.added_to_group"))

    if await is_bot_admin(update.bot, chat.id):
        actor_id = update.from_user.id if update.from_user else 0
        if actor_id:
            await send_admin_panel(
                update.bot,
                session,
                locale,
                chat.id,
                actor_id,
                group,
            )


@router.chat_member()
async def on_chat_member(update: ChatMemberUpdated, session: AsyncSession) -> None:
    chat = update.chat
    if chat.type not in {"group", "supergroup"}:
        return
    group = await get_or_create_group(session, chat.id, chat.title or "")
    await sync_member_from_update(session, group, update.new_chat_member)
