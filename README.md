# Telegram Schedule Bot + Mini App

Готовый Telegram-бот с Mini App для расписания по группам.

## Возможности

- Telegram-бот на aiogram 3
- Mini App на HTML/CSS/JavaScript
- PostgreSQL на RelaxDev для постоянного хранения данных
- SQLite как локальный fallback, если `DATABASE_URL` не задан
- Выбор группы и дня
- Запоминание выбранной группы
- Админка прямо в Mini App
- Добавление, редактирование и удаление занятий
- Telegram theme integration

## Деплой на RelaxDev

RelaxDev поддерживает Python/FastAPI, переменные окружения и PostgreSQL. Файловая система контейнера эфемерна, поэтому для продакшена используется PostgreSQL, а не SQLite.

### 1. Репозиторий

Залей проект в GitHub/GitLab/GitVerse/GitFlic и импортируй репозиторий в RelaxDev.

### 2. Создай PostgreSQL

В проекте RelaxDev:

1. Открой раздел **База данных**.
2. Создай **PostgreSQL**.
3. RelaxDev автоматически добавит `DATABASE_URL` в переменные окружения.

### 3. Переменные окружения

Добавь:

```env
BOT_TOKEN=токен_от_BotFather
ADMIN_IDS=твой_telegram_id
WEBAPP_URL=https://адрес-твоего-проекта.relaxdev.ru
```

`DATABASE_URL` вручную задавать не нужно, если PostgreSQL создан внутри RelaxDev.

### 4. Команда запуска

Если RelaxDev не определит её автоматически, укажи:

```bash
python -m app.main
```

Приложение слушает `0.0.0.0:$PORT`, как требуется платформе.

### 5. Первый запуск

После деплоя открой адрес проекта в браузере. Если появилась страница Mini App — API работает.

Открой бота в Telegram и отправь `/start`.

### 6. Настройка Mini App в BotFather

Можно пользоваться кнопкой из `/start`. Также для удобства можно назначить Mini App кнопкой меню через BotFather.

В качестве URL укажи **точный HTTPS-адрес проекта RelaxDev**, например:

```text
https://my-schedule.relaxdev.ru
```

## Локальный запуск

Если `DATABASE_URL` пустой, проект использует SQLite.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

## Docker

```bash
docker compose up -d --build
```

Для продакшена на RelaxDev предпочтительнее PostgreSQL.

## Админка

В `ADMIN_IDS` укажи Telegram ID администраторов через запятую.

В админке можно:

1. Создать группу.
2. Выбрать группу.
3. Добавлять занятия.
4. Редактировать занятия.
5. Удалять занятия.

Дни:

1 — Понедельник  
2 — Вторник  
3 — Среда  
4 — Четверг  
5 — Пятница  
6 — Суббота  
7 — Воскресенье

## Важно

- Не добавляй `.env` в Git.
- Не публикуй `BOT_TOKEN`.
- Не используй SQLite как постоянное хранилище на RelaxDev: контейнерная файловая система сбрасывается при пересборке.
