from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from bot.database.models import Tag
from bot.keyboards.reply import MENU_BUTTON, format_quick_tag_button
from bot.utils.text import Locale


def quick_tags_reply_keyboard(
    locale: Locale,
    tags: list[Tag],
    *,
    show_menu_button: bool = False,
    selective: bool = False,
) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    for index in range(0, len(tags), 2):
        row = [
            KeyboardButton(text=format_quick_tag_button(tag.name))
            for tag in tags[index : index + 2]
        ]
        rows.append(row)
    if show_menu_button:
        rows.append([KeyboardButton(text=MENU_BUTTON)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        selective=selective,
        input_field_placeholder=locale.get("buttons.quick_placeholder"),
    )


def remove_reply_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
