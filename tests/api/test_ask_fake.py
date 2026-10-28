from fastapi.testclient import TestClient

from app.contracts import REFUSAL
from app.main import app

client = TestClient(app)


def test_ask_returns_contract_shape_with_citation():
    body = client.post("/ask", json={"question": "Phí thường niên thẻ?"}).json()
    assert body["found"] is True
    assert body["citations"][0] == {"n": 1, "source": "bieu-phi-the.pdf", "page": 3, "score": 0.91}
    assert set(body) == {"answer", "found", "citations", "retrieval_mode", "route", "latency_ms", "trace_id"}


def test_ask_refusal_is_200_with_found_false():
    r = client.post("/ask", json={"question": "Câu hỏi ngoài phạm vi"})
    assert r.status_code == 200
    assert r.json()["found"] is False and r.json()["answer"] == REFUSAL


def test_ask_rejects_empty_question():
    assert client.post("/ask", json={"question": ""}).status_code == 400
