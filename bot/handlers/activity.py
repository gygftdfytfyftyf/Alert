from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User
from bot.handlers.helpers import ensure_group, is_group_chat
from bot.services.tag_pending import promote_pending_members
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
    result = await session.execute(
        select(User).where(
            User.group_id == group.id,
            User.telegram_user_id == message.from_user.id,
        )
    )
    user = result.scalar_one_or_none()
    if user is not None:
        await promote_pending_members(session, group, user)
