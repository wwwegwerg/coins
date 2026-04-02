from __future__ import annotations

from typing import Any

import httpx


class BackendClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url
        self._timeout = timeout_seconds

    @staticmethod
    def _cookies(token: str) -> dict[str, str]:
        return {"coin_detector_token": token}

    @staticmethod
    def _json_or_none(response: httpx.Response) -> Any:
        try:
            return response.json()
        except Exception:
            return None

    async def login(self, login: str, password: str) -> tuple[bool, str | None, str | None]:
        payload = {"login": login, "password": password}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(f"{self._base_url}/login", json=payload)
                data = self._json_or_none(response)
        except Exception as exc:
            return False, None, f"Backend unreachable: {exc}"

        if not isinstance(data, dict):
            return False, None, "Invalid backend response"

        if data.get("success") is True and isinstance(data.get("token"), str):
            return True, data["token"], None

        return False, None, data.get("error") or "invalid_credentials"

    async def check_auth(self, token: str) -> tuple[bool, str | None]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    f"{self._base_url}/auth",
                    cookies=self._cookies(token),
                )
                data = self._json_or_none(response)
        except Exception:
            return False, None

        if not isinstance(data, dict):
            return False, None

        return bool(data.get("authorized")), data.get("login")

    async def logout(self, token: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                await client.post(f"{self._base_url}/logout", cookies=self._cookies(token))
            return True
        except Exception:
            return False

    async def detect(self, token: str, filename: str, image_bytes: bytes) -> dict[str, Any]:
        files = {"image": (filename, image_bytes, "image/jpeg")}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/detect",
                    cookies=self._cookies(token),
                    files=files,
                )
                data = self._json_or_none(response)
        except Exception as exc:
            return {"ok": False, "unauthorized": False, "error": f"Backend unreachable: {exc}"}

        if response.status_code == 401:
            return {"ok": False, "unauthorized": True, "error": "Unauthorized"}

        if not isinstance(data, dict):
            return {"ok": False, "unauthorized": False, "error": "Invalid backend response"}

        task_id = data.get("task_id")
        if isinstance(task_id, str) and task_id:
            return {"ok": True, "unauthorized": False, "task_id": task_id}

        return {
            "ok": False,
            "unauthorized": False,
            "error": data.get("error") or "detect_failed",
        }

    async def get_result(self, token: str, task_id: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    f"{self._base_url}/result/{task_id}",
                    cookies=self._cookies(token),
                )
                data = self._json_or_none(response)
        except Exception as exc:
            return {"ok": False, "unauthorized": False, "error": f"Backend unreachable: {exc}"}

        if response.status_code == 401:
            return {"ok": False, "unauthorized": True, "error": "Unauthorized"}

        if not isinstance(data, dict):
            return {"ok": False, "unauthorized": False, "error": "Invalid backend response"}

        status = data.get("status")
        if not isinstance(status, str):
            return {"ok": False, "unauthorized": False, "error": "Invalid backend response"}

        if status == "SUCCESS":
            return {
                "ok": True,
                "unauthorized": False,
                "status": status,
                "result": data.get("result") if isinstance(data.get("result"), dict) else {},
            }

        if status == "FAILURE":
            return {
                "ok": True,
                "unauthorized": False,
                "status": status,
                "error": str(data.get("error") or "Task failed"),
            }

        return {
            "ok": True,
            "unauthorized": False,
            "status": status,
        }

    async def get_history(self, token: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    f"{self._base_url}/history",
                    cookies=self._cookies(token),
                )
                data = self._json_or_none(response)
        except Exception as exc:
            return {"ok": False, "unauthorized": False, "error": f"Backend unreachable: {exc}"}

        if response.status_code == 401:
            return {"ok": False, "unauthorized": True, "error": "Unauthorized"}

        if not isinstance(data, dict):
            return {"ok": False, "unauthorized": False, "error": "Invalid backend response"}

        if data.get("success") is True and isinstance(data.get("items"), list):
            return {"ok": True, "unauthorized": False, "items": data["items"]}

        return {
            "ok": False,
            "unauthorized": False,
            "error": data.get("error") or "history_failed",
        }

    async def get_balance(self, token: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    f"{self._base_url}/balance",
                    cookies=self._cookies(token),
                )
                data = self._json_or_none(response)
        except Exception as exc:
            return {"ok": False, "unauthorized": False, "error": f"Backend unreachable: {exc}"}

        if response.status_code == 401:
            return {"ok": False, "unauthorized": True, "error": "Unauthorized"}

        if not isinstance(data, dict):
            return {"ok": False, "unauthorized": False, "error": "Invalid backend response"}

        if data.get("success") is True:
            return {
                "ok": True,
                "unauthorized": False,
                "balance": data.get("balance"),
                "cost": data.get("cost"),
            }

        return {
            "ok": False,
            "unauthorized": False,
            "error": data.get("error") or "balance_failed",
        }

    async def topup_balance(self, token: str, amount: int) -> dict[str, Any]:
        payload = {"amount": amount}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/balance/topup",
                    cookies=self._cookies(token),
                    json=payload,
                )
                data = self._json_or_none(response)
        except Exception as exc:
            return {"ok": False, "unauthorized": False, "error": f"Backend unreachable: {exc}"}

        if response.status_code == 401:
            return {"ok": False, "unauthorized": True, "error": "Unauthorized"}

        if not isinstance(data, dict):
            return {"ok": False, "unauthorized": False, "error": "Invalid backend response"}

        if data.get("success") is True:
            return {
                "ok": True,
                "unauthorized": False,
                "balance": data.get("balance"),
                "added": data.get("added"),
            }

        return {
            "ok": False,
            "unauthorized": False,
            "error": data.get("error") or "topup_failed",
        }

    async def get_result_image(self, image_path: str) -> dict[str, Any]:
        url = f"{self._base_url}{image_path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url)
        except Exception as exc:
            return {"ok": False, "error": f"Backend unreachable: {exc}"}

        if response.status_code >= 400:
            return {"ok": False, "error": f"Image fetch failed: {response.status_code}"}

        return {"ok": True, "content": response.content}
