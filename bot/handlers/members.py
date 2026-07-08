from __future__ import annotations

import logging

from aiogram import Router
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberUpdated
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.permissions import get_or_create_group
from bot.services.users import sync_member_from_update

logger = logging.getLogger(__name__)
router = Router(name="members")


@router.my_chat_member()
async def on_bot_membership(update: ChatMemberUpdated, session: AsyncSession) -> None:
    chat = update.chat
    if chat.type not in {"group", "supergroup"}:
        return
    new_status = update.new_chat_member.status
    if new_status in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR}:
        await get_or_create_group(session, chat.id, chat.title or "")
        logger.info("Bot added to group %s", chat.id)


@router.chat_member()
async def on_chat_member(update: ChatMemberUpdated, session: AsyncSession) -> None:
    chat = update.chat
    if chat.type not in {"group", "supergroup"}:
        return
    group = await get_or_create_group(session, chat.id, chat.title or "")
    await sync_member_from_update(session, group, update.new_chat_member)
