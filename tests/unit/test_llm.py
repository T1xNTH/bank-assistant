"""Exercise the actual HTTP client against a local stub server."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app import llm


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
    assert (result.text, result.model, result.input_tokens, result.output_tokens) == (
        "Xin chào", "upstream-model", 12, 4)
    assert gateway["requests"] == [("/v1/chat/completions", "Bearer stub-secret", {
        "messages": messages, "model": "local-chat", "temperature": 0.2})]


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
