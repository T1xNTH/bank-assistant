"""Runtime settings read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    rag_backend: str = os.getenv("RAG_BACKEND", "fake")  # fake | real
    llm_backend: str = os.getenv("LLM_BACKEND", "fake")  # fake | litellm
    auth_backend: str = os.getenv("AUTH_BACKEND", "fake")  # fake | apikey


def get_settings() -> Settings:
    return Settings()
