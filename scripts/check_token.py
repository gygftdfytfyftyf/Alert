#!/usr/bin/env python3
"""Проверка BOT_TOKEN и вывод ссылки для добавления бота в группу."""

from __future__ import annotations

import asyncio
import os
import sys

from aiogram import Bot
from aiogram.exceptions import TelegramUnauthorizedError
from dotenv import load_dotenv


async def main() -> int:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token == "your_telegram_bot_token_here":
        print("❌ BOT_TOKEN не задан. Создайте бота в @BotFather и укажите токен в .env")
        print()
        print("Шаги:")
        print("  1. Откройте https://t.me/BotFather")
        print("  2. Отправьте /newbot и следуйте инструкциям")
        print("  3. Скопируйте токен в файл .env: BOT_TOKEN=...")
        print("  4. В BotFather: /setprivacy → Disable")
        print("  5. Запустите снова: python3 scripts/check_token.py")
        return 1

    bot = Bot(token=token)
    try:
        me = await bot.get_me()
    except TelegramUnauthorizedError:
        print("❌ Неверный BOT_TOKEN. Проверьте токен в .env")
        return 1
    finally:
        await bot.session.close()

    username = me.username
    print(f"✅ Бот подключён: @{username} ({me.first_name})")
    print()
    print("Добавить в группу:")
    print(f"  • Ссылка: https://t.me/{username}?startgroup=true")
    print(f"  • Или найдите @{username} в Telegram → Добавить в группу")
    print()
    print("После добавления:")
    print("  1. Выдайте боту права администратора")
    print("  2. В группе отправьте /menu")
    print()
    print("Запуск бота:")
    print("  python3 -m bot.main")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
