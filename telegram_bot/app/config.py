import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    bot_token: str
    backend_base_url: str
    request_timeout_seconds: float
    sqlite_path: str
    log_level: str
    webhook_base_url: str
    webhook_path: str
    webhook_secret: str
    app_host: str
    app_port: int


    @classmethod
    def from_env(cls) -> "Settings":
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            raise RuntimeError("BOT_TOKEN is required")

        webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "").strip().rstrip("/")
        if not webhook_base_url:
            raise RuntimeError("WEBHOOK_BASE_URL is required (ngrok HTTPS URL)")

        webhook_path = os.getenv("WEBHOOK_PATH", "/telegram/webhook").strip()
        if not webhook_path.startswith("/"):
            webhook_path = f"/{webhook_path}"

        return cls(
            bot_token=bot_token,
            backend_base_url=os.getenv("BACKEND_BASE_URL", "http://host.docker.internal:8000").rstrip("/"),
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
            sqlite_path=os.getenv("SQLITE_PATH", "/data/bot.db"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            webhook_base_url=webhook_base_url,
            webhook_path=webhook_path,
            webhook_secret=os.getenv("WEBHOOK_SECRET", "").strip(),
            app_host=os.getenv("APP_HOST", "0.0.0.0"),
            app_port=int(os.getenv("APP_PORT", "8080")),
        )
