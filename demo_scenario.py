#!/usr/bin/env python3
"""Симуляция сценария работы бота в консоли (без Telegram API)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from bot.database.session import SessionLocal, init_db
from bot.keyboards.builders import (
    assign_members_keyboard,
    main_menu_keyboard,
    tag_detail_keyboard,
    tag_list_keyboard,
)
from bot.services.permissions import get_or_create_group
from bot.services.tags import create_tag, list_tags
from bot.services.users import format_tag_call, set_tag_members, upsert_user
from bot.utils.text import load_locale


@dataclass
class FakeUser:
    id: int
    db_id: int = 0
    username: str | None = None
    first_name: str = ""


@dataclass
class ChatDemo:
    title: str
    messages: list[str] = field(default_factory=list)

    def bot(self, text: str, buttons: list[list[str]] | None = None) -> None:
        lines = [f"🤖 Бот: {text}"]
        if buttons:
            lines.append("")
            for row in buttons:
                lines.append("  " + "  ".join(f"[{b}]" for b in row))
        self.messages.append("\n".join(lines))

    def user(self, name: str, text: str) -> None:
        self.messages.append(f"👤 {name}: {text}")

    def render(self) -> str:
        return "\n\n".join(self.messages)


def keyboard_rows(markup) -> list[list[str]]:
    return [[button.text for button in row] for row in markup.inline_keyboard]


async def run_demo() -> str:
    locale = load_locale()
    await init_db()
    chat = ChatDemo(title="Группа «Логистика и монтаж»")

    async with SessionLocal() as session:
        group = await get_or_create_group(session, -1001234567890, chat.title)
        admin_id = 1001

        members = [
            FakeUser(2001, username="ivan", first_name="Иван"),
            FakeUser(2002, username="alex", first_name="Алексей"),
            FakeUser(2003, username="sergey", first_name="Сергей"),
            FakeUser(2004, username="dmitry", first_name="Дмитрий"),
            FakeUser(2005, username="andrey", first_name="Андрей"),
        ]
        for member in members:
            user = await upsert_user(
                session,
                group.id,
                telegram_user_id=member.id,
                username=member.username,
                first_name=member.first_name,
            )
            member.db_id = user.id

        chat.user("Администратор", "/start")
        chat.bot(locale.get("commands.start_group"))

        chat.user("Администратор", "/menu")
        chat.bot(
            locale.get("commands.menu_title"),
            keyboard_rows(main_menu_keyboard(locale, is_admin=True, can_view_tags=True)),
        )

        chat.user("Администратор", "нажимает [➕ Создать тег]")
        chat.bot(
            locale.get("commands.enter_tag_name"),
            keyboard_rows(main_menu_keyboard(locale, True, True))[:1] or [["❌ Отмена"]],
        )

        chat.user("Администратор", "Провайдеры")
        tag1 = await create_tag(session, group, "Провайдеры", admin_id)
        chat.bot(locale.get("commands.tag_created", name=tag1.name))

        chat.user("Администратор", "нажимает [👥 Назначить участников]")
        selected = {members[0].db_id, members[1].db_id, members[2].db_id}
        assign_kb = assign_members_keyboard(locale, tag1.id, await _users(session, group.id), selected, 0)
        chat.bot(
            f"{locale.get('buttons.assign_members')}: <b>{tag1.name}</b>",
            keyboard_rows(assign_kb),
        )

        await set_tag_members(session, group, tag1, list(selected), admin_id)
        chat.user("Администратор", "нажимает [💾 Сохранить]")
        chat.bot(locale.get("commands.members_saved", name=tag1.name))

        tag2 = await create_tag(session, group, "Камов", admin_id)
        chat.bot(locale.get("commands.tag_created", name=tag2.name))
        await set_tag_members(session, group, tag2, [members[3].db_id, members[4].db_id], admin_id)

        tags = await list_tags(session, group.id)
        chat.user("Администратор", "нажимает [📋 Список тегов]")
        chat.bot(
            locale.get("commands.tags_title"),
            keyboard_rows(tag_list_keyboard(locale, tags, is_admin=True)),
        )

        chat.user("Администратор", "открывает тег «Провайдеры»")
        chat.bot(
            f"<b>{tag1.name}</b>",
            keyboard_rows(tag_detail_keyboard(locale, tag1.id)),
        )

        chat.user("Участник", "нажимает [📣 Вызвать тег] у «Провайдеры»")
        tag1_loaded = await _tag_with_members(session, group.id, tag1.id)
        active = [m for m in tag1_loaded.members if m.is_active]
        chat.bot(format_tag_call(tag1_loaded.name, active))

        chat.user("Участник", "/tags")
        chat.bot(
            locale.get("commands.tags_title"),
            keyboard_rows(tag_list_keyboard(locale, tags, is_admin=False, for_call=True)),
        )

    return chat.render()


async def _users(session, group_id):
    from bot.services.users import list_active_users

    return await list_active_users(session, group_id)


async def _tag_with_members(session, group_id, tag_id):
    from bot.services.tags import get_tag

    return await get_tag(session, group_id, tag_id)


if __name__ == "__main__":
    print("=" * 60)
    print("ДЕМО: Telegram-бот управления тегами")
    print("=" * 60)
    print()
    print(asyncio.run(run_demo()))
