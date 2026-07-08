from __future__ import annotations

import logging

from aiogram import Router
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberUpdated
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.group_setup import setup_group_when_ready
from bot.services.permissions import get_or_create_group
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
    promoted_to_admin = (
        old_status == ChatMemberStatus.MEMBER
        and new_status == ChatMemberStatus.ADMINISTRATOR
    )

    if not ((was_outside and is_inside) or promoted_to_admin):
        return

    group = await get_or_create_group(session, chat.id, chat.title or "")
    actor_id = update.from_user.id if update.from_user else 0
    logger.info("Bot ready in group %s (%s), promoted=%s", chat.id, chat.title, promoted_to_admin)

    if was_outside and is_inside:
        await update.bot.send_message(chat.id, locale.get("commands.added_to_group"))

    if actor_id:
        await setup_group_when_ready(
            update.bot,
            session,
            group,
            locale,
            chat.id,
            actor_id,
        )


@router.chat_member()
async def on_chat_member(update: ChatMemberUpdated, session: AsyncSession, locale: Locale) -> None:
    chat = update.chat
    if chat.type not in {"group", "supergroup"}:
        return

    group = await get_or_create_group(session, chat.id, chat.title or "")
    actor_id = update.from_user.id if update.from_user else 0
    await sync_member_from_update(
        session,
        group,
        update.new_chat_member,
        actor_telegram_id=actor_id,
    )

    new_status = update.new_chat_member.status
    joined = new_status in {
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
        ChatMemberStatus.RESTRICTED,
    }
    if joined and update.new_chat_member.user and not update.new_chat_member.user.is_bot:
        logger.info(
            "Member joined group %s: user=%s",
            chat.id,
            update.new_chat_member.user.id,
        )
