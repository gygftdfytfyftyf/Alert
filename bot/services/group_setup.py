from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Group
from bot.handlers.helpers import send_admin_panel
from bot.services.owner_access import ensure_bot_owner_in_group
from bot.services.permissions import get_user_access, is_bot_admin, is_bot_owner
from bot.services.quick_panel import send_quick_panel
from bot.services.tags import list_tags
from bot.services.users import refresh_group_members
from bot.utils.text import Locale

logger = logging.getLogger(__name__)


async def setup_group_when_ready(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    locale: Locale,
    chat_id: int,
    actor_user_id: int,
) -> None:
    """Sync members, open admin UI for managers, publish quick keys when tags exist."""
    access = await get_user_access(bot, session, group, actor_user_id)

    if await is_bot_owner(actor_user_id):
        await ensure_bot_owner_in_group(bot, session, group, actor_user_id)
        access = await get_user_access(bot, session, group, actor_user_id)

    if not await is_bot_admin(bot, chat_id):
        if access.can_manage:
            await send_admin_panel(
                bot,
                session,
                locale,
                chat_id,
                actor_user_id,
                group,
            )
        return

    try:
        await refresh_group_members(bot, session, group, actor_user_id)
    except TelegramBadRequest:
        logger.warning("Could not refresh members during group setup in chat %s", chat_id)

    if access.can_manage:
        await send_admin_panel(
            bot,
            session,
            locale,
            chat_id,
            actor_user_id,
            group,
        )

    tags = await list_tags(session, group.id)
    if group.enable_quick_buttons and tags:
        await send_quick_panel(
            bot,
            session,
            group,
            locale,
            chat_id,
            actor_user_id=actor_user_id,
            actor_can_manage=access.can_manage,
        )
