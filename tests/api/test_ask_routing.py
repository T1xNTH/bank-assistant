"""/ask and the job worker route to local-chat on PII, confidential chunks or force_local (CI, fake LLM)."""

import json

import fakeredis
import pytest
from fastapi.testclient import TestClient
from rq import SimpleWorker
from rq.job import Job
from rq.serializers import JSONSerializer
from rq.timeouts import TimerDeathPenalty

from app.contracts import Hit, User
from app.deps import get_answerer, get_current_user
from app.main import create_app
from app.queue import jobs
from app.rag.answer import RagAnswerer
from tests.fakes import FakeLLM

USER = User("u1", "credit")
PII = {
    "CCCD": "CCCD 079123456789",
    "ACCOUNT_NUMBER": "số tài khoản 0123456789012",
    "PHONE_NUMBER": "số điện thoại 0912345678",
}
RAW = {"079123456789", "0123456789012", "0912345678"}


def hit(classification="public"):
    return Hit("d1", "doc1.pdf", 1, "nội dung", 0.9, "public", classification)


class Retrieve:
    def __init__(self, hits):
        self.hits = hits

    def __call__(self, question, user, k, mode):
        return self.hits[:k]


@pytest.fixture
def ask():
    application = create_app()
    application.dependency_overrides[get_current_user] = lambda: USER

    def post(question, hits=None, **fields):
        hits = [hit()] if hits is None else hits
        llm = FakeLLM("Trả lời [1].")
        application.dependency_overrides[get_answerer] = lambda: RagAnswerer(Retrieve(list(hits)), llm)
        with TestClient(application) as client:
            response = client.post("/ask", json={"question": question, **fields})
        assert response.status_code == 200
        return response.json(), llm

    return post


def sent_to_llm(llm):
    return json.dumps([messages for messages, _ in llm.calls], ensure_ascii=False)


@pytest.mark.parametrize("kind", PII)
def test_pii_in_question_routes_local_with_masked_text(ask, kind):
    body, llm = ask(f"Tra cứu khoản vay cho {PII[kind]} giúp tôi")
    assert body["route"] == "local"
    assert [alias for _, alias in llm.calls] == ["local-chat"]
    sent = sent_to_llm(llm)
    assert f"<{kind}>" in sent and not any(raw in sent for raw in RAW)


def test_confidential_chunk_routes_local(ask):
    body, llm = ask("Hạn mức phê duyệt nội bộ?", hits=[hit("public"), hit("confidential")])
    assert body["route"] == "local"
    assert [alias for _, alias in llm.calls] == ["local-chat"]


@pytest.mark.parametrize("classes", [["public"], ["internal"], ["public", "internal"]])
def test_no_pii_and_non_confidential_chunks_route_cloud(ask, classes):
    body, llm = ask("Phí thường niên thẻ chuẩn?", hits=[hit(c) for c in classes])
    assert body["route"] == "cloud"
    assert [alias for _, alias in llm.calls] == ["cloud-chat"]


def test_force_local_routes_local(ask):
    body, llm = ask("Phí thường niên thẻ chuẩn?", force_local=True)
    assert body["route"] == "local"
    assert [alias for _, alias in llm.calls] == ["local-chat"]


def test_force_local_refusal_still_reports_local(ask):
    body, llm = ask("Phí thường niên thẻ chuẩn?", hits=[], force_local=True)
    assert body["found"] is False and body["route"] == "local" and llm.calls == []


# Worker: PII is detected once at enqueue, before the masked question is persisted.


@pytest.fixture
def queued(monkeypatch):
    connection = fakeredis.FakeRedis()
    queue = jobs.JobQueue(connection, max_length=5)
    application = create_app()
    application.dependency_overrides[jobs.get_job_queue] = lambda: queue
    application.dependency_overrides[jobs.get_current_user] = lambda: USER
    llm = FakeLLM("Trả lời [1].")
    hits = []
    monkeypatch.setattr(jobs, "get_answerer", lambda: RagAnswerer(Retrieve(hits), llm))

    def run(question, classes=("public",), **fields):
        hits[:] = [hit(c) for c in classes]
        llm.calls.clear()
        with TestClient(application) as client:
            job_id = client.post("/ask/jobs", json={"question": question, **fields}).json()["job_id"]
            worker = SimpleWorker([queue.queue], connection=connection, serializer=JSONSerializer)
            worker.death_penalty_class = TimerDeathPenalty
            worker.work(burst=True, with_scheduler=False)
            body = client.get(f"/ask/jobs/{job_id}").json()
        payload = Job.fetch(job_id, connection=connection, serializer=JSONSerializer).args[0]
        assert body["status"] == "done"
        return body["result"], payload, llm

    yield run
    connection.close()


def test_worker_routes_pii_question_local_without_persisting_pii(queued):
    result, payload, llm = queued(f"Tra cứu cho {PII['CCCD']}")
    assert result["route"] == "local"
    assert [alias for _, alias in llm.calls] == ["local-chat"]
    assert payload["force_local"] is True
    assert not any(raw in json.dumps(payload) or raw in sent_to_llm(llm) for raw in RAW)


def test_worker_routes_confidential_chunk_local(queued):
    result, payload, llm = queued("Hạn mức phê duyệt nội bộ?", classes=("confidential",))
    assert result["route"] == "local" and payload["force_local"] is False
    assert [alias for _, alias in llm.calls] == ["local-chat"]


def test_worker_keeps_force_local(queued):
    result, _, llm = queued("Phí thường niên thẻ chuẩn?", force_local=True)
    assert result["route"] == "local"
    assert [alias for _, alias in llm.calls] == ["local-chat"]


def test_worker_routes_plain_question_cloud(queued):
    result, payload, llm = queued("Phí thường niên thẻ chuẩn?", classes=("public", "internal"))
    assert result["route"] == "cloud" and payload["force_local"] is False
    assert [alias for _, alias in llm.calls] == ["cloud-chat"]
