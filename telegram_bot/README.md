# Telegram Bot (aiogram 3, webhook)

Бот живет отдельно от backend-папки и работает через webhook (для внешнего доступа используйте ngrok).

## Что уже реализовано

- авторизация по кнопке после `/start`;
- FSM-ввод логина/пароля;
- работа с backend API: `/login`, `/auth`, `/logout`;
- хранение backend token в SQLite;
- очистка чата: пользовательский текст удаляется, бот переиспользует одну карточку через `edit`.

## Расположение

- backend: `./MoneyDetector-main`
- bot: `./telegram_bot`
- docker compose для бота: `./docker-compose.bot.yml`

## Настройка `.env`

```bash
cp telegram_bot/.env.example telegram_bot/.env
```

Заполните обязательно:

- `BOT_TOKEN`
- `WEBHOOK_BASE_URL` (HTTPS URL из ngrok, без path)
- `WEBHOOK_SECRET` (любая длинная строка)

Остальные значения можно оставить по умолчанию.

## Запуск в Docker

```bash
docker compose -f docker-compose.bot.yml up -d --build
```

Бот слушает внутри контейнера `0.0.0.0:8080` (проброшен на хост `8080`).

## Запуск ngrok

```bash
ngrok http 8080
```

Дальше:

1. Возьмите HTTPS URL из ngrok (например, `https://abcd-1234.ngrok-free.app`).
2. Запишите его в `WEBHOOK_BASE_URL`.
3. Перезапустите контейнер бота:

```bash
docker compose -f docker-compose.bot.yml up -d --build
```

При старте контейнер сам вызывает `setWebhook` на URL:

- `${WEBHOOK_BASE_URL}${WEBHOOK_PATH}`

## Важно

Если URL ngrok поменялся, нужно обновить `WEBHOOK_BASE_URL` и перезапустить контейнер бота.
