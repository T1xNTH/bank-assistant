"""Runtime settings read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    rag_backend: str = os.getenv("RAG_BACKEND", "fake")  # fake | real
    llm_backend: str = os.getenv("LLM_BACKEND", "fake")  # fake | litellm
    auth_backend: str = field(default_factory=lambda: os.getenv("AUTH_BACKEND", "fake"))  # fake | apikey
    api_keys_file: str = field(default_factory=lambda: os.getenv("API_KEYS_FILE", "config/api_keys.json"))


def get_settings() -> Settings:
    return Settings()
