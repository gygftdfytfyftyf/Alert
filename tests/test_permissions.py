from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from bot.database.models import Group, Tag, User
from bot.services.permissions import get_user_access, is_bot_owner


@pytest.mark.asyncio
async def test_is_bot_owner_reads_env() -> None:
    os.environ["BOT_OWNER_IDS"] = "42,43"
    assert await is_bot_owner(42) is True
    assert await is_bot_owner(99) is False


@pytest.mark.asyncio
async def test_owner_gets_manage_access_without_telegram_admin(session) -> None:
    os.environ["BOT_OWNER_IDS"] = "555"
    group = Group(telegram_group_id=-1001, title="Test")
    session.add(group)
    await session.commit()
    await session.refresh(group)

    bot = AsyncMock()
    with patch("bot.services.permissions.is_telegram_admin", AsyncMock(return_value=False)):
        access = await get_user_access(bot, session, group, 555)

    assert access.can_manage is True
    assert access.can_assign_editors is True
    assert access.can_call_tags is True


@pytest.mark.asyncio
async def test_regular_member_can_call_when_setting_all(session) -> None:
    os.environ["BOT_OWNER_IDS"] = ""
    group = Group(telegram_group_id=-1002, title="Test", who_can_use_tags="all")
    session.add(group)
    await session.commit()
    await session.refresh(group)

    bot = AsyncMock()
    with patch("bot.services.permissions.is_telegram_admin", AsyncMock(return_value=False)):
        access = await get_user_access(bot, session, group, 777)

    assert access.can_manage is False
    assert access.can_call_tags is True
