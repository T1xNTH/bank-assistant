import os

import pytest

os.environ.setdefault("RAG_BACKEND", "fake")
os.environ.setdefault("LLM_BACKEND", "fake")
os.environ.setdefault("AUTH_BACKEND", "fake")


@pytest.fixture(autouse=True)
def isolated_audit_db(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_DB_PATH", str(tmp_path / "audit.db"))
