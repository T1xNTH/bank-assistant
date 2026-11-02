"""LangGraph agent: route between RAG and tools; interrupt before tao_ticket.

One turn: the model (through ``app.llm`` with the alias ``decide_route`` picks) either answers a
greeting or clarifying question itself, or names one tool as JSON. ``ToolNode`` runs the read-only
tools (``tinh_lai_vay``, ``tra_cuu_giao_dich``, ``tra_cuu_tai_lieu``) and ``render`` writes the reply
from the tool result in code. Money never goes back through the model: masking treats any run of
8+ digits as an account number, so a model-written amount would come out as ``<ACCOUNT_NUMBER>``.

``tao_ticket`` never reaches ``ToolNode``. ``propose`` builds the masked proposal and calls
``interrupt``; the thread waits in the SQLite checkpointer until ``AgentService.decide`` resumes it
with a decision built from the authenticated approver. Only then does ``create_ticket`` call
``TicketStore.create``, with the owner taken from the trusted state, never from model arguments
(T-029 F-03). The approver must hold role ``approver`` and differ from the owner.

State holds masked text only: the user message is masked (fail-closed) before it enters the
graph, tool outputs are masked by ``AgentTools``, and the checkpoint stores nothing else from the
user. Accounts are shown as ``TK1``, ``TK2``... (order of account id) because masking hides real
account numbers, and the model passes the same reference back (T-029 F-01).

Owner: A — Epic E-011. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt

from app.agent.core_banking import CoreBanking
from app.agent.tickets import TicketDecision, TicketStore
from app.agent.tools import AgentTools, ToolUnavailable
from app.contracts import LLM, REFUSAL, Answerer, User
from app.llm import LLMError
from app.prompts import AGENT_SYSTEM
from app.rag.answer import AnswerUnavailable
from app.routing import decide_route
from app.security.masking import MaskingError, require_mask_content, require_mask_content_types, require_mask_numbered

READ_TOOLS = ("tinh_lai_vay", "tra_cuu_giao_dich", "tra_cuu_tai_lieu")
TOOL_ARGS = {
    "tinh_lai_vay": {"principal", "annual_rate_percent", "months", "method"},
    "tra_cuu_giao_dich": {"account_ref", "limit"},
    "tra_cuu_tai_lieu": {"question"},
    "tao_ticket": {"summary"},
}
MAX_MESSAGE = 4000
MAX_COMMENT = 500
HISTORY = 12  # messages of earlier turns sent to the model
SENSITIVE = "confidential"  # customer banking data in the thread routes later turns to local-chat
# A numbered placeholder from require_mask_numbered; only this turn's values are in the vault.
PLACEHOLDER = re.compile(r"<(?:CCCD|ACCOUNT_NUMBER|PHONE_NUMBER)_\d+>")
AMOUNT_PLACEHOLDER = re.compile(r"<ACCOUNT_NUMBER_\d+>")
# Only a plain or dot-grouped number is an amount. The masker joins "50.000.000 12" (amount + term) or
# "100 000 000" into one span; reading those as a principal gave 5.000.000.012 đ (review round 3, F-10).
AMOUNT_TEXT = re.compile(r"\d+|\d{1,3}(?:\.\d{3})+")
STALE_AMOUNT = (
    "chưa xác định được số tiền vay (số này có thể là số tài khoản, hoặc đã quá 30 phút), "
    "anh/chị nhập lại, ví dụ 'vay 100.000.000 đồng'"
)
BAD_AMOUNT = "không đọc chắc được số tiền, anh/chị viết riêng số tiền, ví dụ '50.000.000 đồng' hoặc '50 triệu'"
VAULT_THREADS = 1000  # threads whose masked amounts are kept in memory (least recently used dropped)
VAULT_VALUES = 20  # amounts kept per thread
VAULT_TTL_S = 30 * 60  # a masked amount is usable for 30 minutes
# Amount or account? Both mask to <ACCOUNT_NUMBER_n> (review rounds 4-5, F-13/F-15). A value is kept as an
# amount only when its clause (text since the last , ; ! ? or newline) marks it as money, and never
# when an account label appears anywhere earlier in that clause ("TK của tôi là 87654321 đ").
_CLAUSE_BREAK = re.compile(r"[,;!?\n]")  # not ".": "account no. 87654321" must keep its label
_ACCOUNT_LABEL = re.compile(
    r"(?<!\w)(?:s?tk|t[aà]i\s*kho[aả]n|account(?:\s*(?:no\.?|number))?|a/c)(?!\w)", re.IGNORECASE
)
_AMOUNT_WORD = re.compile(
    r"(?<!\w)(?:vay|m[uư][oợ]n|c[aầ]n|s[oố]\s*ti[eề]n|ti[eề]n\s*g[oố]c|g[oố]c|t[ií]nh\s*l[aã]i|tr[iị]\s*gi[aá])(?!\w)",
    re.IGNORECASE,
)
_LOAN_ACCOUNT_BEFORE = re.compile(r"kho[aả]n\s*vay\s*(?:s[oố])?\s*[:#]?\s*$", re.IGNORECASE)  # an id, unless "đồng"
_CURRENCY_BEFORE = re.compile(r"(?<!\w)vn[dđ]\s*$", re.IGNORECASE)
# "đồng" is also the first syllable of common words ("đồng thời", "đồng ý"): those are not a currency.
_NOT_CURRENCY = r"(?!\s+(?:thời|ý|nghiệp|bộ|hồ|tình|thuận|loạt|nhất|đều|chí|hành|minh|phục|hương|lòng|nghĩa|đội)(?!\w))"
_AMOUNT_AFTER = re.compile(rf"^\s*(?:đ|đồng{_NOT_CURRENCY}|dong|vnđ|vnd)(?!\w)", re.IGNORECASE)
UNCLEAR = "Xin lỗi, tôi chưa hiểu yêu cầu. Anh/chị nói rõ hơn giúp tôi được không?"
THREAD_ID = re.compile(r"[0-9a-f]{32}")
UNAVAILABLE = (LLMError, AnswerUnavailable, ToolUnavailable, MaskingError, sqlite3.Error)


class ThreadNotFound(LookupError):
    """Unknown thread, or one owned by another user (the API answers 404 for both)."""


class DecisionConflict(RuntimeError):
    """The thread has no action waiting for a decision (already decided, or never asked)."""


class AgentUnavailable(RuntimeError):
    """A dependency failed (LLM, Qdrant, SQLite, masking); never carries user text."""


@dataclass(frozen=True)
class AgentResult:
    """``answer_source``: ``"tool"`` means code wrote the answer from tool results whose text is already
    masked (amounts, dates, TK refs, masked descriptions); the API must return it as is, because masking
    again turns every 8+ digit amount into ``<ACCOUNT_NUMBER>``. ``"model"``: mask as usual. Logs and
    audit mask both."""

    thread_id: str
    status: Literal["completed", "pending_approval"]
    answer: str | None = None
    pending_action: dict | None = None
    answer_source: Literal["model", "tool"] | None = None


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    owner: str  # authenticated user_id; the only owner a ticket can get
    department: str
    role: str
    pii: list[str]  # PII types the user's messages had, for routing
    sensitive: bool
    answer: str | None
    decision: dict | None
    ticket_failed: bool  # the approved write failed; the thread waits for a decision again
    answer_source: Literal["model", "tool"]
    vault_seq: int  # placeholders numbered so far, so each turn's numbers are new
    issued: list[str]  # names of the placeholders issued in this thread (never their values)


def _clean(text: str) -> str:
    """Drop lone surrogates (e.g. a JSON "\\ud800" from the model): the checkpoint cannot store them."""
    return text.encode("utf-8", "replace").decode("utf-8")


def _is_text(value: Any, limit: int) -> bool:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


# Formatting


def vnd(amount: str | int | Decimal) -> str:
    """12345678.9 -> "12.345.678,90 đ" (Vietnamese grouping; whole amounts drop ",00")."""
    value = Decimal(str(amount))
    text = f"{abs(value):,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    if text.endswith(",00"):
        text = text[:-3]
    return f"{'-' if value < 0 else ''}{text} đ"


def render_loan(result: dict) -> str:
    rows = result["schedule"]
    method = "trả góp đều (annuity)" if result["method"] == "annuity" else "dư nợ giảm dần, gốc trả đều"
    first = rows[0]
    lines = [
        f"Khoản vay {vnd(result['principal'])}, lãi suất {result['annual_rate_percent']}%/năm, "
        f"{result['months']} tháng, {method}:",
        f"- Kỳ đầu trả {vnd(first['payment'])} (gốc {vnd(first['principal'])}, lãi {vnd(first['interest'])}).",
    ]
    if len(rows) > 1:
        lines.append(f"- Kỳ cuối trả {vnd(rows[-1]['payment'])}.")
    lines.append(f"- Tổng lãi {vnd(result['total_interest'])}, tổng phải trả {vnd(result['total_payment'])}.")
    lines.append("Cách tính: lãi tháng = lãi năm / 12, làm tròn đến đồng xu mỗi kỳ, không gồm phí.")
    return "\n".join(lines)


def render_transactions(rows: list[dict]) -> str:
    if not rows:
        return "Không có giao dịch nào phù hợp."
    lines = [f"{len(rows)} giao dịch gần nhất:"]
    for row in rows:
        lines.append(f"- {str(row['ts'])[:10]} · {row['account_ref']} · {vnd(row['amount'])} · {row['description']}")
    return "\n".join(lines)


def render_rag(result: dict) -> str:
    if not result["found"]:
        return REFUSAL
    sources = [f"[{c['n']}] {c['source']}, trang {c['page']}" for c in result["citations"]]
    return result["answer"] + "\n\nNguồn:\n" + "\n".join(sources)


# Model reply -> tool call

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def parse_reply(text: str) -> tuple[str, dict] | str:
    """``(tool, args)`` for a tool call, else the text to show (a direct answer)."""
    body = _FENCE.sub(r"\1", text).strip()
    try:
        data = json.loads(body)
    except ValueError:
        return text.strip() or UNCLEAR
    if isinstance(data, dict) and isinstance(data.get("tool"), str):
        name, args = data["tool"], data.get("args")
        if name in TOOL_ARGS and isinstance(args, dict):
            return name, {k: v for k, v in args.items() if k in TOOL_ARGS[name]}
        return UNCLEAR
    if isinstance(data, dict) and isinstance(data.get("answer"), str) and data["answer"].strip():
        return data["answer"].strip()
    return UNCLEAR


_RATE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
_MONTHS = re.compile(r"(\d+)\s*th[aá]ng", re.IGNORECASE)
_YEARS = re.compile(r"(\d+(?:[.,]\d+)?)\s*n[aă]m", re.IGNORECASE)


def _stated(pattern: re.Pattern, messages: list[AnyMessage], scale: int = 1) -> set[Decimal]:
    found = set()
    for message in messages:
        if isinstance(message, HumanMessage):
            text = PLACEHOLDER.sub(" ", message.content)  # "<ACCOUNT_NUMBER_12>" states no number
            found |= {Decimal(n.replace(",", ".")) * scale for n in pattern.findall(text)}
    return found


def unstated_loan_terms(args: dict, messages: list[AnyMessage]) -> list[str]:
    """Rate and term the model passed that no user message states as such ("12%"; "12 tháng" or "1 năm")."""
    rates = _stated(_RATE, messages)
    terms = _stated(_MONTHS, messages) | _stated(_YEARS, messages, 12)
    missing = []
    for key, label, stated in (("annual_rate_percent", "lãi suất (%/năm)", rates), ("months", "kỳ hạn", terms)):
        try:
            value = Decimal(str(args.get(key)))
        except ArithmeticError:
            continue  # not a number: the calculator rejects it with its own message
        if value.is_finite() and value not in stated:
            missing.append(label)
    return missing


def amounts_in(masked: str, hidden: dict[str, str]) -> dict[str, str]:
    """The hidden ACCOUNT_NUMBER values whose placeholder the message marks as an amount.

    Kept: "vay khoảng <ACCOUNT_NUMBER_1>", "cần <...>", "số tiền: <...>", "<...> đồng/đ/VND", "VND <...>".
    Never: a clause with TK/STK/tài khoản/account/a/c before the number; "khoản vay <...>" needs "đồng" after.
    """
    kept = {}
    for placeholder, value in hidden.items():
        at = masked.find(placeholder)
        if not AMOUNT_PLACEHOLDER.fullmatch(placeholder) or at < 0:
            continue
        head = masked[max(0, at - 200) : at]
        breaks = list(_CLAUSE_BREAK.finditer(head))
        clause = PLACEHOLDER.sub(" ", head[breaks[-1].end() :] if breaks else head)
        money_after = _AMOUNT_AFTER.match(masked[at + len(placeholder) :]) is not None
        if _ACCOUNT_LABEL.search(clause):
            continue
        if _LOAN_ACCOUNT_BEFORE.search(clause):
            if money_after:
                kept[placeholder] = value
        elif money_after or _AMOUNT_WORD.search(clause) or _CURRENCY_BEFORE.search(clause):
            kept[placeholder] = value
    return kept


def model_messages(state: AgentState) -> list[dict]:
    """System prompt plus earlier user messages and replies; tool-call steps are left out."""
    turns: list[dict] = []
    for message in state["messages"]:
        if isinstance(message, HumanMessage):
            turns.append({"role": "user", "content": message.content})
        elif isinstance(message, AIMessage) and message.content and not message.tool_calls:
            turns.append({"role": "assistant", "content": message.content})
    return [{"role": "system", "content": AGENT_SYSTEM}, *turns[-HISTORY:]]


# Graph


class _BoundTools:
    """Read-only tools bound to one authenticated user; ``ToolNode`` passes model arguments only."""

    def __init__(
        self, user: User, pii: list[str], bank: CoreBanking, answerer: Answerer, vault: dict[str, str] | None = None
    ):
        self.user, self.pii, self.bank, self.answerer = user, pii, bank, answerer
        self.vault = vault or {}  # placeholder -> value masked out of this turn's message; memory only
        self.agent_tools = AgentTools(user, bank)

    def _amount(self, value: Any) -> Any:
        """``"<ACCOUNT_NUMBER_1>"`` -> 100000000 when the user's message hid that amount; else unchanged.

        Only ACCOUNT_NUMBER placeholders: a phone or CCCD must never become a principal that is then
        shown unmasked and stored in the checkpoint (review round 3, F-09).
        """
        if not isinstance(value, str) or not PLACEHOLDER.fullmatch(value):
            return value
        if not AMOUNT_PLACEHOLDER.fullmatch(value):
            raise ValueError(BAD_AMOUNT)
        raw = self.vault.get(value)
        if raw is None:
            raise ValueError(STALE_AMOUNT)
        if not AMOUNT_TEXT.fullmatch(raw):
            raise ValueError(BAD_AMOUNT)
        return int(raw.replace(".", ""))

    def tinh_lai_vay(
        self, principal: Any = None, annual_rate_percent: Any = None, months: Any = None, method: Any = "annuity"
    ) -> dict:
        try:
            principal = self._amount(principal)
            return {"ok": self.agent_tools.tinh_lai_vay(principal, annual_rate_percent, months, method)}
        except ValueError as exc:  # messages never include the input (T-029)
            return {"error": str(exc)}

    def _refs(self) -> dict[str, str]:
        try:
            accounts = self.bank.accounts(self.user)
        except sqlite3.Error:
            raise ToolUnavailable("Transaction lookup unavailable") from None
        return {f"TK{i}": account["id"] for i, account in enumerate(accounts, 1)}

    def tra_cuu_giao_dich(self, account_ref: Any = None, limit: Any = 20) -> dict:
        if type(limit) is not int or not 1 <= limit <= 100:
            return {"error": "limit must be an integer between 1 and 100"}
        refs = self._refs()
        if account_ref is not None and (not isinstance(account_ref, str) or account_ref not in refs):
            return {"error": f"account_ref must be one of: {', '.join(refs) or 'none'}"}
        rows = []
        for ref, account_id in refs.items():
            if account_ref in (None, ref):
                rows += [{**row, "account_ref": ref} for row in self.agent_tools.tra_cuu_giao_dich(account_id, limit)]
        rows.sort(key=lambda row: (str(row["ts"]), str(row["id"])), reverse=True)  # same order as CoreBanking
        keep = ("ts", "account_ref", "amount", "description")
        return {"ok": [{key: row[key] for key in keep} for row in rows[:limit]]}

    def tra_cuu_tai_lieu(self, question: Any = None) -> dict:
        if not isinstance(question, str) or not question.strip() or len(question) > MAX_MESSAGE:
            return {"error": "question must be non-empty text"}
        masked, types = require_mask_content_types(question)
        result = self.answerer.answer(masked, self.user, force_local=bool(self.pii or types))
        citations = [{"n": c.n, "source": c.source, "page": c.page} for c in result.citations]
        answer = _clean(result.answer)
        return {"ok": {"answer": answer, "found": result.found, "route": result.route, "citations": citations}}

    def as_langchain(self) -> list[StructuredTool]:
        return [StructuredTool.from_function(getattr(self, name), name=name, description=name) for name in READ_TOOLS]


def build_graph(
    user: User,
    *,
    llm: LLM,
    answerer: Answerer,
    bank: CoreBanking,
    tickets: TicketStore,
    checkpointer,
    pii: list[str],
    vault: dict[str, str] | None = None,
):
    bound = _BoundTools(user, pii, bank, answerer, vault)

    def agent(state: AgentState) -> dict:
        classifications = [SENSITIVE] if state.get("sensitive") else []
        alias = decide_route(state.get("pii", []), classifications).alias
        reply = parse_reply(llm.chat(model_messages(state), alias).text)
        # app.llm masks replies already; mask again so no LLM implementation can put PII in the checkpoint.
        if isinstance(reply, str):
            reply = require_mask_content(_clean(reply))  # after json.loads, which decodes "\ud800"
            return {"messages": [AIMessage(content=reply)], "answer": reply, "answer_source": "model"}
        name, args = reply
        args = {key: require_mask_content(_clean(v)) if isinstance(v, str) else v for key, v in args.items()}
        if name == "tinh_lai_vay":
            principal = args.get("principal")
            # A placeholder this thread never issued was made up by the model (seen with qwen2.5:3b).
            invented = (
                isinstance(principal, str)
                and PLACEHOLDER.fullmatch(principal) is not None
                and principal not in state.get("issued", [])
            )
            if not invented:
                try:
                    bound._amount(principal)  # an unreadable amount is the first thing to fix
                except ValueError as exc:
                    answer = f"Chưa thực hiện được (tinh_lai_vay): {exc}."
                    return {"messages": [AIMessage(content=answer)], "answer": answer, "answer_source": "tool"}
            missing = (["số tiền vay"] if invented else []) + unstated_loan_terms(args, state["messages"])
            if missing:  # the model filled in a rate or term the user never gave (seen with qwen2.5:3b)
                answer = f"Anh/chị cho biết {' và '.join(missing)} của khoản vay giúp tôi."
                return {"messages": [AIMessage(content=answer)], "answer": answer, "answer_source": "tool"}
        call = {"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:12]}", "type": "tool_call"}
        return {"messages": [AIMessage(content="", tool_calls=[call])]}

    def after_agent(state: AgentState) -> str:
        last = state["messages"][-1]
        if not getattr(last, "tool_calls", None):
            return END
        return "propose" if last.tool_calls[0]["name"] == "tao_ticket" else "tools"

    def render(state: AgentState) -> dict:
        message = state["messages"][-1]
        data = json.loads(message.content)
        if "error" in data:
            answer = f"Chưa thực hiện được ({message.name}): {data['error']}."
        elif message.name == "tinh_lai_vay":
            answer = render_loan(data["ok"])
        elif message.name == "tra_cuu_giao_dich":
            answer = render_transactions(data["ok"])
        else:
            answer = render_rag(data["ok"])
        # A RAG answer is model text (app.llm masked it); the others are templates over tool output.
        source = "model" if message.name == "tra_cuu_tai_lieu" and "ok" in data else "tool"
        update: dict = {"messages": [AIMessage(content=answer)], "answer": answer, "answer_source": source}
        # Customer transactions, or a RAG answer the Answerer routed local (confidential chunks), now sit in
        # the history that later turns send to the model: keep those turns on local-chat (security-design).
        if "ok" in data and (
            message.name == "tra_cuu_giao_dich"
            or (message.name == "tra_cuu_tai_lieu" and data["ok"]["route"] == "local")
        ):
            update["sensitive"] = True
        return update

    def propose(state: AgentState) -> dict:
        call = state["messages"][-1].tool_calls[0]
        try:
            proposal = bound.agent_tools.tao_ticket(call["args"].get("summary"))
        except ValueError as exc:
            answer = f"Chưa tạo được đề xuất ticket: {exc}."
            tool_message = ToolMessage(content=answer, tool_call_id=call["id"], name="tao_ticket")
            return {"messages": [tool_message, AIMessage(content=answer)], "answer": answer, "answer_source": "tool"}
        # Execution stops here until AgentService.decide resumes the thread; the node then runs again
        # and interrupt returns the decision. Building the proposal twice is harmless: it is pure.
        decision = interrupt({"tool": "tao_ticket", "args": {"summary": proposal["summary"]}})
        return {"decision": {**decision, "summary": proposal["summary"], "call_id": call["id"]}}

    def after_propose(state: AgentState) -> str:
        return "create_ticket" if state.get("decision") else END

    def after_create(state: AgentState) -> str:
        return "propose" if state.get("ticket_failed") else END

    def create_ticket(state: AgentState) -> dict:
        decision = state["decision"]
        summary = decision["summary"]
        if decision["approve"] is True:
            approver = User(**decision["approver"])
            try:
                row = tickets.create(
                    state["owner"],
                    summary,
                    approver.user_id,
                    decision=TicketDecision(
                        created_by=state["owner"], summary=summary, approver=approver, approved=True
                    ),
                )
            except (sqlite3.Error, OSError):
                # Nothing was written: ask again (propose interrupts anew) so the approver can retry.
                return {"decision": None, "ticket_failed": True}
            answer = f"Đã tạo ticket #{row['id']} (trạng thái {row['status']}) sau khi người duyệt đồng ý."
        else:
            answer = "Người duyệt đã từ chối, không tạo ticket."
        if decision.get("comment"):
            answer += f" Ghi chú của người duyệt: {decision['comment']}"
        tool_message = ToolMessage(content=answer, tool_call_id=decision["call_id"], name="tao_ticket")
        return {
            "messages": [tool_message, AIMessage(content=answer)],
            "answer": answer,
            "answer_source": "tool",
            "decision": None,
            "ticket_failed": False,
        }

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(bound.as_langchain(), handle_tool_errors=False))
    graph.add_node("render", render)
    graph.add_node("propose", propose)
    graph.add_node("create_ticket", create_ticket)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", after_agent, ["tools", "propose", END])
    graph.add_edge("tools", "render")
    graph.add_edge("render", END)
    graph.add_conditional_edges("propose", after_propose, ["create_ticket", END])
    graph.add_conditional_edges("create_ticket", after_create, ["propose", END])
    return graph.compile(checkpointer=checkpointer)


# Service used by the /agent endpoints (T-031)


def sqlite_checkpointer(path: str | Path | None = None) -> SqliteSaver:
    path = Path(path if path is not None else os.getenv("AGENT_CHECKPOINT_DB_PATH", "data/agent_checkpoints.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver(sqlite3.connect(path, check_same_thread=False))


class AgentService:
    """Start, continue and decide agent threads for authenticated users.

    ``run`` continues only threads the same user started; ``decide`` takes the approver from the
    authenticated request, refuses self-approval, and answers each pending action once. One lock per
    thread serializes calls inside this process (the API runs one process; several would need a
    database lock). Errors: ``ThreadNotFound`` (404), ``PermissionError`` (403), ``DecisionConflict``
    (409), ``AgentUnavailable`` (503), ``ValueError`` for bad input (422).
    """

    def __init__(
        self,
        *,
        llm: LLM | None = None,
        answerer: Answerer | None = None,
        bank: CoreBanking | None = None,
        tickets: TicketStore | None = None,
        checkpointer=None,
    ):
        if llm is None:
            from app import llm as gateway

            llm = gateway
        if answerer is None:
            from app.rag.answer import RagAnswerer

            answerer = RagAnswerer(llm=llm)
        self.llm, self.answerer = llm, answerer
        self.bank = bank if bank is not None else CoreBanking()
        self.tickets = tickets if tickets is not None else TicketStore()
        self.checkpointer = checkpointer if checkpointer is not None else sqlite_checkpointer()
        self._locks: dict[str, list] = {}  # thread_id -> [lock, users]; removed when no call holds or waits
        # thread_id -> {placeholder: (amount text, time stored)}: masked amounts, memory only, so
        # "Vay 100.000.000 đồng" then "12%, 12 tháng" works across turns. Only values the message marks as an
        # amount (amounts_in); dropped after VAULT_TTL_S and on restart (STALE_AMOUNT).
        self._vaults: OrderedDict[str, dict[str, tuple[str, float]]] = OrderedDict()
        self._guard = threading.Lock()

    @contextmanager
    def _lock(self, thread_id: str) -> Iterator[None]:
        with self._guard:
            entry = self._locks.setdefault(thread_id, [threading.Lock(), 0])
            entry[1] += 1
        try:
            with entry[0]:
                yield
        finally:
            with self._guard:
                entry[1] -= 1
                if entry[1] == 0:
                    del self._locks[thread_id]

    def _remember(self, thread_id: str, masked: str, hidden: dict[str, str]) -> dict[str, str]:
        now = time.monotonic()
        with self._guard:
            vault = {k: v for k, v in self._vaults.pop(thread_id, {}).items() if now - v[1] < VAULT_TTL_S}
            vault.update((k, (v, now)) for k, v in amounts_in(masked, hidden).items())
            vault = dict(list(vault.items())[-VAULT_VALUES:])
            self._vaults[thread_id] = vault
            while len(self._vaults) > VAULT_THREADS:
                self._vaults.popitem(last=False)
            return {k: v for k, (v, _) in vault.items()}

    def _graph(self, user: User, pii: list[str], vault: dict[str, str] | None = None):
        return build_graph(
            user,
            llm=self.llm,
            answerer=self.answerer,
            bank=self.bank,
            tickets=self.tickets,
            checkpointer=self.checkpointer,
            pii=pii,
            vault=vault,
        )

    @staticmethod
    def _config(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}

    def _snapshot(self, thread_id: str):
        # Reading the checkpoint does not depend on whose tools the graph is bound to.
        return self._graph(User("reader", "public"), []).get_state(self._config(thread_id))

    @staticmethod
    def _pending(snapshot) -> dict | None:
        for task in snapshot.tasks:
            for item in task.interrupts:
                return item.value
        return None

    def _result(self, thread_id: str, snapshot) -> AgentResult:
        pending = self._pending(snapshot)
        if pending is not None:
            return AgentResult(thread_id, "pending_approval", None, pending)
        values = snapshot.values
        return AgentResult(thread_id, "completed", values.get("answer"), None, values.get("answer_source", "model"))

    def run(self, user: User, message: str, thread_id: str | None = None) -> AgentResult:
        if not isinstance(user, User) or not isinstance(user.user_id, str) or not user.user_id.strip():
            raise ValueError("Authenticated user required")
        if not _is_text(message, MAX_MESSAGE):
            raise ValueError(f"message must be 1..{MAX_MESSAGE} characters of valid text")
        if thread_id is not None and (not isinstance(thread_id, str) or not THREAD_ID.fullmatch(thread_id)):
            raise ThreadNotFound("Unknown thread")  # ids are server-made; a client cannot pick one
        try:
            new = thread_id is None
            thread_id = thread_id or uuid.uuid4().hex
            with self._lock(thread_id):
                snapshot = self._snapshot(thread_id)
                values = snapshot.values or {}
                if not new and values.get("owner") != user.user_id:
                    raise ThreadNotFound("Unknown thread")
                if self._pending(snapshot) is not None:  # the decision comes first; this message is not taken
                    return self._result(thread_id, snapshot)
                seq = values.get("vault_seq", 0)
                masked, types, hidden = require_mask_numbered(message, start=seq)
                pii = sorted(set(values.get("pii", [])) | set(types))
                vault = self._remember(thread_id, masked, hidden)
                graph = self._graph(user, pii, vault)  # the vault never enters the state or the model
                state = {
                    "messages": [HumanMessage(content=masked)],
                    "vault_seq": seq + len(hidden),
                    "issued": [*values.get("issued", []), *hidden][-200:],
                    "owner": user.user_id,
                    "department": user.department,
                    "role": user.role,
                    "pii": pii,
                    "answer": None,
                    "answer_source": None,
                    "decision": None,
                }
                graph.invoke(state, self._config(thread_id))
                return self._result(thread_id, graph.get_state(self._config(thread_id)))
        except UNAVAILABLE as exc:
            raise AgentUnavailable(f"agent unavailable ({type(exc).__name__})") from None

    def decide(self, thread_id: str, approver: User, approve: bool, comment: str | None = None) -> AgentResult:
        if not isinstance(approver, User) or approver.role != "approver":
            raise PermissionError("Approver role required")
        if not isinstance(approve, bool):
            raise ValueError("approve must be a boolean")
        if comment is not None and (
            not isinstance(comment, str) or len(comment) > MAX_COMMENT or _clean(comment) != comment
        ):
            raise ValueError(f"comment must be at most {MAX_COMMENT} characters")
        if not isinstance(thread_id, str) or not THREAD_ID.fullmatch(thread_id):
            raise ThreadNotFound("Unknown thread")
        try:
            masked_comment = require_mask_content(comment) if comment and comment.strip() else None
            with self._lock(thread_id):
                snapshot = self._snapshot(thread_id)
                values = snapshot.values or {}
                if not values.get("owner"):
                    raise ThreadNotFound("Unknown thread")
                if self._pending(snapshot) is None:
                    raise DecisionConflict("No pending action")
                if approver.user_id == values["owner"]:
                    raise PermissionError("Self-approval is not allowed")
                owner = User(values["owner"], values["department"], values.get("role", "staff"))
                graph = self._graph(owner, values.get("pii", []))
                decision = {
                    "approve": approve,
                    "comment": masked_comment,
                    "approver": {"user_id": approver.user_id, "department": approver.department, "role": approver.role},
                }
                graph.invoke(Command(resume=decision), self._config(thread_id))
                snapshot = graph.get_state(self._config(thread_id))
                if snapshot.values.get("ticket_failed"):  # still pending: the approver may decide again
                    raise AgentUnavailable("agent unavailable (ticket store)")
                return self._result(thread_id, snapshot)
        except UNAVAILABLE as exc:
            raise AgentUnavailable(f"agent unavailable ({type(exc).__name__})") from None
