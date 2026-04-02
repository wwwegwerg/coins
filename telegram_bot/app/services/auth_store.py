from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import aiosqlite


@dataclass(slots=True)
class UserSession:
    telegram_user_id: int
    backend_login: str
    token: str


class AuthStore:
    def __init__(self, sqlite_path: str) -> None:
        self._sqlite_path = sqlite_path

    async def init(self) -> None:
        db_path = Path(self._sqlite_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self._sqlite_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    telegram_user_id INTEGER PRIMARY KEY,
                    backend_login TEXT NOT NULL,
                    token TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    async def save_session(self, telegram_user_id: int, backend_login: str, token: str) -> None:
        async with aiosqlite.connect(self._sqlite_path) as db:
            await db.execute(
                """
                INSERT INTO user_sessions (telegram_user_id, backend_login, token)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    backend_login = excluded.backend_login,
                    token = excluded.token,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (telegram_user_id, backend_login, token),
            )
            await db.commit()

    async def get_session(self, telegram_user_id: int) -> UserSession | None:
        async with aiosqlite.connect(self._sqlite_path) as db:
            cursor = await db.execute(
                """
                SELECT telegram_user_id, backend_login, token
                FROM user_sessions
                WHERE telegram_user_id = ?
                """,
                (telegram_user_id,),
            )
            row = await cursor.fetchone()

        if not row:
            return None

        return UserSession(
            telegram_user_id=row[0],
            backend_login=row[1],
            token=row[2],
        )

    async def delete_session(self, telegram_user_id: int) -> None:
        async with aiosqlite.connect(self._sqlite_path) as db:
            await db.execute(
                "DELETE FROM user_sessions WHERE telegram_user_id = ?",
                (telegram_user_id,),
            )
            await db.commit()
