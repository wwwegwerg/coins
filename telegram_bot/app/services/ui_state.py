from __future__ import annotations

from collections.abc import MutableMapping


class UIStateStore:
    def __init__(self) -> None:
        self._message_ids: MutableMapping[int, int] = {}
        self._result_message_ids: MutableMapping[int, int] = {}

    def set_message_id(self, telegram_user_id: int, message_id: int) -> None:
        self._message_ids[telegram_user_id] = message_id

    def get_message_id(self, telegram_user_id: int) -> int | None:
        return self._message_ids.get(telegram_user_id)

    def set_result_message_id(self, telegram_user_id: int, message_id: int) -> None:
        self._result_message_ids[telegram_user_id] = message_id

    def get_result_message_id(self, telegram_user_id: int) -> int | None:
        return self._result_message_ids.get(telegram_user_id)

    def clear_result_message_id(self, telegram_user_id: int) -> None:
        self._result_message_ids.pop(telegram_user_id, None)

    def clear(self, telegram_user_id: int) -> None:
        self._message_ids.pop(telegram_user_id, None)
        self._result_message_ids.pop(telegram_user_id, None)
