"""POST /ask end to end: API key -> masking -> RagAnswerer -> Qdrant + bge-m3 + reranker -> LiteLLM -> citations.

Runs the FastAPI app in process with RAG_BACKEND=real, AUTH_BACKEND=apikey (keys made for the test in a
temporary file) and LLM_BACKEND=litellm against the compose services: Qdrant with the corpus ingested
into QDRANT_COLLECTION (default bank_docs) and the LiteLLM gateway on LLM_BASE_URL (default
http://127.0.0.1:4000) with LITELLM_MASTER_KEY set. Skipped when any of them is missing. Calls the
paid cloud model (about 15 questions, well under 0.01 USD with gpt-6-luna) and loads two models on
CPU, so it takes a few minutes.

Pages and facts below hold for the shared corpus only: the 30 PDFs of GitHub Release
``corpus-2026-10-28`` ingested with the CR-009 chunker, 2815 points. The VietinBank fee schedules are
browser prints, so a corpus printed again paginates and ranks differently; the fixture fails on any
other point count instead of reporting misleading misses.
"""

import hashlib
import json
import os
import re
import secrets
import urllib.request

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from app import deps
from app.config import Settings
from app.contracts import REFUSAL

pytestmark = pytest.mark.integration

# T-019 manual set: (department, question, source, pages holding the answer, fact the answer must state).
# Checked by reading the chunks; not taken from eval/golden.jsonl so the E-008 evaluation stays
# independent. The fact (a regex, case-insensitive) catches an answer that cites the right page but
# leaves out what was asked (PR #64 QA: a transfer-fee answer gave foreign-currency fees only).
QUESTIONS = [
    ("hr", "Mức lương tối thiểu tháng vùng I là bao nhiêu?", "293-cp.signed.pdf", {2}, r"5[.,]310[.,]000"),
    ("hr", "Mức lương tối thiểu giờ vùng IV là bao nhiêu?", "293-cp.signed.pdf", {2}, r"17[.,]800"),
    (
        "hr",
        "Tổng số giờ làm thêm trong một ngày không được vượt quá bao nhiêu?",
        "145.signed.pdf",
        {45},
        r"50\s*%|12 giờ",
    ),
    ("credit", "Hồ sơ đề nghị vay vốn gồm những gì?", "86-vbhn-nhnn.pdf", {11}, r"điều kiện vay"),
    (
        "credit",
        "Tổ chức tín dụng không được cho vay đối với những nhu cầu vốn nào?",
        "86-vbhn-nhnn.pdf",
        {9, 10},
        r"vàng miếng",
    ),
    (
        "credit",
        "Lãi suất áp dụng với dư nợ gốc bị quá hạn tối đa là bao nhiêu?",
        "86-vbhn-nhnn.pdf",
        {13, 14},
        r"150\s*%",
    ),
    (
        "credit",
        "Chủ thẻ tín dụng VietinBank được phát hành tối đa bao nhiêu thẻ phụ?",
        "DieukhoanvaDieukienphathanhvasudungthetindungcanhanVietinBank.pdf",
        {5},
        r"\b(0?3|ba)\b",
    ),
    ("public", "Phí phát hành lại thẻ ghi nợ quốc tế là bao nhiêu?", "dichvsptheghinoqt.pdf", {1}, r"50[.,]000"),
    (
        "public",
        "Phí cấp lại mã PIN thẻ ghi nợ quốc tế tại quầy là bao nhiêu?",
        "dichvsptheghinoqt.pdf",
        {3},
        r"27[.,]273",
    ),
    (
        "public",
        "Phí chuyển tiền trong nước khác hệ thống là bao nhiêu?",
        "dichvuthanhtoanchuyentienvtb.pdf",
        {2, 3},
        r"0[,.]03\s*%",
    ),
]
OUT_OF_SCOPE = [
    ("public", "Giá vàng SJC hôm nay là bao nhiêu?"),
    ("credit", "Thời tiết Hà Nội ngày mai thế nào?"),
]
CORPUS_POINTS = 2815  # release corpus-2026-10-28, scripts/ingest.py with the CR-009 chunker
HR_DOCS = {"145.signed.pdf", "158-ndcp.signed.pdf", "293-cp.signed.pdf", "74-cp.signed.pdf"}
SUPERSEDED = {"74-cp.signed.pdf", "06-vbhn-nhnn.pdf"}


def _gateway_up(base: str, key: str) -> bool:
    request = urllib.request.Request(f"{base}/health/liveliness", headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status == 200
    except OSError:
        return False


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    connection = QdrantClient(url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"), timeout=10)
    name = os.getenv("QDRANT_COLLECTION", "bank_docs")
    try:
        points = connection.count(name).count if connection.collection_exists(name) else 0
    except Exception:
        pytest.skip("Qdrant is not reachable")
    finally:
        connection.close()
    if points == 0:
        pytest.skip(f"collection {name} is empty; run scripts/ingest.py first")
    if points != CORPUS_POINTS:
        pytest.fail(
            f"{name} has {points} points, the shared corpus has {CORPUS_POINTS}: download release "
            "corpus-2026-10-28 into data/ (docs/07-development/corpus.md), then scripts/ingest.py --data data"
        )
    gateway_key = os.getenv("LITELLM_MASTER_KEY", "")
    base = os.getenv("LLM_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
    if not gateway_key or not _gateway_up(base, gateway_key):
        pytest.skip("LiteLLM gateway is not reachable or LITELLM_MASTER_KEY is unset")

    keys = {department: secrets.token_urlsafe(32) for department in ("public", "credit", "hr")}
    registry = tmp_path_factory.mktemp("keys") / "api_keys.json"
    registry.write_text(
        json.dumps(
            {
                hashlib.sha256(key.encode()).hexdigest(): {"user_id": f"t019-{dep}", "department": dep, "role": "staff"}
                for dep, key in keys.items()
            }
        )
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("AUTH_BACKEND", "apikey")
        patch.setenv("API_KEYS_FILE", str(registry))
        patch.setenv("LLM_BACKEND", "litellm")
        patch.setenv("LLM_BASE_URL", base)
        patch.delenv("RETRIEVAL_MODE", raising=False)
        # Settings.rag_backend is read at import; the dependency and the startup hook must both see "real".
        real = Settings(rag_backend="real")
        patch.setattr(deps, "get_settings", lambda: real)
        from app import main

        patch.setattr(main, "get_settings", lambda: real)
        with TestClient(main.create_app()) as client:
            yield client, keys


def ask(api, department, question, **body):
    client, keys = api
    response = client.post("/ask", json={"question": question, **body}, headers={"X-API-Key": keys[department]})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(("department", "question", "source", "pages", "fact"), QUESTIONS, ids=range(1, 11))
def test_in_scope_question_cites_the_right_file_and_page(api, department, question, source, pages, fact):
    body = ask(api, department, question)
    cited = [(c["source"], c["page"]) for c in body["citations"]]
    print(f"\n[{department}] {question}\n  {body['answer']}\n  {cited} {body['latency_ms']} ms")
    assert body["found"] is True
    assert body["retrieval_mode"] == "hybrid_rerank" and body["route"] == "cloud"
    assert any(s == source and p in pages for s, p in cited), cited
    assert re.search(fact, body["answer"], re.IGNORECASE), body["answer"]
    assert not SUPERSEDED & {s for s, _ in cited}
    # Every marker in the text has a citation and every citation is marked: the contract's [n] rule.
    assert {int(n) for n in re.findall(r"\[(\d+)\]", body["answer"])} == {c["n"] for c in body["citations"]}


@pytest.mark.parametrize(("department", "question"), OUT_OF_SCOPE)
def test_out_of_scope_question_is_refused(api, department, question):
    body = ask(api, department, question)
    assert (body["found"], body["answer"], body["citations"]) == (False, REFUSAL, [])


def test_other_department_cannot_read_hr_documents(api):
    body = ask(api, "credit", "Mức lương tối thiểu tháng vùng I là bao nhiêu?")
    assert not HR_DOCS & {c["source"] for c in body["citations"]}


def test_superseded_document_is_never_cited(api):
    # NĐ 74/2024 set the region I wage before NĐ 293/2025 replaced it.
    body = ask(api, "hr", "Theo Nghị định 74/2024/NĐ-CP, mức lương tối thiểu tháng vùng I là bao nhiêu?")
    assert not SUPERSEDED & {c["source"] for c in body["citations"]}


def test_mode_from_request_is_used(api):
    body = ask(api, "hr", "Mức lương tối thiểu tháng vùng I là bao nhiêu?", mode="dense")
    assert body["retrieval_mode"] == "dense"
    assert body["found"] is True


def test_missing_key_is_401(api):
    client, _ = api
    assert client.post("/ask", json={"question": "Phí phát hành lại thẻ?"}).status_code == 401
