from __future__ import annotations

QUICK_TAG_PREFIX = "📣 "
MENU_BUTTON = "⚙️ Меню"


def format_quick_tag_button(tag_name: str) -> str:
    return f"{QUICK_TAG_PREFIX}{tag_name}"


def parse_quick_tag_text(text: str) -> str | None:
    cleaned = text.strip()
    if cleaned.startswith(QUICK_TAG_PREFIX):
        name = cleaned[len(QUICK_TAG_PREFIX) :].strip()
        return name or None
    return None
