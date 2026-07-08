from __future__ import annotations

import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import ChangeLog, Group, GroupEditor, Tag, User

logger = logging.getLogger(__name__)


async def merge_groups_by_chat_id(
    session: AsyncSession,
    old_chat_id: int,
    new_chat_id: int,
) -> Group:
    old_group = (
        await session.execute(select(Group).where(Group.telegram_group_id == old_chat_id))
    ).scalar_one_or_none()
    new_group = (
        await session.execute(select(Group).where(Group.telegram_group_id == new_chat_id))
    ).scalar_one_or_none()

    if old_group is None:
        if new_group is None:
            new_group = Group(telegram_group_id=new_chat_id)
            session.add(new_group)
            await session.commit()
            await session.refresh(new_group)
        return new_group

    if new_group is None:
        old_group.telegram_group_id = new_chat_id
        await session.commit()
        await session.refresh(old_group)
        logger.info("Migrated group %s -> %s", old_chat_id, new_chat_id)
        return old_group

    if old_group.id == new_group.id:
        return new_group

    await _move_group_children(session, old_group.id, new_group.id)
    await session.delete(old_group)
    await session.commit()
    await session.refresh(new_group)
    logger.info("Merged group %s into %s (chat %s -> %s)", old_group.id, new_group.id, old_chat_id, new_chat_id)
    return new_group


async def _move_group_children(session: AsyncSession, source_id: int, target_id: int) -> None:
    for tag in (await session.execute(select(Tag).where(Tag.group_id == source_id))).scalars():
        tag.group_id = target_id

    for user in (await session.execute(select(User).where(User.group_id == source_id))).scalars():
        existing = (
            await session.execute(
                select(User).where(
                    User.group_id == target_id,
                    User.telegram_user_id == user.telegram_user_id,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            user.group_id = target_id
        else:
            await session.delete(user)

    for editor in (await session.execute(select(GroupEditor).where(GroupEditor.group_id == source_id))).scalars():
        existing = (
            await session.execute(
                select(GroupEditor).where(
                    GroupEditor.group_id == target_id,
                    GroupEditor.telegram_user_id == editor.telegram_user_id,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            editor.group_id = target_id
        else:
            await session.delete(editor)

    await session.execute(
        update(ChangeLog).where(ChangeLog.group_id == source_id).values(group_id=target_id)
    )
