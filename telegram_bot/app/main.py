from __future__ import annotations

import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.config import Settings
from app.handlers.auth import router as auth_router
from app.handlers.menu import router as menu_router
from app.handlers.start import router as start_router
from app.middlewares.services import ServicesMiddleware
from app.services.auth_store import AuthStore
from app.services.backend_client import BackendClient
from app.services.ui_state import UIStateStore


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def create_app(settings: Settings) -> web.Application:
    setup_logging(settings.log_level)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start_router)
    dp.include_router(auth_router)
    dp.include_router(menu_router)

    auth_store = AuthStore(settings.sqlite_path)
    backend_client = BackendClient(
        base_url=settings.backend_base_url,
        timeout_seconds=settings.request_timeout_seconds,
    )
    ui_state = UIStateStore()

    dp.update.middleware(ServicesMiddleware(auth_store, backend_client, ui_state))

    async def on_startup(_: web.Application) -> None:
        await auth_store.init()
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_my_commands([])

        webhook_url = f"{settings.webhook_base_url}{settings.webhook_path}"
        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.webhook_secret or None,
            drop_pending_updates=True,
        )
        logging.getLogger(__name__).info("Webhook set to %s", webhook_url)

    async def on_shutdown(_: web.Application) -> None:
        try:
            await bot.delete_webhook()
        finally:
            await bot.session.close()

    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook_secret or None,
    )
    webhook_handler.register(app, path=settings.webhook_path)

    setup_application(app, dp, bot=bot)
    return app


def main() -> None:
    settings = Settings.from_env()
    app = create_app(settings)
    web.run_app(app, host=settings.app_host, port=settings.app_port)


if __name__ == "__main__":
    main()
