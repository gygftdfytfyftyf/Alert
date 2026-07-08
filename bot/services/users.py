from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatMember
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import Group, Tag, User
from bot.services.permissions import log_change


ACTIVE_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.RESTRICTED,
}


def member_to_user_fields(member: ChatMember) -> dict:
    tg_user = member.user
    return {
        "telegram_user_id": tg_user.id,
        "username": tg_user.username,
        "first_name": tg_user.first_name or "",
        "last_name": tg_user.last_name,
        "is_active": member.status in ACTIVE_STATUSES and not tg_user.is_bot,
    }


async def upsert_user(
    session: AsyncSession,
    group_id: int,
    telegram_user_id: int,
    username: str | None,
    first_name: str,
    last_name: str | None = None,
    is_active: bool = True,
) -> User:
    result = await session.execute(
        select(User).where(
            User.group_id == group_id,
            User.telegram_user_id == telegram_user_id,
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            group_id=group_id,
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
        )
        session.add(user)
    else:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = is_active
    await session.commit()
    await session.refresh(user)
    return user


async def list_active_users(session: AsyncSession, group_id: int) -> list[User]:
    result = await session.execute(
        select(User)
        .where(User.group_id == group_id, User.is_active.is_(True))
        .order_by(User.first_name, User.username)
    )
    return list(result.scalars().all())


async def refresh_group_members(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    actor_telegram_id: int,
) -> int:
    known_result = await session.execute(select(User).where(User.group_id == group.id))
    known_users = {user.telegram_user_id: user for user in known_result.scalars().all()}
    seen_ids: set[int] = set()
    active_count = 0

    try:
        administrators = await bot.get_chat_administrators(group.telegram_group_id)
    except TelegramBadRequest as exc:
        raise exc

    for member in administrators:
        if member.user.is_bot:
            continue
        fields = member_to_user_fields(member)
        seen_ids.add(fields["telegram_user_id"])
        if fields["is_active"]:
            active_count += 1
        await upsert_user(session, group.id, **fields)

    for user in known_users.values():
        try:
            member = await bot.get_chat_member(group.telegram_group_id, user.telegram_user_id)
        except TelegramBadRequest:
            user.is_active = False
            continue
        fields = member_to_user_fields(member)
        seen_ids.add(fields["telegram_user_id"])
        if fields["is_active"]:
            active_count += 1
        await upsert_user(session, group.id, **fields)

    await session.commit()
    await log_change(session, group, actor_telegram_id, "members_refreshed")
    return active_count


async def sync_member_from_update(
    session: AsyncSession,
    group: Group,
    member: ChatMember,
) -> User | None:
    if member.user.is_bot:
        return None
    fields = member_to_user_fields(member)
    return await upsert_user(session, group.id, **fields)


async def set_tag_members(
    session: AsyncSession,
    group: Group,
    tag: Tag,
    user_ids: list[int],
    actor_telegram_id: int,
) -> Tag:
    result = await session.execute(
        select(Tag)
        .options(selectinload(Tag.members))
        .where(Tag.id == tag.id, Tag.group_id == group.id)
    )
    loaded_tag = result.scalar_one()
    if not user_ids:
        loaded_tag.members = []
    else:
        users_result = await session.execute(
            select(User).where(
                User.group_id == group.id,
                User.id.in_(user_ids),
                User.is_active.is_(True),
            )
        )
        loaded_tag.members = list(users_result.scalars().all())
    member_count = len(loaded_tag.members)
    tag_name = loaded_tag.name
    await session.commit()
    await log_change(
        session,
        group,
        actor_telegram_id,
        "members_assigned",
        f"tag={tag_name}; count={member_count}",
    )
    return loaded_tag


def format_user_mention(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    display = user.first_name or "user"
    return f'<a href="tg://user?id={user.telegram_user_id}">{display}</a>'


def format_tag_call(tag_name: str, members: list[User]) -> str:
    lines = [f"🔔 {tag_name}"]
    lines.extend(format_user_mention(member) for member in members)
    return "\n".join(lines)
