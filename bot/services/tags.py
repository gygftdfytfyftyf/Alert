from __future__ import annotations

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import Group, Tag
from bot.services.permissions import is_chat_admin, log_change


async def list_tags(session: AsyncSession, group_id: int) -> list[Tag]:
    result = await session.execute(
        select(Tag).where(Tag.group_id == group_id).order_by(Tag.name)
    )
    return list(result.scalars().all())


async def get_tag(session: AsyncSession, group_id: int, tag_id: int) -> Tag | None:
    result = await session.execute(
        select(Tag)
        .options(selectinload(Tag.members))
        .where(Tag.group_id == group_id, Tag.id == tag_id)
    )
    return result.scalar_one_or_none()


async def create_tag(
    session: AsyncSession,
    group: Group,
    name: str,
    actor_telegram_id: int,
) -> Tag:
    tag = Tag(group_id=group.id, name=name.strip())
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    await log_change(
        session,
        group,
        actor_telegram_id,
        "tag_created",
        f"name={name.strip()}",
    )
    return tag


async def rename_tag(
    session: AsyncSession,
    group: Group,
    tag: Tag,
    new_name: str,
    actor_telegram_id: int,
) -> Tag:
    old_name = tag.name
    tag.name = new_name.strip()
    await session.commit()
    await log_change(
        session,
        group,
        actor_telegram_id,
        "tag_renamed",
        f"{old_name} -> {tag.name}",
    )
    return tag


async def delete_tag(
    session: AsyncSession,
    group: Group,
    tag: Tag,
    actor_telegram_id: int,
) -> None:
    name = tag.name
    await session.delete(tag)
    await session.commit()
    await log_change(
        session,
        group,
        actor_telegram_id,
        "tag_deleted",
        f"name={name}",
    )


async def tag_name_exists(session: AsyncSession, group_id: int, name: str, exclude_id: int | None = None) -> bool:
    query = select(Tag.id).where(Tag.group_id == group_id, Tag.name == name.strip())
    if exclude_id is not None:
        query = query.where(Tag.id != exclude_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


async def can_use_tags(bot: Bot, session: AsyncSession, group: Group, user_id: int) -> bool:
    if group.who_can_use_tags == "all":
        return True
    return await is_chat_admin(bot, group.telegram_group_id, user_id)


async def can_view_tag_list(group: Group, is_admin: bool) -> bool:
    if is_admin:
        return True
    return group.allow_tag_list_view
