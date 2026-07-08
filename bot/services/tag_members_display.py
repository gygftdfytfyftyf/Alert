from __future__ import annotations

from bot.database.models import Tag
from bot.services.tag_pending import format_pending_mention
from bot.utils.text import Locale


def format_assign_members_caption(locale: Locale, tag: Tag) -> str:
    lines = [locale.get("buttons.assign_members") + f": <b>{tag.name}</b>"]
    if tag.pending_members:
        pending_labels = ", ".join(
            f"⏳ {format_pending_mention(pending)}" for pending in tag.pending_members
        )
        lines.append("")
        lines.append(locale.get("commands.members_pending_in_tag", names=pending_labels))
    return "\n".join(lines)
