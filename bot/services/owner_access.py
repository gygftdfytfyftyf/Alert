from __future__ import annotations

import logging

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Group, GroupEditor
from bot.services.editors import add_editor

logger = logging.getLogger(__name__)


async def ensure_bot_owner_in_group(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    user_id: int,
) -> bool:
    """Register bot owner as delegated editor when they are not a Telegram admin."""
    from bot.services.permissions import is_bot_owner, is_telegram_admin

    if not await is_bot_owner(user_id):
        return False
    if await is_telegram_admin(bot, group.telegram_group_id, user_id):
        return False

    result = await session.execute(
        select(GroupEditor.id).where(
            GroupEditor.group_id == group.id,
            GroupEditor.telegram_user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is not None:
        return False

    await add_editor(session, group, user_id, user_id)
    logger.info("Auto-registered bot owner %s as editor in group %s", user_id, group.telegram_group_id)
    return True
