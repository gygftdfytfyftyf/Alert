from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import Group, Tag, TagPendingMember, User


@dataclass(frozen=True)
class PendingMemberSpec:
    telegram_user_id: int | None
    username: str | None
    label: str


def format_pending_mention(pending: TagPendingMember) -> str:
    if pending.username:
        return f"@{pending.username.lstrip('@')}"
    if pending.telegram_user_id:
        label = pending.label or str(pending.telegram_user_id)
        return f'<a href="tg://user?id={pending.telegram_user_id}">{label}</a>'
    return pending.label or "?"


async def upsert_pending_member(
    session: AsyncSession,
    tag_id: int,
    spec: PendingMemberSpec,
) -> TagPendingMember:
    username = spec.username.lstrip("@") if spec.username else None
    query = select(TagPendingMember).where(TagPendingMember.tag_id == tag_id)
    if spec.telegram_user_id is not None:
        query = query.where(TagPendingMember.telegram_user_id == spec.telegram_user_id)
    elif username:
        query = query.where(func.lower(TagPendingMember.username) == username.lower())
    else:
        query = query.where(TagPendingMember.label == spec.label)

    existing = (await session.execute(query)).scalar_one_or_none()
    if existing is not None:
        existing.label = spec.label
        if username:
            existing.username = username
        if spec.telegram_user_id is not None:
            existing.telegram_user_id = spec.telegram_user_id
        await session.commit()
        await session.refresh(existing)
        return existing

    pending = TagPendingMember(
        tag_id=tag_id,
        telegram_user_id=spec.telegram_user_id,
        username=username,
        label=spec.label,
    )
    session.add(pending)
    await session.commit()
    await session.refresh(pending)
    return pending


async def promote_pending_members(
    session: AsyncSession,
    group: Group,
    user: User,
) -> int:
    if not user.is_active:
        return 0

    conditions = []
    if user.telegram_user_id:
        conditions.append(TagPendingMember.telegram_user_id == user.telegram_user_id)
    if user.username:
        conditions.append(func.lower(TagPendingMember.username) == user.username.lower())
    if not conditions:
        return 0

    result = await session.execute(
        select(TagPendingMember)
        .join(Tag, Tag.id == TagPendingMember.tag_id)
        .options(selectinload(TagPendingMember.tag).selectinload(Tag.members))
        .where(Tag.group_id == group.id, or_(*conditions))
    )
    promoted = 0
    for pending in result.scalars().all():
        tag = pending.tag
        if not any(member.id == user.id for member in tag.members):
            tag.members.append(user)
            promoted += 1
        await session.delete(pending)
    await session.commit()
    return promoted
