from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.services.auth_store import AuthStore
from app.services.backend_client import BackendClient
from app.services.ui_state import UIStateStore


class ServicesMiddleware(BaseMiddleware):
    def __init__(
        self,
        auth_store: AuthStore,
        backend_client: BackendClient,
        ui_state: UIStateStore,
    ) -> None:
        self._auth_store = auth_store
        self._backend_client = backend_client
        self._ui_state = ui_state

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["auth_store"] = self._auth_store
        data["backend_client"] = self._backend_client
        data["ui_state"] = self._ui_state
        return await handler(event, data)
