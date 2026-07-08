from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.helpers import ensure_group, is_group_chat
from bot.services.users import upsert_user
from bot.utils.text import Locale

logger = logging.getLogger(__name__)
router = Router(name="activity")


@router.message()
async def track_active_user(message: Message, session: AsyncSession, locale: Locale) -> None:
    if not is_group_chat(message) or message.from_user is None or message.from_user.is_bot:
        return
    group = await ensure_group(message, session, locale)
    if group is None:
        return
    await upsert_user(
        session,
        group.id,
        telegram_user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name or "",
        last_name=message.from_user.last_name,
        is_active=True,
    )
