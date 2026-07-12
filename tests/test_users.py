from __future__ import annotations

import pytest
from sqlalchemy import select

from bot.database.models import Group, Tag, User
from bot.services.users import (
    deactivate_user_and_prune_tags,
    set_tag_members,
    sync_member_from_update,
    upsert_user,
)


class FakeUser:
    def __init__(self, user_id: int, *, is_bot: bool = False, username: str = "u") -> None:
        self.id = user_id
        self.is_bot = is_bot
        self.username = username
        self.first_name = "Test"
        self.last_name = None


class FakeMember:
    def __init__(self, user: FakeUser, status: str) -> None:
        self.user = user
        self.status = status


@pytest.mark.asyncio
async def test_deactivate_user_prunes_tags(session) -> None:
    group = Group(telegram_group_id=-2001, title="G")
    session.add(group)
    await session.commit()
    await session.refresh(group)

    user = await upsert_user(
        session,
        group.id,
        telegram_user_id=10,
        username="worker",
        first_name="Worker",
        is_active=True,
    )
    tag = Tag(group_id=group.id, name="Support")
    session.add(tag)
    await session.commit()
    await session.refresh(tag)

    await set_tag_members(session, group, tag, [user.id], actor_telegram_id=1)
    loaded = await session.get(Tag, tag.id)
    assert len(loaded.members) == 1

    changed = await deactivate_user_and_prune_tags(session, group, 10, actor_telegram_id=1)
    assert changed is True

    loaded = await session.get(Tag, tag.id)
    assert loaded.members == []

    inactive = (
        await session.execute(select(User).where(User.telegram_user_id == 10))
    ).scalar_one()
    assert inactive.is_active is False


@pytest.mark.asyncio
async def test_sync_member_leave_deactivates_and_prunes(session) -> None:
    group = Group(telegram_group_id=-2002, title="G2")
    session.add(group)
    await session.commit()
    await session.refresh(group)

    user = await upsert_user(
        session,
        group.id,
        telegram_user_id=20,
        username="cam",
        first_name="Cam",
        is_active=True,
    )
    tag = Tag(group_id=group.id, name="Cams")
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    await set_tag_members(session, group, tag, [user.id], actor_telegram_id=1)

    member = FakeMember(FakeUser(20), "kicked")
    result = await sync_member_from_update(session, group, member, actor_telegram_id=1)
    assert result is None

    loaded = await session.get(Tag, tag.id)
    assert loaded.members == []
