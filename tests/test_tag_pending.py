from __future__ import annotations

import pytest
from sqlalchemy import select

from bot.database.models import Group, Tag, TagPendingMember, User
from bot.services.tag_pending import PendingMemberSpec, format_pending_mention, promote_pending_members, upsert_pending_member


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
