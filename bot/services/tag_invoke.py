from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Group, Tag
from bot.services.permissions import get_user_access
from bot.services.tag_pending import format_pending_mention
from bot.services.tags import delete_tag, get_tag, list_tags
from bot.services.users import format_user_mention


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
    access = await get_user_access(bot, session, group, user_id)
    if not access.can_call_tags:
        return InvokeTagResult(ok=False, alert=locale.get("no_permission"))

    active_members = [member for member in tag.members if member.is_active]
    pending_members = list(tag.pending_members)
    if not active_members and not pending_members:
        if group.auto_delete_empty_tags and access.can_manage:
            await delete_tag(session, group, tag, user_id)
            return InvokeTagResult(
                ok=False,
                alert=locale.get("commands.tag_empty", name=tag.name),
                deleted_empty_tag=True,
            )
        return InvokeTagResult(ok=False, alert=locale.get("commands.tag_empty", name=tag.name))

    lines = [f"🔔 {tag.name}"]
    lines.extend(format_user_mention(member) for member in active_members)
    lines.extend(format_pending_mention(pending) for pending in pending_members)

    return InvokeTagResult(
        ok=True,
        message="\n".join(lines),
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

    loaded_tag = await get_tag(session, group.id, tag.id)
    if loaded_tag is None:
        return InvokeTagResult(ok=False, alert=locale.get("commands.tag_not_found"))

    return await invoke_tag(bot, session, group, loaded_tag, user_id, locale)
