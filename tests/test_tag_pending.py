from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from bot.database.models import Group, Tag, TagPendingMember, User
from bot.services.tag_invoke import invoke_tag
from bot.services.tag_members_display import format_assign_members_caption
from bot.services.tag_pending import PendingMemberSpec, format_pending_mention, promote_pending_members, upsert_pending_member
from bot.services.tags import get_tag
from bot.utils.text import load_locale


def test_format_pending_mention_username() -> None:
    pending = TagPendingMember(tag_id=1, username="alice", label="@alice")
    assert format_pending_mention(pending) == "@alice"


@pytest.mark.asyncio
async def test_pending_promoted_when_user_becomes_active(session) -> None:
    group = Group(telegram_group_id=-4001, title="G")
    session.add(group)
    await session.commit()
    await session.refresh(group)

    tag = Tag(group_id=group.id, name="Support")
    session.add(tag)
    await session.commit()
    await session.refresh(tag)

    await upsert_pending_member(
        session,
        tag.id,
        PendingMemberSpec(telegram_user_id=555, username="worker", label="@worker"),
    )

    user = User(
        group_id=group.id,
        telegram_user_id=555,
        username="worker",
        first_name="Worker",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    promoted = await promote_pending_members(session, group, user)
    assert promoted == 1

    pending_left = (await session.execute(select(TagPendingMember))).scalars().all()
    assert pending_left == []

    loaded = await session.get(Tag, tag.id)
    await session.refresh(loaded, ["members"])
    assert len(loaded.members) == 1
    assert loaded.members[0].telegram_user_id == 555


@pytest.mark.asyncio
async def test_invoke_tag_mentions_pending_members(session) -> None:
    locale = load_locale()
    group = Group(telegram_group_id=-5001, title="G", who_can_use_tags="all")
    session.add(group)
    await session.commit()
    await session.refresh(group)

    tag = Tag(group_id=group.id, name="Булочки")
    session.add(tag)
    await session.commit()
    await session.refresh(tag)

    await upsert_pending_member(
        session,
        tag.id,
        PendingMemberSpec(telegram_user_id=None, username="paytech_support2", label="@paytech_support2"),
    )

    loaded = await get_tag(session, group.id, tag.id)
    assert loaded is not None

    bot = AsyncMock()
    result = await invoke_tag(bot, session, group, loaded, user_id=1, locale=locale)
    assert result.ok is True
    assert result.message is not None
    assert "Булочки" in result.message
    assert "@paytech_support2" in result.message


@pytest.mark.asyncio
async def test_assign_caption_shows_pending_members(session) -> None:
    locale = load_locale()
    group = Group(telegram_group_id=-5002, title="G")
    session.add(group)
    await session.commit()
    await session.refresh(group)

    tag = Tag(group_id=group.id, name="Support")
    session.add(tag)
    await session.commit()
    await session.refresh(tag)

    await upsert_pending_member(
        session,
        tag.id,
        PendingMemberSpec(telegram_user_id=None, username="alice", label="@alice"),
    )

    loaded = await get_tag(session, group.id, tag.id)
    assert loaded is not None
    caption = format_assign_members_caption(locale, loaded)
    assert "@alice" in caption
    assert "⏳" in caption
