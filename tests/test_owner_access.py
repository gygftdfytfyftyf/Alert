from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from bot.database.models import Group, GroupEditor
from bot.services.owner_access import ensure_bot_owner_in_group


@pytest.mark.asyncio
async def test_owner_auto_registered_as_editor(session) -> None:
    import os

    os.environ["BOT_OWNER_IDS"] = "888"
    group = Group(telegram_group_id=-3001, title="Client")
    session.add(group)
    await session.commit()
    await session.refresh(group)

    bot = AsyncMock()
    with (
        patch("bot.services.permissions.is_bot_owner", AsyncMock(return_value=True)),
        patch("bot.services.permissions.is_telegram_admin", AsyncMock(return_value=False)),
    ):
        added = await ensure_bot_owner_in_group(bot, session, group, 888)

    assert added is True
    editors = (await session.execute(
        __import__("sqlalchemy").select(GroupEditor).where(GroupEditor.group_id == group.id)
    )).scalars().all()
    assert len(editors) == 1
    assert editors[0].telegram_user_id == 888


@pytest.mark.asyncio
async def test_telegram_admin_owner_not_duplicated_as_editor(session) -> None:
    group = Group(telegram_group_id=-3002, title="Client")
    session.add(group)
    await session.commit()
    await session.refresh(group)

    bot = AsyncMock()
    with (
        patch("bot.services.permissions.is_bot_owner", AsyncMock(return_value=True)),
        patch("bot.services.permissions.is_telegram_admin", AsyncMock(return_value=True)),
    ):
        added = await ensure_bot_owner_in_group(bot, session, group, 888)

    assert added is False
