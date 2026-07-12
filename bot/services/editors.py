from __future__ import annotations

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Group, GroupEditor, User
from bot.services.permissions import is_telegram_admin, log_change


async def list_editors(session: AsyncSession, group_id: int) -> list[GroupEditor]:
    result = await session.execute(
        select(GroupEditor)
        .where(GroupEditor.group_id == group_id)
        .order_by(GroupEditor.created_at)
    )
    return list(result.scalars().all())


async def get_editor_user(session: AsyncSession, group_id: int, telegram_user_id: int) -> User | None:
    result = await session.execute(
        select(User).where(
            User.group_id == group_id,
            User.telegram_user_id == telegram_user_id,
        )
    )
    return result.scalar_one_or_none()


async def add_editor(
    session: AsyncSession,
    group: Group,
    telegram_user_id: int,
    added_by_telegram_id: int,
) -> GroupEditor:
    editor = GroupEditor(
        group_id=group.id,
        telegram_user_id=telegram_user_id,
        added_by_telegram_id=added_by_telegram_id,
    )
    session.add(editor)
    await session.commit()
    await session.refresh(editor)
    await log_change(
        session,
        group,
        added_by_telegram_id,
        "editor_added",
        f"user_id={telegram_user_id}",
    )
    return editor


async def remove_editor(
    session: AsyncSession,
    group: Group,
    telegram_user_id: int,
    removed_by_telegram_id: int,
) -> bool:
    result = await session.execute(
        select(GroupEditor).where(
            GroupEditor.group_id == group.id,
            GroupEditor.telegram_user_id == telegram_user_id,
        )
    )
    editor = result.scalar_one_or_none()
    if editor is None:
        return False
    await session.delete(editor)
    await session.commit()
    await log_change(
        session,
        group,
        removed_by_telegram_id,
        "editor_removed",
        f"user_id={telegram_user_id}",
    )
    return True


async def can_become_editor(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    telegram_user_id: int,
) -> bool:
    if await is_telegram_admin(bot, group.telegram_group_id, telegram_user_id):
        return False
    result = await session.execute(
        select(GroupEditor.id).where(
            GroupEditor.group_id == group.id,
            GroupEditor.telegram_user_id == telegram_user_id,
        )
    )
    return result.scalar_one_or_none() is None
