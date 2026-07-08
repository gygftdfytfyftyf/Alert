from __future__ import annotations

import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramMigrateToChat
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.database.models import Group, GroupEditor

logger = logging.getLogger(__name__)

ADMIN_STATUSES = {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}


@dataclass(frozen=True)
class UserAccess:
    is_telegram_admin: bool
    is_delegated_editor: bool
    can_manage: bool
    can_assign_editors: bool
    can_view_tags: bool
    can_call_tags: bool


async def is_bot_owner(user_id: int) -> bool:
    return user_id in get_settings().owner_ids


async def is_telegram_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status in ADMIN_STATUSES:
            return True
    except TelegramMigrateToChat as exc:
        return await is_telegram_admin(bot, exc.migrate_to_chat_id, user_id)
    except TelegramBadRequest as exc:
        logger.warning("get_chat_member failed for user %s in chat %s: %s", user_id, chat_id, exc)

    try:
        administrators = await bot.get_chat_administrators(chat_id)
        return any(
            admin.user.id == user_id and admin.status in ADMIN_STATUSES
            for admin in administrators
        )
    except TelegramMigrateToChat as exc:
        return await is_telegram_admin(bot, exc.migrate_to_chat_id, user_id)
    except TelegramBadRequest as exc:
        logger.warning("get_chat_administrators failed for chat %s: %s", chat_id, exc)
        return False


is_chat_admin = is_telegram_admin


async def is_delegated_editor(session: AsyncSession, group_id: int, user_id: int) -> bool:
    result = await session.execute(
        select(GroupEditor.id).where(
            GroupEditor.group_id == group_id,
            GroupEditor.telegram_user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def can_manage_tags(bot: Bot, session: AsyncSession, group: Group, user_id: int) -> bool:
    if await is_bot_owner(user_id):
        return True
    if await is_telegram_admin(bot, group.telegram_group_id, user_id):
        return True
    return await is_delegated_editor(session, group.id, user_id)


async def can_assign_editors(bot: Bot, group: Group, user_id: int) -> bool:
    if await is_bot_owner(user_id):
        return True
    return await is_telegram_admin(bot, group.telegram_group_id, user_id)


async def get_user_access(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    user_id: int,
) -> UserAccess:
    tg_admin = await is_telegram_admin(bot, group.telegram_group_id, user_id)
    owner = await is_bot_owner(user_id)
    editor = await is_delegated_editor(session, group.id, user_id)
    can_manage = owner or tg_admin or editor
    can_view = can_manage or group.allow_tag_list_view
    can_call = can_manage
    if not can_call:
        if group.who_can_use_tags == "all":
            can_call = True
        elif group.who_can_use_tags == "admins" and tg_admin:
            can_call = True
    return UserAccess(
        is_telegram_admin=tg_admin,
        is_delegated_editor=editor,
        can_manage=can_manage,
        can_assign_editors=owner or tg_admin,
        can_view_tags=can_view,
        can_call_tags=can_call,
    )


async def is_bot_admin(bot: Bot, chat_id: int) -> bool:
    me = await bot.get_me()
    return await is_telegram_admin(bot, chat_id, me.id)


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
    from bot.database.models import ChangeLog

    session.add(
        ChangeLog(
            group_id=group.id,
            actor_telegram_id=actor_telegram_id,
            action=action,
            details=details,
        )
    )
    await session.commit()
