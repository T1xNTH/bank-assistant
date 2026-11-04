"""Contract, authentication, safe comments and best-effort scoring."""

import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import tracing
from app.deps import get_current_user
from app.main import create_app
from app.security import pii

TRACE = "1234567890abcdef1234567890abcdef"


@pytest.fixture
def scores(monkeypatch):
    calls = []
    monkeypatch.setattr(tracing, "_runtime", lambda: (
        SimpleNamespace(create_score=lambda **kwargs: calls.append(kwargs)), None,
    ))
    return calls


@pytest.mark.parametrize("score", [-1, 1])
def test_feedback_records_score_and_masks_comment(scores, score):
    response = TestClient(create_app()).post("/feedback", json={
        "trace_id": TRACE, "score": score, "comment": "Gọi 0912345678",
    })
    assert response.status_code == 204 and response.content == b""
    assert scores == [{
        "trace_id": TRACE, "name": "user-feedback", "value": score,
        "data_type": "NUMERIC", "comment": "Gọi <PHONE_NUMBER>",
    }]


@pytest.mark.parametrize("trace", ["unknown", "0912345678", "0" * 32, ""])
def test_unknown_or_invalid_trace_is_safe_204(scores, trace):
    assert TestClient(create_app()).post("/feedback", json={"trace_id": trace, "score": 1}).status_code == 204
    assert scores == []


def test_export_failure_and_missing_keys_are_safe(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("Unknown trace")

    monkeypatch.setattr(tracing, "_runtime", lambda: (SimpleNamespace(create_score=fail), None))
    client = TestClient(create_app())
    assert client.post("/feedback", json={"trace_id": TRACE, "score": -1}).status_code == 204
    monkeypatch.setattr(tracing, "_runtime", lambda: None)
    assert client.post("/feedback", json={"trace_id": TRACE, "score": 1}).status_code == 204


def test_escaped_comment_and_masking_failure_fail_closed(scores, monkeypatch):
    secret = "0912345678"
    escaped = "".join(f"\\u{ord(c):04x}" for c in secret)
    client = TestClient(create_app())
    assert client.post("/feedback", json={"trace_id": TRACE, "score": 1, "comment": escaped}).status_code == 204
    assert secret not in json.dumps(scores) and scores[0]["comment"] == "<PHONE_NUMBER>"
    monkeypatch.setattr(pii, "mask_text", lambda _: (_ for _ in ()).throw(RuntimeError(secret)))
    assert client.post("/feedback", json={"trace_id": TRACE, "score": 1, "comment": secret}).status_code == 204
    assert scores[1]["comment"] == "[REDACTED]"


@pytest.mark.parametrize("payload", [
    {}, {"trace_id": TRACE}, {"trace_id": TRACE, "score": 0},
    *({"trace_id": TRACE, "score": score} for score in (True, "1", 1.0, 2, None)),
    {"trace_id": TRACE, "score": 1, "comment": "x" * 1001},
])
def test_invalid_feedback_is_400_without_export(scores, payload):
    assert TestClient(create_app()).post("/feedback", json=payload).status_code == 400
    assert scores == []


def test_authentication_is_required(scores):
    application = create_app()

    def denied():
        raise HTTPException(status_code=401)

    application.dependency_overrides[get_current_user] = denied
    assert TestClient(application).post("/feedback", json={"trace_id": TRACE, "score": 1}).status_code == 401
    assert scores == []
