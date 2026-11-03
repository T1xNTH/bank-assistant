"""LangGraph agent (T-030): tool choice, RAG citations, HITL interrupt before tao_ticket, SQLite checkpointer.

Real graph, real SqliteSaver, real synthetic core banking and ticket SQLite files; the model is scripted.
"""

import json
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest

from app.agent import graph as agent_graph
from app.agent.core_banking import CoreBanking
from app.agent.graph import AgentService, AgentUnavailable, DecisionConflict, ThreadNotFound, sqlite_checkpointer
from app.agent.tickets import TicketStore
from app.contracts import Hit, LLMResult, User
from app.llm import LLMError
from scripts.seed_core_banking import seed
from tests.fakes import FakeAnswerer, FakeRetriever

OWNER = User("synthetic-user-1", "credit")
APPROVER = User("approver-1", "credit", "approver")
LOAN = '{"tool": "tinh_lai_vay", "args": {"principal": 100000000, "annual_rate_percent": 12, "months": 12}}'
DOCS = '{"tool": "tra_cuu_tai_lieu", "args": {"question": "Phí phát hành lại thẻ ghi nợ quốc tế?"}}'
TICKET = '{"tool": "tao_ticket", "args": {"summary": "Khách báo mất thẻ, SĐT 0912345678"}}'


class ScriptedLLM:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, messages, alias, temperature=0.0):
        self.calls.append((messages, alias))
        if not self.replies:
            pytest.fail("unexpected LLM call")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return LLMResult(text=reply, model=f"fake/{alias}")


class SpyAnswerer(FakeAnswerer):
    def __init__(self):
        super().__init__(FakeRetriever([Hit("d1", "dichvsptheghinoqt.pdf", 1, "Phí 50.000 đ", 0.9, "public")]))
        self.calls = []

    def answer(self, question, user, mode=None, force_local=False):
        self.calls.append((question, user, force_local))
        return super().answer(question, user, mode, force_local)


@pytest.fixture
def env(tmp_path):
    bank = CoreBanking(seed(tmp_path / "bank.db"))
    tickets = TicketStore(tmp_path / "tickets.db")
    checkpoints = tmp_path / "checkpoints.db"
    answerer = SpyAnswerer()

    def service(*replies, path=checkpoints):
        llm = ScriptedLLM(*replies)
        svc = AgentService(
            llm=llm, answerer=answerer, bank=bank, tickets=tickets, checkpointer=sqlite_checkpointer(path)
        )
        return svc, llm

    return {"service": service, "tickets": tickets, "answerer": answerer, "checkpoints": checkpoints}


def ticket_rows(tickets):
    if not tickets.path.exists():
        return []
    with closing(sqlite3.connect(tickets.path)) as connection:
        return connection.execute("SELECT created_by, summary, status, approved_by FROM tickets").fetchall()


def pending_thread(env):
    svc, _ = env["service"](TICKET)
    result = svc.run(OWNER, "Tạo ticket: khách báo mất thẻ, SĐT 0912345678")
    assert result.status == "pending_approval"
    return result.thread_id


# Tool choice


def test_document_question_goes_to_rag_and_keeps_citations(env):
    svc, llm = env["service"](DOCS)
    result = svc.run(OWNER, "Phí phát hành lại thẻ ghi nợ quốc tế là bao nhiêu?")
    assert result.status == "completed" and result.pending_action is None
    assert result.answer == "Trả lời [1].\n\nNguồn:\n[1] dichvsptheghinoqt.pdf, trang 1"
    assert env["answerer"].calls == [("Phí phát hành lại thẻ ghi nợ quốc tế?", OWNER, False)]
    assert [alias for _, alias in llm.calls] == ["cloud-chat"]


def test_document_question_without_hits_is_refused(env):
    env["answerer"].retriever.hits = []
    svc, _ = env["service"](DOCS)
    assert svc.run(OWNER, "Giá vàng hôm nay?").answer == "Không tìm thấy thông tin này trong tài liệu nội bộ hiện có."


def test_loan_question_goes_to_the_calculator_and_amounts_are_written_by_code(env):
    svc, llm = env["service"](LOAN)
    result = svc.run(OWNER, "Vay 100 triệu, lãi 12%/năm, 12 tháng trả góp đều thì mỗi tháng trả bao nhiêu?")
    assert result.status == "completed"
    assert "Kỳ đầu trả 8.884.878,87 đ" in result.answer
    assert "Tổng lãi 6.618.546,40 đ" in result.answer
    assert env["answerer"].calls == [] and len(llm.calls) == 1  # no second model pass over the amounts


def test_bad_loan_arguments_are_reported_not_raised(env):
    svc, _ = env["service"]('{"tool": "tinh_lai_vay", "args": {"principal": "<ACCOUNT_NUMBER>", "months": 12}}')
    result = svc.run(OWNER, "Vay 100.000.000 đồng 12 tháng")
    assert result.answer.startswith("Chưa thực hiện được (tinh_lai_vay): Invalid principal")


def test_transactions_use_account_refs_and_route_later_turns_local(env):
    svc, llm = env["service"]('{"tool": "tra_cuu_giao_dich", "args": {"account_ref": "TK1", "limit": 2}}', DOCS)
    result = svc.run(OWNER, "Cho xem 2 giao dịch gần nhất")
    assert result.answer.splitlines() == [
        "2 giao dịch gần nhất:",
        "- 2026-01-05 · TK1 · -50.000 đ · Synthetic transaction 5",
        "- 2026-01-04 · TK1 · 40.000 đ · Synthetic transaction 4",
    ]
    assert "SYN-ACC-001" not in result.answer
    svc.run(OWNER, "Còn phí thẻ thì sao?", result.thread_id)
    assert [alias for _, alias in llm.calls] == ["cloud-chat", "local-chat"]  # customer data now in the history
    assert env["answerer"].calls[-1][2] is True  # the RAG question may quote that data (PR #94 QA F-01)


def test_unknown_account_ref_is_an_error_message(env):
    svc, _ = env["service"]('{"tool": "tra_cuu_giao_dich", "args": {"account_ref": "SYN-ACC-002"}}')
    answer = svc.run(OWNER, "Giao dịch tài khoản SYN-ACC-002").answer
    assert answer == "Chưa thực hiện được (tra_cuu_giao_dich): account_ref must be one of: TK1."


@pytest.mark.parametrize(
    ("reply", "answer"),
    [
        ('{"answer": "Chào anh/chị!"}', "Chào anh/chị!"),
        ("Chào anh/chị!", "Chào anh/chị!"),
        ('{"tool": "xoa_du_lieu", "args": {}}', agent_graph.UNCLEAR),
        ('{"tool": "tinh_lai_vay", "args": "x"}', agent_graph.UNCLEAR),
        ("```json\n" + '{"answer": "Xin chào"}' + "\n```", "Xin chào"),
    ],
    ids=["json-answer", "plain-text", "unknown-tool", "bad-args", "fenced"],
)
def test_direct_replies_and_unknown_tools(env, reply, answer):
    svc, _ = env["service"](reply)
    assert svc.run(OWNER, "Xin chào").answer == answer


def test_pii_in_message_is_masked_and_routes_local(env):
    svc, llm = env["service"](DOCS)
    svc.run(OWNER, "Khách SĐT 0912345678 hỏi phí phát hành lại thẻ")
    messages, alias = llm.calls[0]
    assert alias == "local-chat"
    assert messages[-1]["content"] == "Khách SĐT <PHONE_NUMBER_1> hỏi phí phát hành lại thẻ"
    assert env["answerer"].calls[0][2] is True  # force_local for the RAG answer too


# HITL: tao_ticket only after a decision (NFR-07)


def test_ticket_waits_for_approval_and_writes_nothing(env):
    thread_id = pending_thread(env)
    svc, _ = env["service"]()
    snapshot = svc.run(OWNER, "Nhắc lại", thread_id)  # a pending action blocks new messages; no model call
    assert snapshot.status == "pending_approval"
    assert snapshot.pending_action == {
        "tool": "tao_ticket",
        "args": {"summary": "Khách báo mất thẻ, SĐT <PHONE_NUMBER>"},
    }
    assert not env["tickets"].path.exists()


def test_rejection_writes_nothing_and_cannot_be_decided_twice(env):
    thread_id = pending_thread(env)
    svc, _ = env["service"]()
    result = svc.decide(thread_id, APPROVER, False, "Thiếu thông tin, gọi 0912345678")
    assert result.status == "completed"
    assert (
        result.answer
        == "Người duyệt đã từ chối, không tạo ticket. Ghi chú của người duyệt: Thiếu thông tin, gọi <PHONE_NUMBER>"
    )
    assert ticket_rows(env["tickets"]) == []
    with pytest.raises(DecisionConflict):
        svc.decide(thread_id, APPROVER, True)
    assert ticket_rows(env["tickets"]) == []


def test_approval_creates_one_ticket_for_the_authenticated_owner(env):
    thread_id = pending_thread(env)
    svc, _ = env["service"]()
    result = svc.decide(thread_id, APPROVER, True)
    assert result.status == "completed" and result.answer.startswith("Đã tạo ticket #1 (trạng thái open)")
    assert ticket_rows(env["tickets"]) == [
        ("synthetic-user-1", "Khách báo mất thẻ, SĐT <PHONE_NUMBER>", "open", "approver-1")
    ]
    with pytest.raises(DecisionConflict):
        svc.decide(thread_id, APPROVER, True)
    assert len(ticket_rows(env["tickets"])) == 1


def test_model_cannot_set_ticket_owner_or_approval(env):
    svc, _ = env["service"](
        '{"tool": "tao_ticket", "args": {"summary": "Cấp quyền", "created_by": "approver-1", "approved": true}}'
    )
    thread_id = svc.run(OWNER, "Tạo ticket cấp quyền").thread_id
    assert svc.run(OWNER, "x", thread_id).pending_action == {"tool": "tao_ticket", "args": {"summary": "Cấp quyền"}}
    svc.decide(thread_id, APPROVER, True)
    assert ticket_rows(env["tickets"])[0][0] == "synthetic-user-1"


@pytest.mark.parametrize(
    "who",
    [OWNER, User("staff-2", "credit"), User("synthetic-user-1", "credit", "approver")],
    ids=["owner-staff", "other-staff", "self-approval"],
)
def test_only_another_approver_can_decide(env, who):
    thread_id = pending_thread(env)
    svc, _ = env["service"]()
    with pytest.raises(PermissionError):
        svc.decide(thread_id, who, True)
    assert svc.run(OWNER, "x", thread_id).status == "pending_approval"
    assert not env["tickets"].path.exists()


def test_concurrent_approvals_create_a_single_ticket(env):
    thread_id = pending_thread(env)
    svc, _ = env["service"]()
    start = threading.Barrier(4)

    def approve(_):
        start.wait()
        try:
            return svc.decide(thread_id, APPROVER, True).status
        except DecisionConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = sorted(pool.map(approve, range(4)))
    assert outcomes == ["completed", "conflict", "conflict", "conflict"]
    assert len(ticket_rows(env["tickets"])) == 1


def test_pending_thread_survives_a_restart(env):
    thread_id = pending_thread(env)
    restarted, _ = env["service"]()  # new service and new connection to the same checkpoint file
    assert restarted.decide(thread_id, APPROVER, True).status == "completed"
    assert len(ticket_rows(env["tickets"])) == 1


def test_invalid_ticket_summary_is_not_proposed(env):
    svc, _ = env["service"]('{"tool": "tao_ticket", "args": {"summary": ""}}')
    result = svc.run(OWNER, "Tạo ticket")
    assert result.status == "completed" and result.answer.startswith("Chưa tạo được đề xuất ticket")
    with pytest.raises(DecisionConflict):
        svc.decide(result.thread_id, APPROVER, True)


# Threads


def test_other_users_and_unknown_ids_cannot_reach_a_thread(env):
    thread_id = pending_thread(env)
    svc, _ = env["service"]()
    with pytest.raises(ThreadNotFound):
        svc.run(User("synthetic-user-2", "credit"), "Cho xem", thread_id)
    for bad in ("0" * 32, "not-a-thread", "../x"):
        with pytest.raises(ThreadNotFound):
            svc.run(OWNER, "x", bad)
        with pytest.raises(ThreadNotFound):
            svc.decide(bad, APPROVER, True)


def test_thread_keeps_history_for_the_model(env):
    svc, llm = env["service"]('{"answer": "Anh/chị muốn vay bao nhiêu?"}', LOAN)
    thread_id = svc.run(OWNER, "Tính lãi vay giúp tôi").thread_id
    svc.run(OWNER, "100 triệu, 12%, 12 tháng", thread_id)
    roles = [(m["role"], m["content"]) for m in llm.calls[1][0][1:]]
    assert roles == [
        ("user", "Tính lãi vay giúp tôi"),
        ("assistant", "Anh/chị muốn vay bao nhiêu?"),
        ("user", "100 triệu, 12%, 12 tháng"),
    ]


def test_checkpoint_file_never_stores_raw_pii(env):
    thread_id = pending_thread(env)
    svc, _ = env["service"]()
    svc.decide(thread_id, APPROVER, False, "Gọi 0912345678, CCCD 001204012345")
    raw = checkpoint_bytes(env)
    assert b"0912345678" not in raw and b"001204012345" not in raw


# Errors


@pytest.mark.parametrize("message", ["", "   ", "x" * 4001, None])
def test_invalid_message(env, message):
    svc, _ = env["service"]()
    with pytest.raises(ValueError):
        svc.run(OWNER, message)


def test_gateway_failure_is_agent_unavailable(env):
    svc, _ = env["service"](LLMError("LLM gateway transport failure (ReadTimeout)"))
    with pytest.raises(AgentUnavailable, match=r"^agent unavailable \(LLMError\)$"):
        svc.run(OWNER, "Phí thẻ?")


def test_decision_arguments_are_validated(env):
    thread_id = pending_thread(env)
    svc, _ = env["service"]()
    with pytest.raises(ValueError):
        svc.decide(thread_id, APPROVER, "yes")
    with pytest.raises(ValueError):
        svc.decide(thread_id, APPROVER, True, "x" * 501)
    assert json.loads(json.dumps(svc.run(OWNER, "x", thread_id).pending_action))["tool"] == "tao_ticket"


# Review claude-review-a round 1 (F-01..F-04)


def test_rag_answer_from_confidential_chunks_keeps_later_turns_local(env):
    # F-01: the Answerer routed local; its answer is in the history the next turn sends to the model.
    env["answerer"].retriever.hits = [Hit("d2", "luong-noi-bo.pdf", 3, "Bậc 3", 0.9, "credit", "confidential")]
    svc, llm = env["service"](DOCS, '{"answer": "Không có gì."}')
    thread_id = svc.run(OWNER, "Lương bậc 3 là bao nhiêu?").thread_id
    svc.run(OWNER, "Cảm ơn", thread_id)
    assert [alias for _, alias in llm.calls] == ["cloud-chat", "local-chat"]


def test_public_rag_answer_keeps_cloud(env):
    svc, llm = env["service"](DOCS, '{"answer": "Không có gì."}')
    thread_id = svc.run(OWNER, "Phí thẻ?").thread_id
    svc.run(OWNER, "Cảm ơn", thread_id)
    assert [alias for _, alias in llm.calls] == ["cloud-chat", "cloud-chat"]


@pytest.mark.parametrize("ref", [["TK1"], {"a": 1}, 1])
def test_non_text_account_ref_is_an_error_message(env, ref):
    # F-02: a list from the model used to raise "unhashable type" (a 500).
    reply = json.dumps({"tool": "tra_cuu_giao_dich", "args": {"account_ref": ref}})
    svc, _ = env["service"](reply)
    assert svc.run(OWNER, "Giao dịch").answer.startswith("Chưa thực hiện được (tra_cuu_giao_dich): account_ref")


def test_lone_surrogates_never_reach_the_checkpoint(env):
    # F-02: msgpack cannot store them; the client gets 422, model text is repaired.
    svc, _ = env["service"](
        '{"answer": "Chào \\ud800 bạn"}', '{"tool": "tao_ticket", "args": {"summary": "Lỗi \\udc00 app"}}'
    )
    with pytest.raises(ValueError):
        svc.run(OWNER, "Xin chào \ud800")
    assert svc.run(OWNER, "Xin chào").answer == "Chào ? bạn"
    pending = svc.run(OWNER, "Tạo ticket")
    assert pending.pending_action == {"tool": "tao_ticket", "args": {"summary": "Lỗi ? app"}}
    with pytest.raises(ValueError):
        svc.decide(pending.thread_id, APPROVER, False, "Không \ud800")


class FlakyTickets(TicketStore):
    def __init__(self, path, failures):
        super().__init__(path)
        self.failures = failures

    def create(self, *args, **kwargs):
        if self.failures:
            self.failures -= 1
            raise sqlite3.OperationalError("database is locked")
        return super().create(*args, **kwargs)


def test_failed_ticket_write_keeps_the_action_pending_for_a_retry(env, tmp_path):
    # F-03: the decision used to be lost (409 on retry, no ticket, owner's next message dropped it).
    thread_id = pending_thread(env)
    flaky = FlakyTickets(tmp_path / "flaky.db", failures=1)
    svc, _ = env["service"]()
    svc.tickets = flaky
    with pytest.raises(AgentUnavailable, match=r"\(ticket store\)"):
        svc.decide(thread_id, APPROVER, True)
    again = svc.run(OWNER, "Sao rồi?", thread_id)
    assert again.status == "pending_approval"
    assert again.pending_action == {"tool": "tao_ticket", "args": {"summary": "Khách báo mất thẻ, SĐT <PHONE_NUMBER>"}}
    assert svc.decide(thread_id, APPROVER, True).answer.startswith("Đã tạo ticket #1")
    assert len(ticket_rows(flaky)) == 1


def test_thread_locks_are_released(env):
    # F-04: random thread ids from any user used to grow the lock table for ever.
    svc, _ = env["service"](DOCS)
    svc.run(OWNER, "Phí thẻ?")
    for _ in range(50):
        with pytest.raises(ThreadNotFound):
            svc.run(OWNER, "x", uuid.uuid4().hex)
    assert svc._locks == {}


# Amounts the masking hides (A's decision 2026-11-02: option c + answer_source for T-031)

MASKED_LOAN = (
    '{"tool": "tinh_lai_vay", "args": {"principal": "<ACCOUNT_NUMBER_1>", "annual_rate_percent": 12, "months": 12}}'
)


def test_masked_amount_reaches_the_calculator_but_never_the_model(env):
    svc, llm = env["service"](MASKED_LOAN)
    result = svc.run(OWNER, "Vay 100.000.000 đồng, lãi 12%/năm, 12 tháng trả góp đều")
    sent = json.dumps([m for m, _ in llm.calls], ensure_ascii=False)
    assert "100.000.000" not in sent and "<ACCOUNT_NUMBER_1>" in sent
    assert "Khoản vay 100.000.000 đ" in result.answer and "Kỳ đầu trả 8.884.878,87 đ" in result.answer
    assert result.answer_source == "tool"


def test_amount_from_an_earlier_turn_resolves_until_a_restart(env):
    # The bot asks for the rate; the amount given one turn earlier must still work (review round 3, F-12).
    svc, llm = env["service"]('{"answer": "Lãi suất và kỳ hạn bao nhiêu?"}', MASKED_LOAN)
    thread_id = svc.run(OWNER, "Vay 100.000.000 đồng").thread_id
    result = svc.run(OWNER, "12%/năm, 12 tháng, tài khoản 12345678", thread_id)
    assert llm.calls[1][0][-1]["content"] == "12%/năm, 12 tháng, tài khoản <ACCOUNT_NUMBER_2>"  # numbering goes on
    assert "Khoản vay 100.000.000 đ" in result.answer
    restarted, _ = env["service"](MASKED_LOAN)  # memory is gone, the checkpoint never had the value
    stale = restarted.run(OWNER, "Tính lại với 12%, 12 tháng", thread_id).answer
    assert stale == f"Chưa thực hiện được (tinh_lai_vay): {agent_graph.STALE_AMOUNT}."


def checkpoint_bytes(env):
    # SqliteSaver writes through WAL: recent pages sit in -wal, not in the main file (review round 3, F-11).
    return b"".join(path.read_bytes() for path in env["checkpoints"].parent.glob(env["checkpoints"].name + "*"))


BAD_AMOUNT_ANSWER = (
    "Chưa thực hiện được (tinh_lai_vay): không đọc chắc được số tiền, anh/chị viết riêng số tiền, "
    "ví dụ '50.000.000 đồng' hoặc '50 triệu'."
)


@pytest.mark.parametrize(
    ("message", "placeholder"),
    [
        ("SĐT 0912345678, CCCD 001204012345, lãi 12% 12 tháng", "<CCCD_2>"),
        ("SĐT 0912345678, lãi 12% 12 tháng", "<PHONE_NUMBER_1>"),
    ],
    ids=["cccd", "phone"],
)
def test_phone_or_cccd_is_never_used_as_principal(env, message, placeholder):
    # F-09: the CCCD became "Khoản vay 1.204.012.345 đ", unmasked and stored in the checkpoint.
    reply = json.dumps(
        {"tool": "tinh_lai_vay", "args": {"principal": placeholder, "annual_rate_percent": 12, "months": 12}}
    )
    svc, _ = env["service"](reply)
    assert svc.run(OWNER, message).answer == BAD_AMOUNT_ANSWER
    raw = checkpoint_bytes(env)
    for digits in (b"001204012345", b"1204012345", b"0912345678", b"912345678"):
        assert digits not in raw


@pytest.mark.parametrize(
    "message",
    ["Vay 50.000.000 12 tháng 12%", "Vay 150.000.000 36 tháng 12%", "vay 100 000 000 12 tháng 12%"],
    ids=["dots-then-term", "dots-then-36", "spaces"],
)
def test_amount_joined_with_another_number_is_not_guessed(env, message):
    # F-10: "50.000.000 12" was read as 5.000.000.012 đ.
    svc, _ = env["service"](MASKED_LOAN)
    assert svc.run(OWNER, message).answer == BAD_AMOUNT_ANSWER


def test_term_must_be_stated_as_a_term(env):
    # F-12: months=12 used to pass because "12%" contains 12.
    svc, _ = env["service"](MASKED_LOAN)
    assert svc.run(OWNER, "Vay 100.000.000 đồng lãi 12%").answer == ("Anh/chị cho biết kỳ hạn của khoản vay giúp tôi.")


def test_vault_is_not_stored_in_the_checkpoint(env):
    svc, _ = env["service"]('{"answer": "Anh/chị cần gì thêm?"}')
    svc.run(OWNER, "Số tài khoản 1234567890123 của tôi")
    assert b"1234567890123" not in checkpoint_bytes(env)


@pytest.mark.parametrize(
    ("reply", "source"),
    [
        (LOAN, "tool"),
        (DOCS, "model"),
        ('{"answer": "Chào"}', "model"),
        ('{"tool": "tinh_lai_vay", "args": {"principal": -1, "annual_rate_percent": 1, "months": 1}}', "tool"),
    ],
    ids=["loan", "rag", "direct", "tool-error"],
)
def test_answer_source_tells_the_api_what_to_mask(env, reply, source):
    svc, _ = env["service"](reply)
    assert svc.run(OWNER, "x").answer_source == source


def test_ticket_outcome_is_a_tool_answer_and_pending_has_no_source(env):
    thread_id = pending_thread(env)
    svc, _ = env["service"]()
    assert svc.run(OWNER, "x", thread_id).answer_source is None
    assert svc.decide(thread_id, APPROVER, False).answer_source == "tool"


@pytest.mark.parametrize(
    ("message", "args", "asked"),
    [
        ("Tôi muốn vay 1.500.000.000 đ", {"annual_rate_percent": 10, "months": 36}, "lãi suất (%/năm) và kỳ hạn"),
        ("Vay 100 triệu, lãi 12%", {"annual_rate_percent": 12, "months": 36}, "kỳ hạn"),
        ("Vay 100 triệu trong 2 năm", {"annual_rate_percent": 8, "months": 24}, "lãi suất (%/năm)"),
    ],
    ids=["both-invented", "term-invented", "rate-invented"],
)
def test_loan_terms_the_user_never_gave_are_asked_for(env, message, args, asked):
    # Live run 2026-11-02: qwen2.5:3b filled in 10%/36 months for "Tôi muốn vay 1.500.000.000 đ".
    reply = json.dumps({"tool": "tinh_lai_vay", "args": {"principal": 100000000, **args}})
    svc, _ = env["service"](reply)
    result = svc.run(OWNER, message)
    assert result.answer == f"Anh/chị cho biết {asked} của khoản vay giúp tôi."
    assert result.answer_source == "tool"


@pytest.mark.parametrize(
    ("message", "rate", "months"),
    [("Vay 100 triệu, 9,5%/năm, 3 năm", 9.5, 36), ("Vay 100 triệu 12% 12 tháng", "12", 12)],
    ids=["comma-rate-years", "string-rate"],
)
def test_stated_loan_terms_pass_the_check(env, message, rate, months):
    reply = json.dumps(
        {"tool": "tinh_lai_vay", "args": {"principal": 100000000, "annual_rate_percent": rate, "months": months}}
    )
    svc, _ = env["service"](reply)
    assert svc.run(OWNER, message).answer.startswith("Khoản vay 100.000.000 đ")


def test_placeholder_the_thread_never_issued_asks_for_the_amount(env):
    # Live run: "Khách SĐT 0912345678 muốn vay, lãi 12% 12 tháng" -> qwen2.5:3b sent "<ACCOUNT_NUMBER_1>".
    svc, _ = env["service"](MASKED_LOAN)
    assert svc.run(OWNER, "Khách SĐT 0912345678 muốn vay, lãi 12% 12 tháng").answer == (
        "Anh/chị cho biết số tiền vay của khoản vay giúp tôi."
    )


# F-13 (review round 4): an account number is never used as the loan amount


def loan_with(placeholder):
    return json.dumps(
        {"tool": "tinh_lai_vay", "args": {"principal": placeholder, "annual_rate_percent": 12, "months": 12}}
    )


@pytest.mark.parametrize(
    "first",
    [
        "Vay 100.000.000, TK 87654321",
        "Vay 100.000.000 đồng vào STK 87654321",
        "Vay 100.000.000 đ, tài khoản số 87654321",
    ],
    ids=["tk", "stk", "tai-khoan"],
)
def test_account_number_is_never_the_principal(env, first):
    svc, _ = env["service"](
        '{"answer": "Lãi suất, kỳ hạn?"}', loan_with("<ACCOUNT_NUMBER_2>"), loan_with("<ACCOUNT_NUMBER_1>")
    )
    thread_id = svc.run(OWNER, first).thread_id
    wrong = svc.run(OWNER, "12% 12 tháng", thread_id)
    assert wrong.answer == f"Chưa thực hiện được (tinh_lai_vay): {agent_graph.STALE_AMOUNT}."
    right = svc.run(OWNER, "12% 12 tháng", thread_id)
    assert "Khoản vay 100.000.000 đ" in right.answer
    assert b"87654321" not in checkpoint_bytes(env)


@pytest.mark.parametrize(
    ("message", "kept"),
    [
        ("Vay 100.000.000, TK 87654321", {"<ACCOUNT_NUMBER_1>": "100.000.000"}),
        ("Khoản vay 250.000.000 VND", {"<ACCOUNT_NUMBER_1>": "250.000.000"}),
        ("Tôi muốn vay số tiền là 300.000.000", {"<ACCOUNT_NUMBER_1>": "300.000.000"}),
        ("Tiền gốc: 120.000.000", {"<ACCOUNT_NUMBER_1>": "120.000.000"}),
        ("Số tài khoản 12345678 muốn vay", {}),
        ("STK: 1234567890", {}),
        ("Giao dịch 12345678 hôm qua", {}),
        ("tk 12345678 đ", {}),
        # review round 5, F-15: account numbers that still became amounts
        ("chuyển vào 87654321 đồng thời vay 100.000.000", {"<ACCOUNT_NUMBER_2>": "100.000.000"}),
        ("TK của tôi là 87654321 đồng ý vay 100 triệu", {}),
        ("TK là 87654321 đ", {}),
        ("tài khoản của tôi: 87654321 đồng", {}),
        ("Tài khoản thanh toán 87654321 đồng", {}),
        ("account no. 87654321 VND", {}),
        ("a/c 87654321 đ", {}),
        ("tài khoản vay 87654321", {}),
        ("khoản vay 87654321", {}),
        ("vay <ACCOUNT_NUMBER_1> TK 87654321", {}),
        # F-16: amounts that were refused
        ("vay khoảng 100.000.000", {"<ACCOUNT_NUMBER_1>": "100.000.000"}),
        ("cần 200.000.000 để mua nhà", {"<ACCOUNT_NUMBER_1>": "200.000.000"}),
        ("mượn 100.000.000", {"<ACCOUNT_NUMBER_1>": "100.000.000"}),
        ("Vay mua nhà 2.000.000.000", {"<ACCOUNT_NUMBER_1>": "2.000.000.000"}),
        ("khoản vay trị giá 100.000.000", {"<ACCOUNT_NUMBER_1>": "100.000.000"}),
        ("VND 100.000.000", {"<ACCOUNT_NUMBER_1>": "100.000.000"}),
        # review round 6, F-17: an amount word far before, or a transfer preposition, is not this number's
        ("Tôi muốn vay 100 triệu chuyển vào 87654321 lãi 12% 12 tháng", {}),
        ("vay 100 triệu giải ngân vào 87654321", {}),
        ("cần vay 100 triệu về số 87654321", {}),
        ("Vay 100 triệu trả lương qua 87654321", {}),
        ("vay rồi trả vào 87654321", {}),
        ("Số hợp đồng vay 87654321", {}),
        ("Mã KH 87654321 vay", {}),
        ("Vay thêm 50.000.000", {"<ACCOUNT_NUMBER_1>": "50.000.000"}),
        ("vay 1 khoản 100.000.000 đồng", {"<ACCOUNT_NUMBER_1>": "100.000.000"}),
    ],
    ids=[
        "vay-then-tk",
        "vnd",
        "so-tien-la",
        "tien-goc",
        "tai-khoan",
        "stk",
        "no-context",
        "tk-then-d",
        "dong-thoi",
        "dong-y",
        "tk-la",
        "tai-khoan-cua-toi",
        "tai-khoan-thanh-toan",
        "account-no",
        "a-c",
        "tai-khoan-vay",
        "khoan-vay-id",
        "typed-placeholder",
        "khoang",
        "can",
        "muon",
        "vay-mua-nha",
        "tri-gia",
        "vnd-before",
        "far-vay-chuyen-vao",
        "giai-ngan-vao",
        "ve-so",
        "qua",
        "tra-vao",
        "hop-dong",
        "ma-kh",
        "vay-them",
        "mot-khoan",
    ],
)
def test_only_values_marked_as_amounts_are_kept(message, kept):
    from app.security.masking import require_mask_numbered

    masked, _, hidden = require_mask_numbered(message)
    assert agent_graph.amounts_in(masked, hidden) == kept


def test_masked_amount_expires_after_thirty_minutes(env, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(agent_graph.time, "monotonic", lambda: clock[0])
    svc, _ = env["service"]('{"answer": "Lãi suất, kỳ hạn?"}', MASKED_LOAN, MASKED_LOAN)
    thread_id = svc.run(OWNER, "Vay 100.000.000 đồng").thread_id
    clock[0] += 29 * 60
    assert "Khoản vay 100.000.000 đ" in svc.run(OWNER, "12% 12 tháng", thread_id).answer
    clock[0] += 31 * 60
    expired = svc.run(OWNER, "Tính lại 12% 12 tháng", thread_id).answer
    assert expired == f"Chưa thực hiện được (tinh_lai_vay): {agent_graph.STALE_AMOUNT}."


# PR #94 QA by B (Codex), F-01: a sensitive history must not reach cloud through the RAG tool's question


@pytest.mark.parametrize("first", ["confidential", "transactions"])
def test_sensitive_history_never_reaches_cloud_through_a_later_rag_question(env, first):
    if first == "confidential":
        secret = Hit("d2", "noi-bo.pdf", 3, "Dự án SYN-ORION-7 giảm phí 0,5%", 0.9, "credit", "confidential")
        env["answerer"].retriever.hits = [secret]
        opener = '{"tool": "tra_cuu_tai_lieu", "args": {"question": "Ưu đãi dự án nội bộ?"}}'
    else:
        opener = '{"tool": "tra_cuu_giao_dich", "args": {"account_ref": "TK1", "limit": 2}}'
    svc, _ = env["service"](opener)
    thread_id = svc.run(OWNER, "Câu hỏi đầu").thread_id
    env["answerer"].retriever.hits = [Hit("d1", "phi-the.pdf", 1, "Phí thẻ 50.000 đ", 0.9, "public")]
    follow = '{"tool": "tra_cuu_tai_lieu", "args": {"question": "Phí thẻ cho SYN-ORION-7, Synthetic transaction 5?"}}'
    restarted, llm = env["service"](follow)  # a new service over the same checkpoint file
    result = restarted.run(OWNER, "Còn phí thẻ thì sao?", thread_id)
    assert [alias for _, alias in llm.calls] == ["local-chat"]
    assert env["answerer"].calls[-1][2] is True
    assert result.status == "completed"


def test_injected_state_is_hidden_from_the_tool_schema_and_required(env):
    # Review round 8 F-20/F-21: the model cannot see or set ``state``; without it the call fails closed.
    bound = agent_graph._BoundTools(OWNER, [], None, env["answerer"])
    schemas = {tool.name: tool.tool_call_schema.model_json_schema()["properties"] for tool in bound.as_langchain()}
    assert list(schemas["tra_cuu_tai_lieu"]) == ["question"]
    with pytest.raises(TypeError):
        bound.tra_cuu_tai_lieu("Phí thẻ?")
    assert env["answerer"].calls == []
