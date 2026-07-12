from __future__ import annotations

import re

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Group, User
from bot.services.tag_pending import PendingMemberSpec
from bot.services.users import member_to_user_fields, upsert_user

INACTIVE_STATUSES = {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}


def parse_member_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for line in text.replace(",", "\n").split("\n"):
        for part in re.split(r"[\s;]+", line.strip()):
            cleaned = part.strip().strip(",;")
            if cleaned:
                tokens.append(cleaned)
    return tokens


def _pending_from_token(raw: str, *, user_id: int | None, username: str | None) -> PendingMemberSpec:
    label = raw if raw.startswith("@") or raw.isdigit() else f"@{username}" if username else raw
    return PendingMemberSpec(
        telegram_user_id=user_id,
        username=username,
        label=label,
    )


async def resolve_group_member(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    chat_id: int,
    token: str,
) -> tuple[User | None, PendingMemberSpec | None, str | None]:
    raw = token.strip()
    if not raw:
        return None, None, "empty"

    username = raw[1:] if raw.startswith("@") else raw
    user_id: int | None = None
    resolved_username: str | None = None

    if username.isdigit():
        user_id = int(username)
        resolved_username = None
    else:
        resolved_username = username
        result = await session.execute(
            select(User).where(
                User.group_id == group.id,
                User.username.is_not(None),
                func.lower(User.username) == username.lower(),
            )
        )
        db_user = result.scalar_one_or_none()
        if db_user is not None:
            user_id = db_user.telegram_user_id
        else:
            try:
                administrators = await bot.get_chat_administrators(chat_id)
            except TelegramBadRequest:
                administrators = []
            for member in administrators:
                if member.user.is_bot:
                    continue
                if member.user.username and member.user.username.lower() == username.lower():
                    user_id = member.user.id
                    resolved_username = member.user.username
                    break

    if user_id is None and resolved_username:
        return None, _pending_from_token(raw, user_id=None, username=resolved_username), None

    if user_id is None:
        return None, None, "username_unknown"

    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except TelegramBadRequest:
        return None, _pending_from_token(raw, user_id=user_id, username=resolved_username), None

    if member.status in INACTIVE_STATUSES or member.user.is_bot:
        return None, _pending_from_token(raw, user_id=user_id, username=member.user.username), None

    fields = member_to_user_fields(member)
    user = await upsert_user(session, group.id, **fields)
    return user, None, None


async def resolve_member_tokens(
    bot: Bot,
    session: AsyncSession,
    group: Group,
    chat_id: int,
    text: str,
) -> tuple[list[User], list[PendingMemberSpec], list[tuple[str, str]]]:
    added: list[User] = []
    pending: list[PendingMemberSpec] = []
    failed: list[tuple[str, str]] = []
    seen_user_ids: set[int] = set()
    seen_pending: set[str] = set()

    for token in parse_member_tokens(text):
        user, pending_spec, error = await resolve_group_member(bot, session, group, chat_id, token)
        if user is not None:
            if user.id not in seen_user_ids:
                seen_user_ids.add(user.id)
                added.append(user)
            continue
        if pending_spec is not None:
            key = f"id:{pending_spec.telegram_user_id}|u:{pending_spec.username}"
            if key not in seen_pending:
                seen_pending.add(key)
                pending.append(pending_spec)
            continue
        failed.append((token, error or "unknown"))

    return added, pending, failed
