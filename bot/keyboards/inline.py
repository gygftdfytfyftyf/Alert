from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class MenuCB(CallbackData, prefix="menu"):
    action: str


class TagCB(CallbackData, prefix="tag"):
    action: str
    tag_id: int = 0
    page: int = 0


class AssignCB(CallbackData, prefix="assign"):
    action: str
    tag_id: int
    user_id: int = 0
    page: int = 0


class SettingsCB(CallbackData, prefix="settings"):
    action: str
    key: str = ""


class EditorCB(CallbackData, prefix="editor"):
    action: str
    user_id: int = 0
    page: int = 0


class CallTagCB(CallbackData, prefix="call"):
    tag_id: int
