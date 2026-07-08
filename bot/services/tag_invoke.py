from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Group, Tag
from bot.services.permissions import is_chat_admin
from bot.services.tags import can_use_tags, delete_tag, get_tag, list_tags
from bot.services.users import format_tag_call


@dataclass
class InvokeTagResult:
    ok: bool
    message: str | None = None
    alert: str | None = None
    deleted_empty_tag: bool = False


async def invoke_tag(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    tag: Tag,
    user_id: int,
    locale,
) -> InvokeTagResult:
    is_admin = await is_chat_admin(bot, group.telegram_group_id, user_id)
    if not is_admin and not await can_use_tags(bot, session, group, user_id):
        return InvokeTagResult(ok=False, alert=locale.get("no_permission"))

    active_members = [member for member in tag.members if member.is_active]
    if not active_members:
        if group.auto_delete_empty_tags and is_admin:
            await delete_tag(session, group, tag, user_id)
            return InvokeTagResult(
                ok=False,
                alert=locale.get("commands.tag_empty", name=tag.name),
                deleted_empty_tag=True,
            )
        return InvokeTagResult(ok=False, alert=locale.get("commands.tag_empty", name=tag.name))

    return InvokeTagResult(
        ok=True,
        message=format_tag_call(tag.name, active_members),
    )


async def invoke_tag_by_name(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    tag_name: str,
    user_id: int,
    locale,
) -> InvokeTagResult:
    tags = await list_tags(session, group.id)
    tag = next((item for item in tags if item.name == tag_name), None)
    if tag is None:
        return InvokeTagResult(ok=False, alert=locale.get("commands.tag_not_found"))

    tag = await get_tag(session, group.id, tag.id)
    if tag is None:
        return InvokeTagResult(ok=False, alert=locale.get("commands.tag_not_found"))

    return await invoke_tag(bot, session, group, tag, user_id, locale)
