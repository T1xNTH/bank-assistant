"""HTTP client for the demo UI: roles map to API keys read from the environment, never from source.

Each role is one environment variable holding a raw API key issued by ``scripts/make_key.py``.
A role whose variable is unset or blank is not offered. Errors come back as ``ApiError`` with the
API's safe ``{"error": {"code", "message"}}`` message, so the UI never shows raw exception text.

Owner: A — Epic E-016 (T-042).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

# Label shown in the UI -> environment variable with that role's API key.
ROLES: dict[str, str] = {
    "Nhân viên tín dụng (credit, staff)": "UI_KEY_CREDIT_STAFF",
    "Nhân viên nhân sự (hr, staff)": "UI_KEY_HR_STAFF",
    "Người duyệt (approver)": "UI_KEY_APPROVER",
}
APPROVER_ENV = "UI_KEY_APPROVER"
DEFAULT_API_URL = "http://127.0.0.1:8000"
TIMEOUT_S = 180.0  # the local model on CPU can take a while (SRS: chậm, đủ để demo)
# Tests replace this with httpx.MockTransport; None means real network.
TRANSPORT: httpx.BaseTransport | None = None


class ApiError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class Role:
    label: str
    key: str
    approver: bool = False


def available_roles(env: dict[str, str] | None = None) -> list[Role]:
    env = os.environ if env is None else env
    return [
        Role(label, env[var].strip(), var == APPROVER_ENV) for label, var in ROLES.items() if env.get(var, "").strip()
    ]


def api_url(env: dict[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    return (env.get("UI_API_URL", "").strip() or DEFAULT_API_URL).rstrip("/")


class Api:
    def __init__(self, base_url: str, key: str) -> None:
        self.base_url = base_url
        self.key = key

    def _post(self, path: str, body: dict) -> dict:
        try:
            with httpx.Client(base_url=self.base_url, timeout=TIMEOUT_S, transport=TRANSPORT) as client:
                response = client.post(path, json=body, headers={"X-API-Key": self.key})
        except httpx.HTTPError as exc:
            raise ApiError(0, f"Không kết nối được API ({type(exc).__name__})") from None
        if response.status_code != 200:
            raise ApiError(response.status_code, _error_message(response))
        return response.json()

    def ask(self, question: str, force_local: bool = False) -> dict:
        return self._post("/ask", {"question": question, "force_local": force_local})

    def agent(self, message: str, thread_id: str | None = None) -> dict:
        body = {"message": message}
        if thread_id:
            body["thread_id"] = thread_id
        return self._post("/agent", body)

    def decide(self, thread_id: str, approve: bool, comment: str = "") -> dict:
        return self._post(f"/agent/{thread_id}/decision", {"approve": approve, "comment": comment})


def _error_message(response: httpx.Response) -> str:
    try:
        message = response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        message = None
    return f"HTTP {response.status_code}: {message}" if isinstance(message, str) else f"HTTP {response.status_code}"
