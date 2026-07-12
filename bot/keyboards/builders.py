from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.models import Group, Tag, User
from bot.keyboards.inline import AssignCB, CallTagCB, EditorCB, MenuCB, SettingsCB, TagCB
from bot.utils.text import Locale


def cancel_keyboard(locale: Locale) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=locale.get("buttons.cancel"), callback_data=MenuCB(action="cancel").pack())]
        ]
    )


def main_menu_keyboard(
    locale: Locale,
    *,
    can_assign_editors: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=locale.get("buttons.create_tag"), callback_data=MenuCB(action="create_tag").pack())],
        [InlineKeyboardButton(text=locale.get("buttons.tag_list_manage"), callback_data=MenuCB(action="tag_list").pack())],
        [
            InlineKeyboardButton(text=locale.get("buttons.settings"), callback_data=MenuCB(action="settings").pack()),
            InlineKeyboardButton(
                text=locale.get("buttons.refresh_members"),
                callback_data=MenuCB(action="refresh_members").pack(),
            ),
        ],
        [InlineKeyboardButton(text=locale.get("buttons.quick_panel"), callback_data=MenuCB(action="quick_panel").pack())],
    ]
    if can_assign_editors:
        rows.append(
            [InlineKeyboardButton(text=locale.get("buttons.manage_editors"), callback_data=MenuCB(action="editors").pack())]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tag_list_keyboard(
    locale: Locale,
    tags: list[Tag],
    *,
    for_call: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for tag in tags:
        if for_call:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"📣 {tag.name}",
                        callback_data=CallTagCB(tag_id=tag.id).pack(),
                    )
                ]
            )
        else:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=tag.name,
                        callback_data=TagCB(action="open", tag_id=tag.id).pack(),
                    )
                ]
            )
    if not for_call:
        rows.append([InlineKeyboardButton(text=locale.get("buttons.back"), callback_data=MenuCB(action="main").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tag_detail_keyboard(locale: Locale, tag_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=locale.get("buttons.rename"), callback_data=TagCB(action="rename", tag_id=tag_id).pack())],
            [
                InlineKeyboardButton(
                    text=locale.get("buttons.assign_members"),
                    callback_data=TagCB(action="assign", tag_id=tag_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=locale.get("buttons.view_members"),
                    callback_data=TagCB(action="view_members", tag_id=tag_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=locale.get("buttons.call_tag"),
                    callback_data=CallTagCB(tag_id=tag_id).pack(),
                )
            ],
            [InlineKeyboardButton(text=locale.get("buttons.delete_tag"), callback_data=TagCB(action="delete", tag_id=tag_id).pack())],
            [InlineKeyboardButton(text=locale.get("buttons.back"), callback_data=MenuCB(action="tag_list").pack())],
        ]
    )


def settings_keyboard(locale: Locale, group: Group, *, show_editors: bool) -> InlineKeyboardMarkup:
    who_label = (
        locale.get("settings.value_admins")
        if group.who_can_use_tags == "admins"
        else locale.get("settings.value_all")
    )
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=f"{locale.get('settings.who_can_use_tags')}: {who_label}",
                callback_data=SettingsCB(action="toggle", key="who_can_use_tags").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{locale.get('settings.allow_tag_list_view')}: "
                f"{locale.get('settings.value_on') if group.allow_tag_list_view else locale.get('settings.value_off')}",
                callback_data=SettingsCB(action="toggle", key="allow_tag_list_view").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{locale.get('settings.auto_delete_empty_tags')}: "
                f"{locale.get('settings.value_on') if group.auto_delete_empty_tags else locale.get('settings.value_off')}",
                callback_data=SettingsCB(action="toggle", key="auto_delete_empty_tags").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{locale.get('settings.enable_change_log')}: "
                f"{locale.get('settings.value_on') if group.enable_change_log else locale.get('settings.value_off')}",
                callback_data=SettingsCB(action="toggle", key="enable_change_log").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{locale.get('settings.enable_quick_buttons')}: "
                f"{locale.get('settings.value_on') if group.enable_quick_buttons else locale.get('settings.value_off')}",
                callback_data=SettingsCB(action="toggle", key="enable_quick_buttons").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=locale.get("buttons.change_log"),
                callback_data=SettingsCB(action="view_log").pack(),
            )
        ],
    ]
    if show_editors:
        rows.append(
            [
                InlineKeyboardButton(
                    text=locale.get("buttons.manage_editors"),
                    callback_data=MenuCB(action="editors").pack(),
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=locale.get("buttons.back"), callback_data=MenuCB(action="main").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def editors_menu_keyboard(locale: Locale, editors: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for telegram_user_id, label in editors:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 {label}",
                    callback_data=EditorCB(action="remove", user_id=telegram_user_id).pack(),
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text=locale.get("buttons.add_editor"), callback_data=EditorCB(action="add", page=0).pack())]
    )
    rows.append([InlineKeyboardButton(text=locale.get("buttons.back"), callback_data=MenuCB(action="main").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def add_editor_keyboard(
    locale: Locale,
    candidates: list[User],
    page: int,
    page_size: int = 8,
) -> InlineKeyboardMarkup:
    start = page * page_size
    chunk = candidates[start : start + page_size]
    rows: list[list[InlineKeyboardButton]] = []

    for user in chunk:
        label = _user_label(user, user.telegram_user_id)
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=EditorCB(action="pick", user_id=user.telegram_user_id, page=page).pack(),
                )
            ]
        )

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="⬅️", callback_data=EditorCB(action="page", page=page - 1).pack())
        )
    if start + page_size < len(candidates):
        nav_row.append(
            InlineKeyboardButton(text="➡️", callback_data=EditorCB(action="page", page=page + 1).pack())
        )
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text=locale.get("buttons.back"), callback_data=MenuCB(action="editors").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _user_label(user: User | None, telegram_user_id: int) -> str:
    if user is None:
        return str(telegram_user_id)
    label = user.first_name or user.username or str(telegram_user_id)
    if user.username:
        return f"{label} (@{user.username})"
    return label


def assign_members_keyboard(
    locale: Locale,
    tag_id: int,
    users: list[User],
    selected_ids: set[int],
    page: int,
    page_size: int = 8,
) -> InlineKeyboardMarkup:
    start = page * page_size
    chunk = users[start : start + page_size]
    rows: list[list[InlineKeyboardButton]] = []

    for user in chunk:
        label = _user_label(user, user.telegram_user_id)
        selected = user.id in selected_ids
        button_text = locale.get("buttons.toggle_on" if selected else "buttons.toggle_off", label=label)
        rows.append(
            [
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=AssignCB(action="toggle", tag_id=tag_id, user_id=user.id, page=page).pack(),
                )
            ]
        )

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=AssignCB(action="page", tag_id=tag_id, page=page - 1).pack(),
            )
        )
    if start + page_size < len(users):
        nav_row.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=AssignCB(action="page", tag_id=tag_id, page=page + 1).pack(),
            )
        )
    if nav_row:
        rows.append(nav_row)

    rows.append(
        [
            InlineKeyboardButton(
                text=locale.get("buttons.add_members_manual"),
                callback_data=AssignCB(action="manual", tag_id=tag_id, page=page).pack(),
            )
        ]
    )
    rows.append(
        [InlineKeyboardButton(text=locale.get("buttons.save"), callback_data=AssignCB(action="save", tag_id=tag_id).pack())]
    )
    rows.append(
        [InlineKeyboardButton(text=locale.get("buttons.back"), callback_data=TagCB(action="open", tag_id=tag_id).pack())]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def assign_manual_prompt_keyboard(locale: Locale, tag_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=locale.get("buttons.back"),
                    callback_data=AssignCB(action="back", tag_id=tag_id).pack(),
                )
            ]
        ]
    )
