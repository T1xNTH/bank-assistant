"""Synchronous LLM client; all real requests go through the authenticated gateway."""

from __future__ import annotations

import json
import os
import time

import httpx2 as httpx

from app.contracts import LLMResult
from app.security.masking import mask_content, mask_data, mask_text


class FakeLLM:
    """Deterministic runtime backend requiring no network or credentials."""

    def chat(self, messages: list[dict], alias: str, temperature: float = 0.0) -> LLMResult:
        # Keep the generic fake reply while supporting the /chat JSON instruction.
        from app.chat import CHAT_SYSTEM

        if messages and messages[0] == {"role": "system", "content": CHAT_SYSTEM}:
            return LLMResult(
                text=json.dumps({"answer": "Câu trả lời mẫu.", "intent": "question", "needs_human": False}),
                model=f"fake/{alias}",
            )
        return LLMResult(text="Câu trả lời [1].", model=f"fake/{alias}")


class LLMError(RuntimeError):
    """Public error that never includes gateway bodies or credentials."""


class LLMRateLimitError(LLMError):
    """Typed, sanitized 429 signal for the worker's bounded retry policy."""


def chat(messages: list[dict], alias: str, temperature: float = 0.0) -> LLMResult:
    messages = mask_data(messages)
    backend = os.getenv("LLM_BACKEND", "fake")
    if backend == "fake":
        return FakeLLM().chat(messages, alias, temperature)
    if backend != "litellm":
        raise LLMError("Unsupported LLM_BACKEND")
    key = os.getenv("LITELLM_MASTER_KEY", "")
    if not key:
        raise LLMError("LITELLM_MASTER_KEY is required")
    base = os.getenv("LLM_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
    url = base + ("/chat/completions" if base.endswith("/v1") else "/v1/chat/completions")
    payload = {"messages": messages, "model": alias, "temperature": temperature}
    if alias == "cloud-chat":
        # The configured reasoning model accepts temperature when reasoning is disabled.
        payload["reasoning_effort"] = "none"
    with httpx.Client(timeout=30.0, follow_redirects=False, trust_env=False) as client:
        for attempt in range(3):
            try:
                response = client.post(url, json=payload, headers={"Authorization": f"Bearer {key}"})
            except httpx.HTTPError:
                raise LLMError("LLM gateway transport failure") from None
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt < 2:
                    time.sleep(0.5 * 2**attempt)
                    continue
            if response.status_code != 200:
                if response.status_code == 429:
                    raise LLMRateLimitError("LLM gateway returned HTTP 429")
                raise LLMError(f"LLM gateway returned HTTP {response.status_code}")
            try:
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                model = data["model"]
                usage = data.get("usage") or {}
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                if not isinstance(text, str) or not isinstance(model, str):
                    raise ValueError
                if any(type(n) is not int or n < 0 for n in (input_tokens, output_tokens)):
                    raise ValueError
                return LLMResult(mask_content(text), mask_text(model), input_tokens, output_tokens)
            except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                raise LLMError("Invalid LLM gateway response") from None
    raise LLMError("LLM gateway retry limit reached")
