"""Exercise /chat with deterministic LLM replies and the runtime fake backend."""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import yaml
from fastapi.testclient import TestClient

from app.deps import get_llm
from app.llm import LLMError
from app.log_config import JsonFormatter
from app.main import create_app
from tests.fakes import FakeLLM


@pytest.fixture
def application():
    return create_app()


def install_fake(application, output):
    fake = FakeLLM(reply=json.dumps(output, ensure_ascii=False))
    application.dependency_overrides[get_llm] = lambda: fake
    return fake


@pytest.mark.parametrize("intent", ["question", "complaint", "request", "other"])
@pytest.mark.parametrize("needs_human", [False, True])
def test_chat_returns_contract_shape(application, intent, needs_human):
    output = {"answer": "Vui lòng liên hệ nhân viên.", "intent": intent, "needs_human": needs_human}
    fake = install_fake(application, output)
    response = TestClient(application).post("/chat", json={"message": "Tôi cần hỗ trợ"})
    assert response.status_code == 200
    body = response.json()
    assert body == {**output, "model": "fake/cloud-chat", "latency_ms": body["latency_ms"]}
    assert type(body["latency_ms"]) is int and body["latency_ms"] >= 0
    messages, alias = fake.calls[0]
    assert len(fake.calls) == 1 and alias == "cloud-chat"
    assert [message["role"] for message in messages] == ["system", "user"]
    assert messages[1]["content"] == "Tôi cần hỗ trợ"


@pytest.mark.parametrize("payload", [{}, {"message": ""}, {"message": "x" * 4001}, {"message": 42},
                                     {"message": None}, {"message": ["hello"]}])
def test_invalid_request_is_rejected_before_llm(application, payload):
    fake = install_fake(application, {})
    response = TestClient(application).post("/chat", json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"
    assert fake.calls == []


def test_message_at_length_limit_is_preserved(application):
    fake = install_fake(application, {"answer": "ok", "intent": "other", "needs_human": False})
    message = "a" * 4000
    assert TestClient(application).post("/chat", json={"message": message}).status_code == 200
    assert fake.calls[0][0][1]["content"] == message


@pytest.mark.parametrize("output", [
    {}, [], None,
    {"answer": "ok", "intent": "unknown", "needs_human": False},
    {"answer": "ok", "intent": "question", "needs_human": "false"},
    {"answer": "ok", "intent": "question", "needs_human": 1},
    {"answer": 42, "intent": "question", "needs_human": False},
    {"answer": "ok", "intent": "question", "needs_human": False, "model": "spoofed"},
])
def test_invalid_output_returns_safe_service_error(application, output):
    install_fake(application, output)
    response = TestClient(application).post("/chat", json={"message": "hello"})
    assert response.status_code == 503
    assert response.json() == {"error": {"code": "SERVICE_UNAVAILABLE", "message": "Service Unavailable"}}


@pytest.mark.parametrize("reply", ["not JSON", '```json\n{"answer":"ok"}\n```', '{"answer":'])
def test_malformed_output_is_rejected(application, reply):
    application.dependency_overrides[get_llm] = lambda: FakeLLM(reply=reply)
    response = TestClient(application).post("/chat", json={"message": "hello"})
    assert response.status_code == 503
    assert reply not in response.text


def test_llm_failure_does_not_expose_input_or_provider_error(application, caplog):
    secret = "private-provider-and-customer-data"

    class BrokenLLM:
        def chat(self, *args, **kwargs):
            raise LLMError(secret)

    application.dependency_overrides[get_llm] = BrokenLLM
    with caplog.at_level(logging.INFO):
        response = TestClient(application).post("/chat", json={"message": secret})
    assert response.status_code == 503
    assert secret not in response.text
    logs = "\n".join(JsonFormatter().format(r) for r in caplog.records if r.name.startswith("app."))
    assert secret not in logs


def test_real_auth_rejects_missing_key_before_llm(application, monkeypatch):
    monkeypatch.setenv("AUTH_BACKEND", "apikey")
    fake = install_fake(application, {})
    response = TestClient(application).post("/chat", json={"message": "hello"})
    assert response.status_code == 401
    assert fake.calls == []


def test_runtime_fake_requires_no_gateway(application, monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "fake")
    monkeypatch.delenv("LITELLM_MASTER_KEY", raising=False)
    from app import llm

    monkeypatch.setattr(llm.httpx, "Client", lambda **kwargs: pytest.fail("Unexpected gateway call"))
    response = TestClient(application).post("/chat", json={"message": "Xin chào"})
    assert response.status_code == 200
    assert response.json()["model"] == "fake/cloud-chat"
    assert response.json()["intent"] == "question"
    assert response.json()["needs_human"] is False


def test_chat_uses_shared_gateway_client(application, monkeypatch):
    output = {"answer": "Liên hệ nhân viên hỗ trợ.", "intent": "complaint", "needs_human": True}
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append((self.path, self.headers["Authorization"],
                             json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "model": "upstream-test-model", "choices": [{"message": {"content": json.dumps(output)}}],
            }).encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("LLM_BACKEND", "litellm")
    monkeypatch.setenv("LLM_BASE_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "synthetic-gateway-key")
    try:
        response = TestClient(application).post("/chat", json={"message": "Tôi cần khiếu nại"})
        assert response.status_code == 200
        assert response.json() == {
            **output, "model": "upstream-test-model", "latency_ms": response.json()["latency_ms"],
        }
        assert len(requests) == 1
        path, authorization, payload = requests[0]
        assert path == "/v1/chat/completions" and authorization == "Bearer synthetic-gateway-key"
        assert payload["model"] == "cloud-chat" and payload["temperature"] == 0.0
        assert payload["messages"][1] == {"role": "user", "content": "Tôi cần khiếu nại"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_chat_schema_matches_authoritative_openapi(application):
    from pathlib import Path

    contract = yaml.safe_load(Path("docs/04-api/openapi.yaml").read_text(encoding="utf-8"))
    generated = application.openapi()
    for name in ("ChatRequest", "ChatResponse"):
        expected = contract["components"]["schemas"][name]
        actual = generated["components"]["schemas"][name]
        assert set(actual["required"]) == set(expected["required"])
        assert set(actual["properties"]) == set(expected["properties"])
        for field, schema in expected["properties"].items():
            assert {key: actual["properties"][field][key] for key in schema} == schema
