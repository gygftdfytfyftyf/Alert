# Telegram Tag Bot

Telegram-бот для управления тегами (ролями) участников в группах. Позволяет администраторам создавать теги, назначать на них пользователей и вызывать тег с упоминанием всех участников.

## Возможности

- Работа одновременно в неограниченном количестве групп с изолированными настройками
- Управление тегами: создание, переименование, удаление, просмотр
- Назначение участников на теги (один пользователь может быть в нескольких тегах)
- Вызов тега с упоминанием всех назначенных пользователей
- **Быстрые кнопки** — постоянная клавиатура внизу чата (`/panel`), нажал — упомянул
- Inline-интерфейс для администраторов и участников
- Настройки доступа на уровне каждой группы
- Журнал изменений
- SQLite по умолчанию, поддержка PostgreSQL

## Стек

- Python 3.11+
- [aiogram](https://docs.aiogram.dev/) 3.x
- SQLAlchemy 2.x (async)
- YAML-локализация

## Быстрый старт

### 1. Создайте бота в Telegram

1. Откройте [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot` и следуйте инструкциям
3. Скопируйте выданный **токен**
4. В BotFather выполните `/setprivacy` → выберите бота → **Disable** (чтобы бот видел сообщения участников)

### 2. Установка и запуск

```bash
bash scripts/setup.sh    # установит зависимости и запросит токен
bash scripts/run.sh      # запустит бота
```

Или вручную:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # вписать BOT_TOKEN
python3 scripts/check_token.py   # проверка и ссылка для группы
python3 -m bot.main
```

### 3. Добавьте бота в группу

После запуска скрипт `check_token.py` покажет ссылку вида:

```
https://t.me/ВАШ_БОТ?startgroup=true
```

1. Перейдите по ссылке или найдите бота в Telegram
2. Выберите группу и добавьте бота
3. **Выдайте боту права администратора**
4. В группе отправьте `/menu`

Бот автоматически пришлёт приветствие при добавлении в группу.

### Docker (локально или на VPS)

```bash
cp .env.example .env   # указать BOT_TOKEN
docker compose up -d --build
```

### Постоянный онлайн-деплой

Бот нельзя держать 24/7 во временной среде Cursor — нужен хостинг с постоянным диском.

#### Вариант A — Railway (проще всего, через браузер)

1. https://railway.app → войти через **GitHub**
2. **New Project** → **Deploy from GitHub repo** → репозиторий `Alert`
3. Ветка: `cursor/telegram-tag-bot-8d30` (или `main` после мержа)
4. **Variables** → добавить:
   - `BOT_TOKEN` = токен от @BotFather
   - `BOT_OWNER_IDS` = `7970058531`
   - `DATABASE_URL` = `sqlite+aiosqlite:////data/bot.db`
5. **Volumes** → Add Volume → mount path: `/data`
6. Дождаться деплоя

Стоимость: ~$5/мес после пробного кредита.

#### Вариант B — Render (тоже через браузер)

1. https://render.com → войти через GitHub
2. **New** → **Blueprint** → репозиторий `Alert` (файл `render.yaml` подхватится)
3. Указать `BOT_TOKEN` и `BOT_OWNER_IDS` при создании
4. План **Starter** (~$7/мес) — нужен для worker + диска

#### Вариант C — свой VPS (самый надёжный)

На Ubuntu-сервере (Hetzner, Timeweb, Selectel и т.д.):

```bash
curl -fsSL https://raw.githubusercontent.com/gygftdfytfyftyf/Alert/cursor/telegram-tag-bot-8d30/scripts/deploy-vps.sh | sudo bash
# отредактировать /opt/aya-teg-bot/.env
sudo bash /opt/aya-teg-bot/scripts/deploy-vps.sh
```

#### Вариант D — Fly.io (через CLI)

```bash
flyctl auth login
bash scripts/deploy-fly.sh
```

**Важно:** не запускайте бота в двух местах одновременно (Cursor + хостинг) — polling конфликтует.

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен Telegram-бота (обязательно) |
| `DATABASE_URL` | URL БД (по умолчанию SQLite) |
| `LOG_LEVEL` | Уровень логирования (`INFO`, `DEBUG`, …) |
| `LOCALE` | Язык интерфейса (по умолчанию `ru`) |

### PostgreSQL

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tagbot
```

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Запуск бота |
| `/menu` | Главное меню |
| `/tags` | Список тегов для вызова |
| `/panel` | Быстрые кнопки тегов внизу экрана |
| `/panel_hide` | Скрыть быстрые кнопки (админ) |
| `/help` | Справка |

## Структура проекта

```
bot/
  main.py              # Точка входа
  config.py            # Конфигурация
  database/            # Модели и сессия БД
  handlers/            # Обработчики команд и callback
  keyboards/           # Inline-клавиатуры
  locales/             # Тексты интерфейса (ru.yaml)
  middlewares/         # DI и обработка ошибок
  services/            # Бизнес-логика
  utils/               # Утилиты локализации
```

## Схема БД

- `groups` — группы Telegram и настройки
- `tags` — теги внутри группы
- `users` — участники группы (отдельно для каждой группы)
- `tag_users` — связь many-to-many между тегами и пользователями
- `change_logs` — журнал изменений

## Настройки группы

- **Кто может вызывать теги** — все участники или только администраторы
- **Просмотр списка тегов** — разрешить/запретить обычным участникам
- **Удалять пустые теги** — автоматически при пустом вызове
- **Журнал изменений** — запись действий администраторов

## Лицензия

MIT
