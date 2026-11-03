"""Authenticated API keys share a Redis budget across synchronous and queued requests."""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError

from app.deps import get_answerer, get_llm
from app.fakes_runtime import CannedAnswerer
from app.main import create_app
from tests.fakes import FakeLLM

KEY = "synthetic-rate-key-a"
OTHER_KEY = "synthetic-rate-key-b"
PAYLOADS = {"/ask": {"question": "Fee?"}, "/chat": {"message": "Hello"}, "/ask/jobs": {"question": "Fee?"}}


@pytest.fixture
def api(monkeypatch, tmp_path, isolated_api_redis):
    registry = tmp_path / "keys.json"
    # Two keys deliberately map to the same user: their budgets must stay independent.
    registry.write_text(json.dumps({
        hashlib.sha256(key.encode()).hexdigest(): {"user_id": "staff", "department": "credit", "role": "staff"}
        for key in (KEY, OTHER_KEY)
    }), encoding="utf-8")
    monkeypatch.setenv("AUTH_BACKEND", "apikey")
    monkeypatch.setenv("API_KEYS_FILE", str(registry))
    monkeypatch.setenv("API_KEY_RPM", "1")
    monkeypatch.setenv("API_KEY_BURST", "1")
    llm = FakeLLM(reply=json.dumps({"answer": "ok", "intent": "other", "needs_human": False}))
    calls = []

    class Answerer(CannedAnswerer):
        def answer(self, *args, **kwargs):
            calls.append(args)
            return super().answer(*args, **kwargs)

    application = create_app()
    application.dependency_overrides[get_llm] = lambda: llm
    application.dependency_overrides[get_answerer] = Answerer
    with TestClient(application) as client:
        yield client, isolated_api_redis, llm, calls


def post(client, endpoint, key=KEY):
    return client.post(endpoint, json=PAYLOADS[endpoint], headers={"X-API-Key": key})


@pytest.mark.parametrize("endpoint", PAYLOADS)
def test_per_key_limit_retry_after_and_no_backend_call(api, endpoint):
    client, connection, llm, calls = api
    assert post(client, endpoint).status_code == (202 if endpoint == "/ask/jobs" else 200)
    before = (len(llm.calls), len(calls), connection.llen("rq:queue:ask-default"))
    denied = post(client, endpoint)
    assert denied.status_code == 429
    assert 1 <= int(denied.headers["Retry-After"]) <= 60
    assert denied.json()["error"]["code"] == "RATE_LIMITED"
    assert before == (len(llm.calls), len(calls), connection.llen("rq:queue:ask-default"))
    assert post(client, endpoint, OTHER_KEY).status_code == (202 if endpoint == "/ask/jobs" else 200)
    keys = list(connection.scan_iter("ask:api:rate:*"))
    assert set(keys) == {f"ask:api:rate:{hashlib.sha256(key.encode()).hexdigest()}".encode()
                         for key in (KEY, OTHER_KEY)}
    stored = b"\n".join(key + connection.dump(key) for key in connection.scan_iter())
    assert KEY.encode() not in stored and OTHER_KEY.encode() not in stored


@pytest.mark.parametrize("first,second", [(a, b) for a in PAYLOADS for b in PAYLOADS if a != b])
def test_budget_shared_across_endpoints_and_app_instances(api, first, second):
    client, _, _, _ = api
    assert post(client, first).status_code in (200, 202)
    with TestClient(create_app()) as other:
        assert post(other, second).status_code == 429


@pytest.mark.parametrize("endpoint", ["/ask", "/chat"])
def test_redis_failure_returns_safe_503_before_backend(api, monkeypatch, endpoint):
    client, connection, llm, calls = api

    def unavailable(*args, **kwargs):
        raise ConnectionError("private-redis-diagnostic")

    monkeypatch.setattr(connection, "pipeline", unavailable)
    response = post(client, endpoint)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "private-redis-diagnostic" not in response.text
    assert llm.calls == calls == []


@pytest.mark.parametrize("endpoint", ["/ask", "/chat"])
def test_authentication_precedes_rate_limit(api, monkeypatch, endpoint):
    client, connection, llm, calls = api
    monkeypatch.setattr(connection, "pipeline", lambda: pytest.fail("Unauthenticated rate-limit access"))
    for key in ("", "invalid-key"):
        assert post(client, endpoint, key).status_code == 401
    assert llm.calls == calls == []
