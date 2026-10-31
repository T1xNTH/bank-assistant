"""Resolve actual Compose merges to verify credential boundaries and profiles."""

import json
import os
import secrets
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


def config(*extra):
    command = ["docker", "compose", "--env-file", str(ROOT / ".env.example"),
               "-f", str(ROOT / "infrastructure/compose.yaml"), *extra,
               "config", "--format", "json"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                            env={**os.environ, "COMPOSE_PROFILES": "",
                                 "OPENAI_API_KEY": "test-provider-secret",
                                 "LITELLM_MASTER_KEY": "sk-" + secrets.token_hex(32),
                                 "OPENAI_MODEL": "test-model"})
    # Do not include rendered config in errors: it may contain shell credentials.
    assert result.returncode == 0, "docker compose config failed"
    return json.loads(result.stdout)["services"]


def test_core_excludes_ollama_and_isolates_provider_key(monkeypatch):
    # Host-side tracing URLs must not override the API container's service DNS.
    monkeypatch.setenv("LANGFUSE_BASE_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("AUTH_BACKEND", "apikey")
    services = config()
    assert "litellm" in services
    assert "ollama" not in services
    assert [name for name, service in services.items()
            if "OPENAI_API_KEY" in service.get("environment", {})] == ["litellm"]
    assert services["litellm"]["environment"]["OPENAI_MODEL"] == "openai/test-model"
    assert all("GEMINI_API_KEY" not in service.get("environment", {}) for service in services.values())
    assert services["api"]["environment"]["LLM_BASE_URL"] == "http://litellm:4000"
    assert services["api"]["environment"]["LANGFUSE_BASE_URL"] == "http://langfuse:3000"
    assert services["api"]["environment"]["AUTH_BACKEND"] == "apikey"
    assert services["api"]["environment"]["API_KEYS_FILE"] == "config/api_keys.json"
    assert services["worker"]["environment"] == services["api"]["environment"]
    assert services["worker"]["command"] == ["python", "-m", "app.queue.worker"]
    assert not services["worker"].get("ports")
    registry_mount = next(mount for mount in services["api"]["volumes"] if mount["target"] == "/app/config")
    assert registry_mount["type"] == "bind" and registry_mount["read_only"]
    assert Path(registry_mount["source"]) == ROOT / "config"
    assert all(port["host_ip"] == "127.0.0.1" for service in services.values()
               for port in service.get("ports", []))


def test_profile_enables_persistent_local_server():
    services = config("--profile", "local-llm")
    ollama = services["ollama"]
    assert ollama["volumes"][0]["target"] == "/root/.ollama"
    assert "OPENAI_API_KEY" not in ollama.get("environment", {})
    assert ollama["ports"][0]["host_ip"] == "127.0.0.1"


def test_ci_merge_publishes_no_ports_and_uses_no_cloud_key():
    services = config("-f", str(ROOT / "infrastructure/compose.ci.yaml"))
    assert all(not service.get("ports") for service in services.values())
    assert services["litellm"]["environment"]["OPENAI_API_KEY"] == ""
    assert services["api"]["environment"]["LLM_BACKEND"] == "fake"
