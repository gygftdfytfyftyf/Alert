from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatMember, User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import ChangeLog, Group


ADMIN_STATUSES = {
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.ADMINISTRATOR,
}


async def is_chat_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except TelegramBadRequest:
        return False
    return member.status in ADMIN_STATUSES


async def is_bot_admin(bot: Bot, chat_id: int) -> bool:
    me = await bot.get_me()
    return await is_chat_admin(bot, chat_id, me.id)


async def get_or_create_group(
    session: AsyncSession,
    telegram_group_id: int,
    title: str = "",
) -> Group:
    result = await session.execute(
        select(Group).where(Group.telegram_group_id == telegram_group_id)
    )
    group = result.scalar_one_or_none()
    if group is None:
        group = Group(telegram_group_id=telegram_group_id, title=title)
        session.add(group)
        await session.commit()
        await session.refresh(group)
    elif title and group.title != title:
        group.title = title
        await session.commit()
    return group


async def update_group_title(session: AsyncSession, group: Group, title: str) -> None:
    if group.title != title:
        group.title = title
        await session.commit()


async def log_change(
    session: AsyncSession,
    group: Group,
    actor_telegram_id: int,
    action: str,
    details: str = "",
) -> None:
    if not group.enable_change_log:
        return
    session.add(
        ChangeLog(
            group_id=group.id,
            actor_telegram_id=actor_telegram_id,
            action=action,
            details=details,
        )
    )
    await session.commit()
