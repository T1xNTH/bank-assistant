"""Streamlit demo chat UI with role selector mapping to API keys.

Run: ``make ui`` (API at ``UI_API_URL``, default http://127.0.0.1:8000). Keys come only from the
environment (``UI_KEY_CREDIT_STAFF``, ``UI_KEY_HR_STAFF``, ``UI_KEY_APPROVER``; see ``.env.example``).

- Hỏi đáp: ``POST /ask``; shows the answer, citations (file, page, score) and the route (cloud/local).
- Agent: ``POST /agent``; a ``pending_approval`` reply shows the pending action. Threads started in
  this browser session are listed for the approver role, who approves or rejects them with
  ``POST /agent/{thread_id}/decision``. The API has no endpoint listing pending threads, so a thread
  from another session is entered by its id.

Owner: A — Epic E-016. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Append, never prepend: ui/app.py must not shadow the ``app`` package (src/app) for code that imports it.
UI_DIR = str(Path(__file__).resolve().parent)
if UI_DIR not in sys.path:
    sys.path.append(UI_DIR)

import ui_api  # noqa: E402

ROUTE_LABEL = {"cloud": "cloud (OpenAI, văn bản đã che)", "local": "local (Ollama/Qwen, không rời máy)"}


def state():
    ss = st.session_state
    ss.setdefault("ask_history", {})  # role label -> list of {question, result | error}
    ss.setdefault("threads", {})  # thread_id -> {role, messages, status, pending}
    ss.setdefault("current_thread", {})  # role label -> thread_id being continued
    return ss


def show_ask_result(result: dict) -> None:
    st.markdown(result["answer"])
    st.caption(
        f"Route: **{ROUTE_LABEL.get(result['route'], result['route'])}** · "
        f"retrieval: {result['retrieval_mode']} · {result['latency_ms']} ms"
    )
    if result["citations"]:
        st.table(
            [
                {"[n]": c["n"], "Tài liệu": c["source"], "Trang": c["page"], "Điểm": round(c["score"], 3)}
                for c in result["citations"]
            ]
        )


def ask_tab(api: ui_api.Api, role: str) -> None:
    history = state()["ask_history"].setdefault(role, [])
    with st.form("ask", clear_on_submit=True):
        question = st.text_area("Câu hỏi về tài liệu nội bộ", max_chars=2000)
        force_local = st.checkbox("Bắt buộc dùng model local (force_local)")
        submitted = st.form_submit_button("Hỏi")
    if submitted and question.strip():
        entry = {"question": question.strip()}
        with st.spinner("Đang tìm trong tài liệu và soạn câu trả lời..."):
            try:
                entry["result"] = api.ask(question.strip(), force_local)
            except ui_api.ApiError as exc:
                entry["error"] = exc.message
        history.append(entry)
    for entry in reversed(history):
        with st.chat_message("user"):
            st.write(entry["question"])
        with st.chat_message("assistant"):
            if "error" in entry:
                st.error(entry["error"])
            else:
                show_ask_result(entry["result"])


def record(thread_id: str, role: str, reply: dict, said: str | None) -> None:
    thread = state()["threads"].setdefault(thread_id, {"role": role, "messages": [], "status": None, "pending": None})
    if said is not None:
        thread["messages"].append(("user", said))
    if reply.get("answer"):
        thread["messages"].append(("assistant", reply["answer"]))
    thread["status"] = reply["status"]
    thread["pending"] = reply.get("pending_action")


def show_pending(pending: dict) -> None:
    st.warning(f"Hành động chờ duyệt: `{pending['tool']}`")
    st.json(pending["args"])


def agent_chat(api: ui_api.Api, role: str) -> None:
    ss = state()
    if st.button("Cuộc hội thoại mới"):
        ss["current_thread"].pop(role, None)
    current = ss["current_thread"].get(role)
    with st.form("agent", clear_on_submit=True):
        message = st.text_area("Tin nhắn cho agent (tra cứu, tính lãi vay, tạo ticket...)", max_chars=4000)
        submitted = st.form_submit_button("Gửi")
    if submitted and message.strip():
        with st.spinner("Agent đang xử lý..."):
            try:
                reply = api.agent(message.strip(), current)
            except ui_api.ApiError as exc:
                st.error(exc.message)
            else:
                record(reply["thread_id"], role, reply, message.strip())
                ss["current_thread"][role] = current = reply["thread_id"]
    thread = ss["threads"].get(current) if current else None
    if thread is None:
        return
    st.caption(f"Thread `{current}`")
    for who, text in thread["messages"]:
        with st.chat_message(who):
            st.write(text)
    if thread["status"] == "pending_approval" and thread["pending"]:
        show_pending(thread["pending"])
        st.info("Đang chờ người duyệt: chọn vai trò người duyệt ở thanh bên để duyệt.")


STATUS_LABEL = {"completed": "hoàn tất", "pending_approval": "đang chờ duyệt tiếp"}


def decide(api: ui_api.Api, thread_id: str, approve: bool, comment: str) -> None:
    """Send the decision; on success keep its result for the next run, then rerun so the panel refreshes."""
    try:
        reply = api.decide(thread_id, approve, comment)
    except ui_api.ApiError as exc:  # e.g. 404 unknown thread, 409 already decided
        st.error(f"Thread `{thread_id}`: {exc.message}")
        return
    record(thread_id, state()["threads"].get(thread_id, {}).get("role", "phiên khác"), reply, None)
    state()["decided"] = {
        "thread_id": thread_id,
        "approve": approve,
        "status": reply["status"],
        "answer": reply.get("answer"),
    }
    st.rerun()


def show_decided(decided: dict) -> None:
    verdict = "đã duyệt" if decided["approve"] else "đã từ chối"
    status = STATUS_LABEL.get(decided["status"], decided["status"])
    st.success(f"Thread `{decided['thread_id']}`: {verdict} · trạng thái: {status}.")
    if decided["answer"]:
        st.markdown(f"**Kết quả từ agent:** {decided['answer']}")


def approval_panel(api: ui_api.Api, role: str) -> None:
    ss = state()
    if "decided" in ss:
        show_decided(ss["decided"])  # kept until the next decision, not lost on the next rerun
    pending = {tid: t for tid, t in ss["threads"].items() if t["status"] == "pending_approval" and t["role"] != role}
    if not pending:
        st.write("Không có hành động nào đang chờ duyệt trong phiên này.")
    for tid, thread in pending.items():
        with st.container(border=True):
            st.caption(f"Thread `{tid}` · người yêu cầu: {thread['role']}")
            for who, text in thread["messages"]:
                st.markdown(f"**{'Người dùng' if who == 'user' else 'Agent'}:** {text}")
            if thread["pending"]:
                show_pending(thread["pending"])
            comment = st.text_input("Ghi chú", key=f"comment-{tid}", max_chars=500)
            approve, reject = st.columns(2)
            for column, verdict, label in ((approve, True, "Duyệt"), (reject, False, "Từ chối")):
                if column.button(label, key=f"{'approve' if verdict else 'reject'}-{tid}"):
                    decide(api, tid, verdict, comment)
    with st.expander("Duyệt theo thread id (thread từ phiên khác)"):
        tid = st.text_input("Thread id", key="manual-thread").strip()
        comment = st.text_input("Ghi chú", key="manual-comment", max_chars=500)
        approve, reject = st.columns(2)
        for column, verdict, label in ((approve, True, "Duyệt"), (reject, False, "Từ chối")):
            if column.button(label, key=f"manual-{'approve' if verdict else 'reject'}") and tid:
                decide(api, tid, verdict, comment)


def main() -> None:
    st.set_page_config(page_title="Trợ lý nội bộ ngân hàng", layout="wide")
    st.title("Trợ lý nội bộ ngân hàng")
    state()
    roles = ui_api.available_roles()
    if not roles:
        st.error(
            "Chưa cấu hình API key nào cho UI. Đặt ít nhất một biến "
            + ", ".join(f"`{v}`" for v in ui_api.ROLES.values())
            + " (key tạo bằng `scripts/make_key.py`)."
        )
        st.stop()
    base_url = ui_api.api_url()
    with st.sidebar:
        label = st.radio("Vai trò", [r.label for r in roles], key="role")
        st.caption(f"API: {base_url}")
    role = next(r for r in roles if r.label == label)
    api = ui_api.Api(base_url, role.key)
    ask, agent = st.tabs(["Hỏi đáp tài liệu", "Agent và duyệt"])
    with ask:
        ask_tab(api, role.label)
    with agent:
        if role.approver:
            st.subheader("Hành động chờ duyệt")
            approval_panel(api, role.label)
            st.divider()
        st.subheader("Trò chuyện với agent")
        agent_chat(api, role.label)


main()
