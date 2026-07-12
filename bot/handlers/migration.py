from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.group_migration import merge_groups_by_chat_id

logger = logging.getLogger(__name__)
router = Router(name="migration")


@router.message(F.migrate_to_chat_id)
async def on_group_migrated(message: Message, session: AsyncSession) -> None:
    if message.migrate_from_chat_id is None or message.migrate_to_chat_id is None:
        return
    await merge_groups_by_chat_id(
        session,
        message.migrate_from_chat_id,
        message.migrate_to_chat_id,
    )
    logger.info(
        "Handled group migration %s -> %s",
        message.migrate_from_chat_id,
        message.migrate_to_chat_id,
    )
