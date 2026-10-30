"""hybrid_rerank on the indexed corpus with the real bge-reranker-v2-m3: in-scope questions keep their
document, out-of-scope ones return nothing at the default threshold.

Needs the corpus ingested into QDRANT_COLLECTION (default bank_docs) on QDRANT_URL; skipped when that
collection is empty. Loads two models on CPU and takes a few minutes. The 50-question evaluation of
refusals is E-008 (T-022/T-023).
"""

import os

import pytest
from qdrant_client import QdrantClient

from app.contracts import User
from app.rag import rerank
from app.rag.retrieve import retrieve
from tests.integration.test_retrieve_recall import QUESTIONS

pytestmark = pytest.mark.integration

# Not answerable from the corpus: unrelated topics, and banking questions about other banks or live data.
OUT_OF_SCOPE = [
    ("Thời tiết Hà Nội ngày mai thế nào?", "public"),
    ("Đội tuyển bóng đá Việt Nam vô địch AFF Cup năm nào?", "public"),
    ("Cách nấu phở bò ngon tại nhà?", "public"),
    ("Viết hàm Python sắp xếp một danh sách số nguyên.", "public"),
    ("Thủ đô của nước Pháp là thành phố nào?", "public"),
    ("Giá vàng SJC hôm nay là bao nhiêu?", "public"),
    ("Lãi suất tiết kiệm kỳ hạn 12 tháng của Vietcombank là bao nhiêu?", "public"),
    ("Tỷ giá USD/VND hôm nay là bao nhiêu?", "public"),
    ("Giá cổ phiếu CTG hôm nay là bao nhiêu?", "public"),
    ("Mức phí mở thẻ của Techcombank là bao nhiêu?", "public"),
    ("Lương tháng 13 của nhân viên ngân hàng được tính như thế nào?", "hr"),
    ("Quy định về chế độ nghỉ phép năm của nhân viên VietinBank?", "hr"),
    ("Ngân hàng Nhà nước có bao nhiêu chi nhánh?", "public"),
    ("Thuế thu nhập cá nhân bậc cao nhất là bao nhiêu phần trăm?", "public"),
]


@pytest.fixture(scope="module")
def corpus():
    connection = QdrantClient(url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"), timeout=60)
    name = os.getenv("QDRANT_COLLECTION", "bank_docs")
    if not connection.collection_exists(name) or connection.count(name).count == 0:
        connection.close()
        pytest.skip(f"collection {name} is not ingested")
    yield connection, name
    connection.close()


@pytest.fixture(autouse=True)
def defaults(monkeypatch):
    monkeypatch.delenv("REFUSAL_THRESHOLD", raising=False)
    monkeypatch.delenv("RERANK_CANDIDATES", raising=False)


def ask(corpus, question, department):
    connection, name = corpus
    return retrieve(
        question, User(f"u-{department}", department), 5, "hybrid_rerank", client=connection, collection=name
    )


def test_in_scope_questions_keep_their_document_above_the_threshold(corpus):
    missed = []
    for question, department, doc in QUESTIONS:
        hits = ask(corpus, question, department)
        assert all(h.score >= rerank.DEFAULT_THRESHOLD for h in hits)
        assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)
        if doc not in {h.doc_id for h in hits}:
            missed.append(question)
    print(f"hybrid_rerank: {len(QUESTIONS) - len(missed)}/{len(QUESTIONS)} in-scope questions answered")
    assert len(missed) <= 1, missed  # measured 12/12 on 2026-10-30


def test_out_of_scope_questions_return_nothing(corpus):
    answered = {q: [(h.doc_id, round(h.score, 3)) for h in ask(corpus, q, d)] for q, d in OUT_OF_SCOPE}
    answered = {q: hits for q, hits in answered.items() if hits}
    print(f"hybrid_rerank: {len(OUT_OF_SCOPE) - len(answered)}/{len(OUT_OF_SCOPE)} out-of-scope questions refused")
    assert not answered  # measured 14/14 on 2026-10-30, highest top score 0.34
