"""T-042 Streamlit UI driven by AppTest against the real FastAPI app (API-key auth, scripted model, CI)."""

import hashlib
import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app import deps
from app.contracts import LLMResult
from app.fakes_runtime import CannedAnswerer
from app.main import create_app
from scripts.seed_core_banking import seed

st_testing = pytest.importorskip("streamlit.testing.v1")
UI = Path(__file__).resolve().parents[2] / "ui"
if str(UI) not in sys.path:
    sys.path.append(str(UI))  # appended: ui/app.py must not shadow the app package
import ui_api  # noqa: E402

KEYS = {"UI_KEY_CREDIT_STAFF": "ui-staff-key", "UI_KEY_APPROVER": "ui-approver-key"}
STAFF, APPROVER = "Nhân viên tín dụng (credit, staff)", "Người duyệt (approver)"
TICKET = json.dumps({"tool": "tao_ticket", "args": {"summary": "Mất thẻ, gọi 0912345678"}})


class ScriptedModel:
    def __init__(self):
        self.replies = []

    def chat(self, messages, alias, temperature=0):
        assert self.replies, "unexpected model call"
        return LLMResult(text=self.replies.pop(0), model="scripted/" + alias)


@pytest.fixture
def api(tmp_path, monkeypatch):
    users = {"ui-staff-key": ("staff-1", "staff"), "ui-approver-key": ("approver-1", "approver")}
    registry = tmp_path / "keys.json"
    registry.write_text(json.dumps({
        hashlib.sha256(key.encode()).hexdigest(): {"user_id": user, "department": "credit", "role": role}
        for key, (user, role) in users.items()
    }))
    monkeypatch.setenv("AUTH_BACKEND", "apikey")
    monkeypatch.setenv("API_KEYS_FILE", str(registry))
    monkeypatch.setenv("CORE_BANKING_DB_PATH", str(seed(tmp_path / "bank.db")))
    monkeypatch.setenv("TICKETS_DB_PATH", str(tmp_path / "tickets.db"))
    monkeypatch.setenv("AGENT_CHECKPOINT_DB_PATH", str(tmp_path / "checkpoints.db"))
    for var in ui_api.ROLES.values():
        monkeypatch.delenv(var, raising=False)
    for var, key in KEYS.items():
        monkeypatch.setenv(var, key)
    model = ScriptedModel()
    app = create_app()
    app.dependency_overrides[deps.get_llm] = lambda: model
    app.dependency_overrides[deps.get_answerer] = CannedAnswerer
    with TestClient(app) as client:
        def forward(request):
            response = client.request(
                request.method, request.url.raw_path.decode(), content=request.content,
                headers={k: v for k, v in request.headers.items() if k.lower() in ("x-api-key", "content-type")},
            )
            return httpx.Response(response.status_code, headers=response.headers, content=response.content)

        monkeypatch.setattr(ui_api, "TRANSPORT", httpx.MockTransport(forward))
        yield model


def run_app():
    at = st_testing.AppTest.from_file(str(UI / "app.py"), default_timeout=30)
    return at.run()


def as_role(at, label):
    at.sidebar.radio(key="role").set_value(label)
    return at.run()


def texts(at):
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption] + [e.value for e in at.error]
    parts += [w.value for w in at.warning] + [s.value for s in at.success] + [i.value for i in at.info]
    return "\n".join(str(p) for p in parts)


def test_roles_come_from_env_and_missing_keys_hide_roles(api):
    at = run_app()
    assert not at.exception
    assert at.sidebar.radio(key="role").options == [STAFF, APPROVER]


def test_no_key_configured_shows_setup_error(api, monkeypatch):
    for var in KEYS:
        monkeypatch.delenv(var)
    at = run_app()
    assert not at.exception and "UI_KEY_APPROVER" in at.error[0].value


def test_ask_shows_answer_citation_file_page_and_route(api):
    at = run_app()
    at.text_area[0].set_value("Phí thường niên thẻ chuẩn?")
    at.button[0].click()  # form submit "Hỏi"
    at = at.run()
    assert not at.exception
    assert "100.000 VND [1]" in texts(at)
    assert "Route: **cloud" in texts(at)
    row = at.table[0].value.iloc[0].to_dict()
    assert (row["[n]"], row["Tài liệu"], row["Trang"]) == (1, "bieu-phi-the.pdf", 3)


def test_force_local_is_sent_and_route_local_shown(api):
    at = run_app()
    at.text_area[0].set_value("Phí thường niên thẻ chuẩn?")
    at.checkbox[0].check()
    at.button[0].click()
    at = at.run()
    assert "Route: **local" in texts(at)


def test_api_error_is_shown_without_crashing(api, monkeypatch):
    monkeypatch.setenv("UI_KEY_CREDIT_STAFF", "wrong-key")
    at = run_app()
    at.text_area[0].set_value("Phí?")
    at.button[0].click()
    at = at.run()
    assert not at.exception and "HTTP 401" in at.error[0].value


def test_agent_pending_action_then_approver_approves(api):
    api.replies.append(TICKET)
    at = run_app()
    at.text_area[1].set_value("Mất thẻ, gọi 0912345678")
    at.button(key="FormSubmitter:agent-Gửi").click()
    at = at.run()
    assert not at.exception
    assert "tao_ticket" in texts(at) and "Đang chờ người duyệt" in texts(at)
    assert "0912345678" not in json.dumps([j.value for j in at.json])

    at = as_role(at, APPROVER)
    [thread_id] = at.session_state["threads"].keys()
    assert "người yêu cầu: " + STAFF in texts(at)
    at.button(key=f"approve-{thread_id}").click()
    at = at.run()
    assert not at.exception
    assert "đã duyệt" in texts(at)
    assert at.session_state["threads"][thread_id]["status"] == "completed"
    assert "Không có hành động nào đang chờ duyệt" in texts(at)


def test_approver_rejects_with_comment(api):
    api.replies.append(TICKET)
    at = run_app()
    at.text_area[1].set_value("Mất thẻ")
    at.button(key="FormSubmitter:agent-Gửi").click()
    at = as_role(at.run(), APPROVER)
    [thread_id] = at.session_state["threads"].keys()
    at.text_input(key=f"comment-{thread_id}").set_value("Chưa đủ thông tin")
    at.button(key=f"reject-{thread_id}").click()
    at = at.run()
    assert "đã từ chối" in texts(at)
    assert "từ chối" in at.session_state["threads"][thread_id]["messages"][-1][1]


def test_staff_does_not_see_approval_panel(api):
    at = run_app()
    assert "Hành động chờ duyệt" not in [s.value for s in at.subheader]


def test_no_api_key_literal_in_ui_source():
    for path in UI.glob("*.py"):
        assert "sk-" not in path.read_text()


def test_connection_failure_is_a_safe_error(monkeypatch):
    def refuse(request):
        raise httpx.ConnectError("boom 0912345678")

    monkeypatch.setattr(ui_api, "TRANSPORT", httpx.MockTransport(refuse))
    with pytest.raises(ui_api.ApiError) as error:
        ui_api.Api("http://api", "k").ask("q")
    assert error.value.status == 0 and "0912345678" not in error.value.message


def pending_thread_from_another_session(api):
    """A staff browser session creates a pending ticket; returns its thread id."""
    api.replies.append(TICKET)
    staff = run_app()
    staff.text_area[1].set_value("Mất thẻ, gọi 0912345678")
    staff.button(key="FormSubmitter:agent-Gửi").click()
    staff = staff.run()
    [thread_id] = staff.session_state["threads"].keys()
    return thread_id


def decide_by_id(at, thread_id, approve, comment=""):
    at.text_input(key="manual-thread").set_value(thread_id)
    at.text_input(key="manual-comment").set_value(comment)
    at.button(key="manual-approve" if approve else "manual-reject").click()
    return at.run()


def test_external_thread_approve_shows_the_agent_result(api, tmp_path):
    thread_id = pending_thread_from_another_session(api)
    at = as_role(run_app(), APPROVER)  # fresh session: the thread is not listed, only reachable by id
    assert thread_id not in at.session_state["threads"]
    at = decide_by_id(at, thread_id, True)
    assert not at.exception
    shown = texts(at)
    assert f"Thread `{thread_id}`: đã duyệt · trạng thái: hoàn tất." in shown
    answer = at.session_state["decided"]["answer"]
    assert answer and f"**Kết quả từ agent:** {answer}" in shown
    import sqlite3
    with sqlite3.connect(tmp_path / "tickets.db") as db:
        [(ticket_id,)] = db.execute("SELECT id FROM tickets").fetchall()
    assert str(ticket_id) in answer  # the created ticket is visible to the approver

    at = at.run()  # an unrelated rerun keeps the result on screen
    assert f"Thread `{thread_id}`: đã duyệt" in texts(at)


def test_external_thread_reject_then_duplicate_decision_is_an_error(api):
    thread_id = pending_thread_from_another_session(api)
    at = decide_by_id(as_role(run_app(), APPROVER), thread_id, False, "Chưa đủ thông tin")
    assert not at.exception
    assert f"Thread `{thread_id}`: đã từ chối · trạng thái: hoàn tất." in texts(at)
    assert "từ chối" in at.session_state["decided"]["answer"]

    at = decide_by_id(at, thread_id, True)  # already decided
    assert not at.exception
    assert f"Thread `{thread_id}`: HTTP 409" in at.error[0].value


def test_unknown_thread_id_is_an_error(api):
    at = decide_by_id(as_role(run_app(), APPROVER), "0" * 32, True)
    assert not at.exception and "HTTP 404" in at.error[0].value
