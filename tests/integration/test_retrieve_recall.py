"""retrieve() on the indexed corpus: recall@5 of both modes on sample questions, and the filters.

Needs the corpus ingested (scripts/ingest.py --data data) into QDRANT_COLLECTION (default
bank_docs) on QDRANT_URL; skipped when that collection is empty. The full evaluation with 50
questions is E-008 (T-022/T-023).
"""

import os

import pytest
from qdrant_client import QdrantClient

from app.contracts import User
from app.rag.retrieve import retrieve

pytestmark = pytest.mark.integration

# (question, user department, expected doc_id). Each asker is in a department allowed to read it.
QUESTIONS = [
    ("Mức lương tối thiểu tháng vùng I hiện nay là bao nhiêu?", "hr", "nd293-2025"),
    ("Mức lương tối thiểu giờ vùng II là bao nhiêu?", "hr", "nd293-2025"),
    ("Mức tham chiếu dùng để tính mức đóng bảo hiểm xã hội được xác định như thế nào?", "hr", "nd158-2025"),
    ("Những đối tượng nào phải tham gia bảo hiểm xã hội bắt buộc?", "hr", "nd158-2025"),
    ("Phí rút tiền mặt bằng thẻ tín dụng quốc tế VietinBank là bao nhiêu?", "public", "vtb-bieu-phi-the-tin-dung-qt"),
    ("Phí quản lý tài khoản thanh toán của khách hàng tổ chức là bao nhiêu?", "public", "vtb-bieu-phi-tai-khoan"),
    ("Phí phát hành thẻ ghi nợ nội địa cho doanh nghiệp là bao nhiêu?", "public", "vtb-bieu-phi-the-ghi-no-noi-dia"),
    ("Điều kiện để đăng ký trả góp qua thẻ tín dụng VietinBank là gì?", "credit", "vtb-dkdk-tra-gop-the-tin-dung"),
    ("Chủ thẻ tín dụng phải thanh toán tối thiểu bao nhiêu mỗi kỳ sao kê?", "credit", "vtb-dkdk-the-tin-dung"),
    ("Ký hiệu trên niêm phong bao, gói tiền mới in gồm những yếu tố nào?", "public", "tt01-2024-vbhn"),
    ("Dữ liệu cá nhân nhạy cảm được xử lý trong trường hợp nào?", "public", "luat91-2025"),
    ("Phí chuyển tiền ra nước ngoài của VietinBank được tính như thế nào?", "public", "vtb-bieu-phi-chuyen-tien"),
]
# Of 12. Measured 2026-10-29: 12/12 in both modes on the T-010 index; dense 11/12 with CR-009 chunks.
MIN_RECALL = {"dense": 10, "hybrid": 11}


@pytest.fixture(scope="module")
def corpus():
    connection = QdrantClient(url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"), timeout=60)
    name = os.getenv("QDRANT_COLLECTION", "bank_docs")
    if not connection.collection_exists(name) or connection.count(name).count == 0:
        connection.close()
        pytest.skip(f"collection {name} is not ingested")
    yield connection, name
    connection.close()


def ask(corpus, question, department, mode, k=5):
    connection, name = corpus
    return retrieve(question, User(f"u-{department}", department), k, mode, client=connection, collection=name)


@pytest.mark.parametrize("mode", ["dense", "hybrid"])
def test_recall_at_5_on_sample_questions(corpus, mode):
    found = [q for q, department, doc in QUESTIONS if doc in {h.doc_id for h in ask(corpus, q, department, mode)}]
    print(f"{mode}: recall@5 {len(found)}/{len(QUESTIONS)}")
    assert len(found) >= MIN_RECALL[mode], f"missed: {sorted(set(q for q, _, _ in QUESTIONS) - set(found))}"


@pytest.mark.parametrize("mode", ["dense", "hybrid"])
def test_filters_on_the_real_corpus(corpus, mode):
    wage = "Mức lương tối thiểu tháng vùng I hiện nay là bao nhiêu?"
    public = ask(corpus, wage, "public", mode, k=20)
    assert public and {h.department for h in public} == {"public"}  # hr documents are hidden
    credit = ask(corpus, wage, "credit", mode, k=20)
    assert {h.department for h in credit} <= {"credit", "public"}
    hr = ask(corpus, wage, "hr", mode, k=20)
    assert "nd293-2025" in {h.doc_id for h in hr}
    assert "nd74-2024" not in {h.doc_id for h in hr}  # superseded by nd293-2025
