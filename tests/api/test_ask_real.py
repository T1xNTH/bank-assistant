"""/ask with RAG_BACKEND=real: startup warm-up, dependency failures as 503, real answerer wiring (CI, no models)."""

import threading

import httpx
import pytest
from fastapi.testclient import TestClient
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from app import main
from app.config import Settings
from app.contracts import REFUSAL, Hit, User
from app.deps import get_answerer, get_current_user
from app.llm import LLMError
from app.rag import answer as ans
from tests.fakes import FakeLLM

USER = User("u1", "credit")


def real_settings(monkeypatch, backend="real"):
    monkeypatch.setattr(main, "get_settings", lambda: Settings(rag_backend=backend))


@pytest.fixture
def warmed(monkeypatch):
    done = threading.Event()
    calls = []

    def fake_warm_up():
        calls.append(threading.current_thread().name)
        done.set()

    monkeypatch.setattr(main, "warm_up", fake_warm_up)
    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    return calls, done


# Startup


def test_real_backend_warms_up_models_in_background(monkeypatch, warmed):
    calls, done = warmed
    real_settings(monkeypatch)
    with TestClient(main.create_app()) as client:
        assert done.wait(5)
        assert client.get("/health").status_code == 200
    assert calls == ["rag-warm-up"]


def test_fake_backend_does_not_warm_up(monkeypatch, warmed):
    calls, _ = warmed
    real_settings(monkeypatch, "fake")
    with TestClient(main.create_app()) as client:
        assert client.get("/health").status_code == 200
    assert calls == []


def test_bad_retrieval_mode_stops_startup(monkeypatch, warmed):
    calls, _ = warmed
    real_settings(monkeypatch)
    monkeypatch.setenv("RETRIEVAL_MODE", "bm25")
    with pytest.raises(ValueError, match="RETRIEVAL_MODE"), TestClient(main.create_app()):
        pass
    assert calls == []


def test_failed_warm_up_is_logged_and_app_still_serves(monkeypatch, caplog):
    done = threading.Event()

    def broken():
        try:
            raise OSError("no space left on device")
        finally:
            done.set()

    monkeypatch.setattr(main, "warm_up", broken)
    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    real_settings(monkeypatch)
    with caplog.at_level("ERROR", logger=main.logger.name), TestClient(main.create_app()) as client:
        assert done.wait(5)
        assert client.get("/health").status_code == 200
    for _ in range(50):  # the log call runs just after done.set() in the worker thread
        if any(r.getMessage() == "rag.warm_up_failed" for r in caplog.records):
            break
        threading.Event().wait(0.02)
    [record] = [r for r in caplog.records if r.getMessage() == "rag.warm_up_failed"]
    assert record.exception_type == "OSError"


def test_warm_up_loads_both_models(monkeypatch):
    from app.rag import embed, rerank

    loaded = []
    monkeypatch.setattr(embed, "_model", lambda: loaded.append("embed"))
    monkeypatch.setattr(rerank, "_model", lambda: loaded.append("rerank"))
    ans.warm_up()
    assert loaded == ["embed", "rerank"]


# Dependency failures


def hit(n):
    return Hit(f"d{n}", f"doc{n}.pdf", n, "nội dung", 0.9, "public")


class Retrieve:
    def __init__(self, hits=None, error=None):
        self.hits, self.error, self.calls = hits or [], error, []

    def __call__(self, question, user, k, mode):
        self.calls.append((question, user, k, mode))
        if self.error:
            raise self.error
        return self.hits


class BrokenLLM:
    def chat(self, messages, alias, temperature=0.0):
        raise LLMError("LLM gateway returned HTTP 502")


QDRANT_ERRORS = [
    ResponseHandlingException(httpx.ConnectError("[Errno 111] Connection refused")),
    UnexpectedResponse(404, "Not Found", b'{"status":{"error":"Collection not found"}}', httpx.Headers()),
]


@pytest.mark.parametrize("error", QDRANT_ERRORS, ids=["connection-refused", "no-collection"])
def test_qdrant_failure_is_answer_unavailable(error):
    with pytest.raises(ans.AnswerUnavailable, match="retrieval") as info:
        ans.RagAnswerer(Retrieve(error=error), FakeLLM()).answer("q", USER)
    assert info.value.__cause__ is error


def test_llm_failure_is_answer_unavailable():
    with pytest.raises(ans.AnswerUnavailable, match="LLM") as info:
        ans.RagAnswerer(Retrieve([hit(1)]), BrokenLLM()).answer("q", USER)
    assert isinstance(info.value.__cause__, LLMError)


def test_other_errors_are_not_hidden():
    with pytest.raises(ValueError, match="k must be"):
        ans.RagAnswerer(Retrieve(error=ValueError("k must be at least 1")), FakeLLM()).answer("q", USER)


def client_with(answerer, user=USER):
    application = main.create_app()
    application.dependency_overrides[get_answerer] = lambda: answerer
    application.dependency_overrides[get_current_user] = lambda: user
    return TestClient(application, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "answerer",
    [
        ans.RagAnswerer(Retrieve(error=QDRANT_ERRORS[0]), FakeLLM()),
        ans.RagAnswerer(Retrieve([hit(1)]), BrokenLLM()),
    ],
    ids=["qdrant", "llm"],
)
def test_ask_returns_503_when_a_dependency_is_down(answerer):
    response = client_with(answerer).post("/ask", json={"question": "Phí phát hành lại thẻ?"})
    assert response.status_code == 503
    assert response.json() == {"error": {"code": "SERVICE_UNAVAILABLE", "message": "Service Unavailable"}}


def test_ask_still_returns_500_for_bugs():
    response = client_with(ans.RagAnswerer(Retrieve(error=KeyError("payload")), FakeLLM())).post(
        "/ask", json={"question": "Phí phát hành lại thẻ?"}
    )
    assert response.status_code == 500


# Real answerer behind /ask


def test_ask_runs_rag_answerer_with_current_user_and_mode():
    retrieve = Retrieve([hit(1), hit(2)])
    client = client_with(ans.RagAnswerer(retrieve, FakeLLM("Phí là 50.000 đ [2].")))
    body = client.post("/ask", json={"question": "Phí phát hành lại thẻ?", "mode": "dense"}).json()
    assert retrieve.calls == [("Phí phát hành lại thẻ?", USER, 5, "dense")]
    assert body["found"] is True
    assert body["answer"] == "Phí là 50.000 đ [2]."
    assert body["citations"] == [{"n": 2, "source": "doc2.pdf", "page": 2, "score": 0.9}]
    assert body["retrieval_mode"] == "dense" and body["route"] == "cloud"


def test_ask_refusal_through_rag_answerer():
    llm = FakeLLM("x [1].")
    body = client_with(ans.RagAnswerer(Retrieve([]), llm)).post("/ask", json={"question": "Giá vàng?"}).json()
    assert (body["found"], body["answer"], body["citations"]) == (False, REFUSAL, [])
    assert llm.calls == []


def test_real_backend_dependency_builds_rag_answerer(monkeypatch):
    from app import deps

    monkeypatch.setattr(deps, "get_settings", lambda: Settings(rag_backend="real"))
    assert isinstance(get_answerer(), ans.RagAnswerer)
