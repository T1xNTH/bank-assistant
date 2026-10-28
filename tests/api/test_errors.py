import json
import logging
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.deps import get_answerer
from app.log_config import JsonFormatter
from app.main import create_app
from app.schemas import AskResponse


@pytest.fixture
def application():
    return create_app()


def assert_error(response, status, code):
    assert response.status_code == status
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    assert UUID(response.headers["x-request-id"]).version == 4


@pytest.mark.parametrize(
    "body",
    [{}, {"question": ""}, {"question": "q", "top_k": 0}, {"question": "q", "mode": "unknown"}],
)
def test_invalid_body_returns_400_envelope(application, body):
    assert_error(TestClient(application).post("/ask", json=body), 400, "BAD_REQUEST")


def test_invalid_json_returns_400_envelope(application):
    response = TestClient(application).post(
        "/ask", content=b'{"question":', headers={"content-type": "application/json"}
    )
    assert_error(response, 400, "BAD_REQUEST")


def test_not_found_does_not_echo_private_path_or_query(application, caplog):
    secret = "customer-015204000835"
    with caplog.at_level(logging.INFO):
        response = TestClient(application).get(f"/{secret}?account={secret}")
    assert_error(response, 404, "NOT_FOUND")
    assert secret not in response.text
    assert secret not in "\n".join(
        JsonFormatter().format(record) for record in caplog.records if record.name.startswith("app.")
    )


@pytest.mark.parametrize(
    ("status", "code"), [(401, "UNAUTHORIZED"), (403, "FORBIDDEN"), (409, "CONFLICT"), (503, "SERVICE_UNAVAILABLE")]
)
def test_http_errors_keep_status_without_exposing_detail(application, status, code):
    @application.get("/denied")
    async def denied():
        raise HTTPException(status, detail={"private": "015204000835"})

    response = TestClient(application).get("/denied")
    assert_error(response, status, code)
    assert "015204000835" not in response.text


def test_rate_limit_preserves_retry_after(application):
    @application.get("/limited")
    async def limited():
        raise HTTPException(429, headers={"Retry-After": "12"})

    response = TestClient(application).get("/limited")
    assert_error(response, 429, "RATE_LIMITED")
    assert response.headers["retry-after"] == "12"


def test_method_not_allowed_preserves_allow_header(application):
    response = TestClient(application).post("/health")
    assert_error(response, 405, "METHOD_NOT_ALLOWED")
    assert "GET" in response.headers["allow"]


def test_unhandled_failure_returns_safe_500_with_matching_log_id(application, caplog):
    secret = "provider-key-and-customer-015204000835"

    class BrokenAnswerer:
        def answer(self, *args):
            raise RuntimeError(secret)

    application.dependency_overrides[get_answerer] = BrokenAnswerer
    with caplog.at_level(logging.INFO):
        response = TestClient(application).post("/ask", json={"question": secret})
    assert_error(response, 500, "INTERNAL_ERROR")
    assert secret not in response.text
    logs = [json.loads(JsonFormatter().format(record)) for record in caplog.records if record.name.startswith("app.")]
    assert {log["request_id"] for log in logs} == {response.headers["x-request-id"]}
    assert any(log.get("exception_type") == "RuntimeError" for log in logs)
    failure = next(log for log in logs if log["message"] == "request.failed")
    assert any(
        frame.startswith("test_errors.py:") and frame.endswith(":answer") for frame in failure["exception_frames"]
    )
    assert all("/" not in frame and "\\" not in frame for frame in failure["exception_frames"])
    assert secret not in json.dumps(logs)


def test_response_validation_failure_is_500_not_client_400(application):
    @application.get("/broken-output", response_model=AskResponse)
    async def broken_output():
        return {}

    assert_error(TestClient(application).get("/broken-output"), 500, "INTERNAL_ERROR")


def test_request_validation_does_not_echo_input(application, caplog):
    secret = "015204000835"
    with caplog.at_level(logging.INFO):
        response = TestClient(application).post("/ask", json={"question": "q", "top_k": secret})
    assert_error(response, 400, "BAD_REQUEST")
    assert secret not in response.text
    assert secret not in "\n".join(
        JsonFormatter().format(record) for record in caplog.records if record.name.startswith("app.")
    )
