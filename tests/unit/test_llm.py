"""Exercise the actual HTTP client against a local stub server."""

import json
import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from app import llm
from app.llm_cost import usage_scope
from app.main import create_app
from app.tracing import Observation


@pytest.fixture
def gateway(monkeypatch):
    state = {"statuses": [200], "requests": [], "body": {
        "model": "upstream-model", "choices": [{"message": {"content": "Xin chào"}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 4},
    }}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["requests"].append((self.path, self.headers["Authorization"], body))
            statuses = state["statuses"]
            status = statuses.pop(0) if len(statuses) > 1 else statuses[0]
            self.send_response(status)
            for name, value in state.get("headers", {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(json.dumps(state["body"]).encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("LLM_BACKEND", "litellm")
    monkeypatch.setenv("LLM_BASE_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "stub-secret")
    sleeps = []
    monkeypatch.setattr(llm.time, "sleep", sleeps.append)
    state["sleeps"] = sleeps
    yield state
    server.shutdown()
    server.server_close()
    thread.join()


def test_chat(gateway):
    messages = [{"role": "user", "content": "Hello"}]
    result = llm.chat(messages, "local-chat", 0.2)
    assert result.meta["usage_known"] is True
    assert (result.text, result.model, result.input_tokens, result.output_tokens) == (
        "Xin chào", "upstream-model", 12, 4)
    assert gateway["requests"] == [("/v1/chat/completions", "Bearer stub-secret", {
        "messages": messages, "model": "local-chat", "temperature": 0.2})]


@pytest.mark.parametrize("body_model,header_model,expected_model,expected_cost", [
    ("cloud-chat", "openai/gpt-6-luna", "openai/gpt-6-luna", 2.8e-6),
    ("gpt-6-luna", None, "gpt-6-luna", 2.8e-6),
    ("gpt-6-luna", "", "gpt-6-luna", 2.8e-6),
    ("cloud-chat", "openai/gpt-4.1-mini-2025-04-14", "openai/gpt-4.1-mini-<ACCOUNT_NUMBER>", 9.6e-6),
    ("gpt-4.1-mini-2025-04-14", None, "gpt-4.1-mini-<ACCOUNT_NUMBER>", 9.6e-6),
    ("cloud-chat", "private-001204012345", "private-<CCCD>", None),
    ("cloud-chat", None, "cloud-chat", None),
    ("local-chat", "ollama_chat/qwen2.5:3b", "ollama_chat/qwen2.5:3b", 0.0),
])
def test_gateway_model_cost_before_masking(gateway, body_model, header_model, expected_model, expected_cost):
    gateway["body"]["model"] = body_model
    gateway["body"]["usage"] = {"prompt_tokens": 8, "completion_tokens": 4}
    if header_model is not None:
        gateway["headers"] = {"X-LiteLLM-Model-Name": header_model}
    attributes = {}

    class Span:
        def set_attribute(self, key, value):
            attributes[key] = value

    with usage_scope() as usage:
        result = llm.chat([], "cloud-chat")
        Observation(Span()).generation(result)
        assert usage.fields() == {
            "input_tokens": 8, "output_tokens": 4,
            "cost_usd": None if expected_cost is None else pytest.approx(expected_cost),
        }
    assert result.model == expected_model
    assert attributes["langfuse.observation.model.name"] == expected_model
    if expected_cost is None:
        assert "langfuse.observation.cost_details" not in attributes
    else:
        assert json.loads(attributes["langfuse.observation.cost_details"])["total"] == pytest.approx(expected_cost)
    assert "2025-04-14" not in repr(result) + json.dumps(attributes)
    assert "001204012345" not in repr(result) + json.dumps(attributes)


def test_gateway_model_price_stays_unknown_without_usage(gateway):
    gateway["headers"] = {"x-litellm-model-name": "openai/gpt-6-luna"}
    del gateway["body"]["usage"]
    with usage_scope() as usage:
        Observation().generation(llm.chat([], "cloud-chat"))
        assert usage.cost_usd is None


@pytest.mark.parametrize("model,expected", [
    ("openai/gpt-6-luna", 2.8e-6), ("openai/gpt-4.1-mini-2025-04-14", 9.6e-6),
])
def test_gateway_header_cost_reaches_http_audit(gateway, model, expected):
    gateway["headers"] = {"x-litellm-model-name": model}
    gateway["body"]["model"] = "cloud-chat"
    gateway["body"]["usage"] = {"prompt_tokens": 8, "completion_tokens": 4}
    gateway["body"]["choices"][0]["message"]["content"] = json.dumps({
        "answer": "Hello", "intent": "other", "needs_human": False,
    })
    with TestClient(create_app()) as client:
        response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200
    with sqlite3.connect(os.environ["AUDIT_DB_PATH"]) as connection:
        row = connection.execute("SELECT input_tokens, output_tokens, cost_usd FROM audit_log").fetchone()
    assert row == (8, 4, pytest.approx(expected))


@pytest.mark.parametrize("status", [429, 500, 503, 599])
def test_retry_then_success(gateway, status):
    gateway["statuses"] = [status, status, 200]
    assert llm.chat([], "cloud-chat").text == "Xin chào"
    assert len(gateway["requests"]) == 3
    assert gateway["sleeps"] == [0.5, 1.0]
    assert all(request[2] == {
        "messages": [], "model": "cloud-chat", "temperature": 0.0, "reasoning_effort": "none",
    } for request in gateway["requests"])


@pytest.mark.parametrize("status,count", [(429, 3), (503, 3), (400, 1), (401, 1), (403, 1), (302, 1)])
def test_failure_is_bounded_and_safe(gateway, status, count):
    gateway["statuses"] = [status]
    gateway["body"] = {"error": "stub-secret private message"}
    with pytest.raises(llm.LLMError, match=f"HTTP {status}") as error:
        llm.chat([], "cloud-chat")
    assert len(gateway["requests"]) == count
    assert "stub-secret" not in str(error.value)
    assert "private" not in str(error.value)
    assert isinstance(error.value, llm.LLMRateLimitError) == (status == 429)


@pytest.mark.parametrize("body", [{}, {"choices": []}, {"choices": None}, {
    "model": "m", "choices": [{"message": {"content": None}}]}, {
    "model": "m", "choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": -1}}])
def test_invalid_response(gateway, body):
    gateway["body"] = body
    with pytest.raises(llm.LLMError, match="Invalid"):
        llm.chat([], "cloud-chat")
    assert len(gateway["requests"]) == 1


def test_optional_usage_and_v1_url(gateway, monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", llm.os.environ["LLM_BASE_URL"] + "/v1/")
    del gateway["body"]["usage"]
    result = llm.chat([], "cloud-chat")
    assert result.input_tokens == result.output_tokens == 0
    assert result.meta["usage_known"] is False
    assert gateway["requests"][0][0] == "/v1/chat/completions"


def test_fake_never_calls_network(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "fake")
    monkeypatch.delenv("LITELLM_MASTER_KEY", raising=False)
    monkeypatch.setattr(llm.httpx, "Client", lambda **kw: pytest.fail("Unexpected network"))
    assert llm.chat([], "local-chat").model == "fake/local-chat"


def test_invalid_backend_and_missing_key(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "unknown")
    with pytest.raises(llm.LLMError, match="Unsupported"):
        llm.chat([], "cloud-chat")
    monkeypatch.setenv("LLM_BACKEND", "litellm")
    monkeypatch.delenv("LITELLM_MASTER_KEY", raising=False)
    with pytest.raises(llm.LLMError, match="required"):
        llm.chat([], "cloud-chat")


def test_transport_failure_is_safe(gateway, monkeypatch):
    def fail(*args, **kwargs):
        raise llm.httpx.ReadTimeout("stub-secret private prompt")

    monkeypatch.setattr(llm.httpx.Client, "post", fail)
    with pytest.raises(llm.LLMError, match="transport failure") as error:
        llm.chat([], "local-chat")
    assert "stub-secret" not in str(error.value)
    assert str(error.value) == "LLM gateway transport failure (ReadTimeout)"
    assert gateway["sleeps"] == []


@pytest.mark.parametrize("alias", ["local-chat", "cloud-chat"])
def test_pii_is_masked_before_actual_gateway_request_and_on_output(gateway, alias):
    secret = "001204012345"
    escaped = "".join(f"\\u{ord(c):04x}" for c in secret)
    messages = [{"role": "user", "content": f'{{"customer":"{escaped}"}}'},
                {"role": "system", "content": f"CCCD: {secret}"}]
    original = json.loads(json.dumps(messages))
    gateway["body"]["choices"][0]["message"]["content"] = f'{{"answer":"{escaped}"}}'
    result = llm.chat(messages, alias)
    sent = gateway["requests"][0][2]["messages"]
    assert secret not in json.dumps(sent) and escaped not in json.dumps(sent)
    assert json.loads(sent[0]["content"])["customer"] == "<CCCD>"
    assert sent[1]["content"] == "CCCD: <CCCD>"
    assert json.loads(result.text) == {"answer": "<CCCD>"}
    assert messages == original  # Do not mutate the caller's messages.
    assert (result.input_tokens, result.output_tokens) == (12, 4)
