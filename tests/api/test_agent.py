"""T-031 HTTP boundary over real graph/checkpointer/banking SQLite, with scripted model calls."""

import hashlib
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import deps
from app.agent import api as agent_api
from app.agent.graph import AgentResult, AgentService
from app.contracts import LLMResult
from app.fakes_runtime import CannedAnswerer
from app.main import create_app
from app.security import pii
from scripts.seed_core_banking import seed

OWNER = {"X-API-Key": "owner-test-key"}
APPROVER = {"X-API-Key": "approver-test-key"}
OTHER = {"X-API-Key": "other-test-key"}
SELF = {"X-API-Key": "self-test-key"}
TICKET = json.dumps({"tool": "tao_ticket", "args": {"summary": "Mất thẻ, gọi 0912345678"}})
LOAN = json.dumps({"tool": "tinh_lai_vay", "args": {
    "principal": "<ACCOUNT_NUMBER_1>", "annual_rate_percent": 12, "months": 12,
}})


class ScriptedModel:
    def __init__(self):
        self.replies = []
        self.calls = []

    def chat(self, messages, alias, temperature=0):
        self.calls.append((messages, alias))
        assert self.replies, "unexpected model call"
        reply = self.replies.pop(0)
        return LLMResult(text=reply, model="scripted/" + alias)


@pytest.fixture
def api(tmp_path, monkeypatch):
    users = [
        (OWNER, "synthetic-user-1", "staff"), (APPROVER, "approver-1", "approver"),
        (OTHER, "synthetic-user-2", "staff"), (SELF, "synthetic-user-1", "approver"),
    ]
    keys = {hashlib.sha256(headers["X-API-Key"].encode()).hexdigest(): {
        "user_id": user, "department": "credit", "role": role,
    } for headers, user, role in users}
    registry = tmp_path / "keys.json"
    registry.write_text(json.dumps(keys))
    monkeypatch.setenv("AUTH_BACKEND", "apikey")
    monkeypatch.setenv("API_KEYS_FILE", str(registry))
    monkeypatch.setenv("CORE_BANKING_DB_PATH", str(seed(tmp_path / "bank.db")))
    monkeypatch.setenv("TICKETS_DB_PATH", str(tmp_path / "tickets.db"))
    monkeypatch.setenv("AGENT_CHECKPOINT_DB_PATH", str(tmp_path / "checkpoints.db"))
    model = ScriptedModel()

    def application():
        app = create_app()
        app.dependency_overrides[deps.get_llm] = lambda: model
        app.dependency_overrides[deps.get_answerer] = CannedAnswerer
        return app

    app = application()
    with TestClient(app) as client:
        yield client, model, application


def ticket_rows():
    path = Path(os.environ["TICKETS_DB_PATH"])
    if not path.exists():
        return []
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute("SELECT created_by, summary, approved_by FROM tickets").fetchall()


def audits():
    with closing(sqlite3.connect(os.environ["AUDIT_DB_PATH"])) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute("SELECT * FROM audit_log ORDER BY rowid")]


def pending(api):
    client, model, _ = api
    model.replies.append(TICKET)
    response = client.post("/agent", headers=OWNER, json={"message": "Mất thẻ, gọi 0912345678"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending_approval" and body["answer"] is None
    assert body["pending_action"] == {"tool": "tao_ticket", "args": {"summary": "Mất thẻ, gọi <PHONE_NUMBER>"}}
    assert ticket_rows() == []
    return body["thread_id"]


def test_approve_creates_one_ticket_bound_to_authenticated_owner(api):
    client, _, _ = api
    thread = pending(api)
    response = client.post(f"/agent/{thread}/decision", headers=APPROVER, json={"approve": True})
    assert response.status_code == 200
    assert response.json() == {
        "thread_id": thread, "status": "completed",
        "answer": "Đã tạo ticket #1 (trạng thái open) sau khi người duyệt đồng ý.",
        "pending_action": None,
    }
    assert ticket_rows() == [("synthetic-user-1", "Mất thẻ, gọi <PHONE_NUMBER>", "approver-1")]
    second = client.post(f"/agent/{thread}/decision", headers=APPROVER, json={"approve": True})
    assert second.status_code == 409 and second.json()["error"]["code"] == "CONFLICT"
    assert len(ticket_rows()) == 1


def test_reject_writes_nothing_and_audits_actor_and_masked_comment(api):
    client, _, _ = api
    thread = pending(api)
    response = client.post(f"/agent/{thread}/decision", headers=APPROVER,
                           json={"approve": False, "comment": "Gọi 0912345678"})
    assert response.status_code == 200 and "từ chối" in response.json()["answer"]
    assert "<PHONE_NUMBER>" in response.json()["answer"] and ticket_rows() == []
    [start, decision] = audits()
    assert start["user_id"] == "synthetic-user-1" and start["question_masked"] == "Mất thẻ, gọi <PHONE_NUMBER>"
    assert decision["user_id"] == "approver-1" and decision["department"] == "credit"
    assert decision["endpoint"] == "/agent/{thread_id}/decision"
    assert json.loads(decision["question_masked"])["approve"] is False
    assert json.loads(decision["question_masked"])["comment"] == "Gọi <PHONE_NUMBER>"
    assert decision["trace_id"] == response.headers["X-Request-ID"]
    assert client.post(f"/agent/{thread}/decision", headers=APPROVER, json={"approve": True}).status_code == 409


@pytest.mark.parametrize("headers", [OWNER, OTHER, SELF])
def test_staff_and_self_approval_are_denied_and_leave_action_pending(api, headers):
    client, _, _ = api
    thread = pending(api)
    response = client.post(f"/agent/{thread}/decision", headers=headers, json={"approve": True})
    assert response.status_code == 403 and response.json()["error"]["code"] == "FORBIDDEN"
    assert ticket_rows() == []
    assert client.post("/agent", headers=OWNER, json={"message": "Nhắc lại", "thread_id": thread}).json()[
        "status"] == "pending_approval"


def test_role_check_precedes_service_initialization(api):
    client, _, _ = api
    def forbidden_dependency():
        pytest.fail("non-approver must be rejected before resolving the agent service")
    client.app.dependency_overrides[deps.get_agent_service] = forbidden_dependency
    response = client.post("/agent/unknown/decision", headers=OWNER,
                           json={"approve": False, "comment": "Gọi 0912345678"})
    assert response.status_code == 403
    assert "<PHONE_NUMBER>" in audits()[-1]["question_masked"]


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}])
@pytest.mark.parametrize("endpoint,body", [("/agent", {"message": "test"}),
                                         ("/agent/unknown/decision", {"approve": True})])
def test_authentication_required(api, headers, endpoint, body):
    client, _, _ = api
    assert client.post(endpoint, headers=headers, json=body).status_code == 401
    assert client.app.state.agent_service is None


@pytest.mark.parametrize("thread", ["unknown", "0" * 32])
def test_unknown_threads_are_404(api, thread):
    client, _, _ = api
    assert client.post("/agent", headers=OWNER, json={"message": "test", "thread_id": thread}).status_code == 404
    assert client.post(f"/agent/{thread}/decision", headers=APPROVER, json={"approve": True}).status_code == 404


def test_another_users_thread_is_hidden(api):
    client, _, _ = api
    thread = pending(api)
    response = client.post("/agent", headers=OTHER, json={"message": "Cho xem", "thread_id": thread})
    assert response.status_code == 404 and ticket_rows() == []


@pytest.mark.parametrize("body", [{}, {"message": ""}, {"message": "  "}, {"message": "x" * 4001},
                                  {"message": ["private-input"]}, {"message": "x", "thread_id": 1}])
def test_invalid_agent_body_is_400_without_echoing_input(api, body):
    client, _, _ = api
    response = client.post("/agent", headers=OWNER, json=body)
    assert response.status_code == 400
    assert response.json() == {"error": {"code": "BAD_REQUEST", "message": "Invalid request"}}


@pytest.mark.parametrize("body", [{}, {"approve": "true"}, {"approve": 1}, {"approve": "false"},
                                  {"approve": True, "comment": "x" * 501}, {"approve": True, "comment": None}])
def test_invalid_decision_cannot_create_a_ticket(api, body):
    client, _, _ = api
    thread = pending(api)
    assert client.post(f"/agent/{thread}/decision", headers=APPROVER, json=body).status_code == 400
    assert ticket_rows() == []


def test_numbered_amounts_and_history_survive_http_requests(api):
    client, model, _ = api
    model.replies += ['{"answer":"Lãi suất và kỳ hạn là bao nhiêu?"}', LOAN]
    first = client.post("/agent", headers=OWNER, json={"message": "Vay 100.000.000 đồng"}).json()
    service = client.app.state.agent_service
    response = client.post("/agent", headers=OWNER,
                           json={"message": "12% 12 tháng", "thread_id": first["thread_id"]})
    assert response.status_code == 200
    assert "Khoản vay 100.000.000 đ" in response.json()["answer"]
    assert "Kỳ đầu trả 8.884.878,87 đ" in response.json()["answer"]
    assert "answer_source" not in response.json() and "<ACCOUNT_NUMBER>" not in response.json()["answer"]
    assert [alias for _, alias in model.calls] == ["local-chat", "local-chat"]
    assert "100.000.000" not in json.dumps(model.calls)
    assert client.app.state.agent_service is service


def test_rag_citations_and_model_output_pii_are_masked(api, caplog):
    client, model, _ = api
    model.replies += [json.dumps({"tool": "tra_cuu_tai_lieu", "args": {"question": "Phí thẻ?"}}),
                      '{"answer":"Gọi 0912345678"}']
    first = client.post("/agent", headers=OWNER, json={"message": "Phí thẻ, SĐT 0912345678"})
    assert first.status_code == 200 and "[1] bieu-phi-the.pdf, trang 3" in first.json()["answer"]
    second = client.post("/agent", headers=OWNER,
                         json={"message": "Nhắc lại", "thread_id": first.json()["thread_id"]})
    assert second.json()["answer"] == "Gọi <PHONE_NUMBER>"
    assert "0912345678" not in first.text + second.text + caplog.text + json.dumps(audits())
    service = client.app.state.agent_service
    raw = b"".join(path.read_bytes() for path in Path(os.environ["AGENT_CHECKPOINT_DB_PATH"]).parent.glob(
        "checkpoints.db*"))
    assert b"0912345678" not in raw and isinstance(service, AgentService)


def test_concurrent_http_approvals_write_once(api):
    client, _, _ = api
    thread = pending(api)
    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(lambda _: client.post(f"/agent/{thread}/decision", headers=APPROVER,
                                                       json={"approve": True}).status_code, range(4)))
    assert sorted(statuses) == [200, 409, 409, 409] and len(ticket_rows()) == 1


def test_new_application_resumes_pending_checkpoint(api):
    _, _, application = api
    thread = pending(api)
    with TestClient(application()) as restarted:
        response = restarted.post(f"/agent/{thread}/decision", headers=APPROVER, json={"approve": True})
        assert response.status_code == 200 and len(ticket_rows()) == 1
        service = restarted.app.state.agent_service
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        service.checkpointer.conn.execute("SELECT 1")


def test_checkpoint_initialization_failure_is_503_and_private(api, monkeypatch, caplog):
    client, _, _ = api
    def broken(**kwargs):
        raise sqlite3.OperationalError("private-storage-path-0912345678")
    monkeypatch.setattr(deps, "AgentService", broken)
    response = client.post("/agent", headers=OWNER, json={"message": "Gọi 0912345678"})
    assert response.status_code == 503
    assert "private-storage" not in response.text + caplog.text
    assert audits()[-1]["question_masked"] == "Gọi <PHONE_NUMBER>"


def test_masking_failure_stops_before_graph_and_redacts_audit(api, monkeypatch, caplog):
    client, _, _ = api
    def broken(text):
        raise RuntimeError("private-input-0912345678")
    monkeypatch.setattr(pii, "mask_text", broken)
    response = client.post("/agent", headers=OWNER, json={"message": "Gọi 0912345678"})
    assert response.status_code == 503 and client.app.state.agent_service is None
    assert "0912345678" not in response.text + caplog.text + json.dumps(audits())


def test_nested_model_surrogate_is_sanitized_503_not_500(api, caplog):
    client, model, _ = api
    model.replies.append('{"tool":"tra_cuu_giao_dich","args":{"account_ref":["\\ud800"]}}')
    response = client.post("/agent", headers=OWNER, json={"message": "Giao dịch"})
    assert response.status_code == 503 and response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "msgpack" not in response.text + caplog.text


def test_pending_masking_preserves_json_structure_and_masks_string_values(monkeypatch):
    pending_action = {"tool": "tao_ticket", "args": {"summary": "private", "count": 2}}
    masked = 'Quoted "text"\nwith a backslash \\ and <PHONE_NUMBER>'
    monkeypatch.setattr(agent_api, "require_mask_content", lambda text: masked)
    result = agent_api._invoke(lambda: AgentResult(
        thread_id="thread", status="pending_approval", pending_action=pending_action,
    ))
    assert result.model_dump()["pending_action"] == {"tool": "tao_ticket", "args": {"summary": masked, "count": 2}}
    assert pending_action["args"]["summary"] == "private"


def test_pending_masking_failure_returns_503(api, monkeypatch):
    client, _, _ = api
    thread = pending(api)
    original = agent_api.require_mask_content

    def broken_summary(text):
        if "<PHONE_NUMBER>" in text:
            raise agent_api.MaskingError("unavailable")
        return original(text)

    monkeypatch.setattr(agent_api, "require_mask_content", broken_summary)
    response = client.post("/agent", headers=OWNER, json={"message": "Continue", "thread_id": thread})
    assert response.status_code == 503
    assert response.json() == {"error": {"code": "SERVICE_UNAVAILABLE", "message": "Service Unavailable"}}
