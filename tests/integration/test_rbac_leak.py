"""NFR-06, FR-02 and FR-04b on the real index: no other department's chunk, no superseded citation,
confidential chunks answered by the local model.

Needs the corpus ingested from ``data/manifest.csv`` (``python scripts/ingest.py --data data``) into
QDRANT_COLLECTION (default bank_docs) on QDRANT_URL; skipped when that collection is empty. A label
changed in the manifest needs ``scripts/ingest.py --only <doc_id>`` before these tests pass.
``hybrid_rerank`` loads the reranker (CPU, a few seconds per question). The LLM is a fake that records
the alias, so no gateway or provider key is needed.

Owner: A — Epic E-010 (T-027). See docs/00-project/product-plan.md.
"""

import csv
import os
from pathlib import Path

import pytest
from qdrant_client import QdrantClient, models

from app.contracts import User
from app.rag.answer import RagAnswerer
from app.rag.retrieve import retrieve
from tests.fakes import FakeLLM

pytestmark = pytest.mark.integration

MANIFEST = Path(__file__).resolve().parents[2] / "data/manifest.csv"
MODES = ["dense", "hybrid", "hybrid_rerank"]
DEPARTMENTS = ["public", "credit", "hr"]

# Questions answered by one department's documents, asked from every department. Each one retrieves
# its own department's document for its owner (checked below), so a leak would have something to leak.
CROSS_DEPARTMENT = [
    ("Mức lương tối thiểu tháng vùng I hiện nay là bao nhiêu?", "hr", "nd293-2025"),
    ("Mức tham chiếu dùng để tính mức đóng bảo hiểm xã hội được xác định như thế nào?", "hr", "nd158-2025"),
    ("Người lao động được nghỉ hằng năm bao nhiêu ngày theo quy định về điều kiện lao động?", "hr", "nd145-2020"),
    ("Thời giờ làm việc bình thường của người lao động là bao nhiêu giờ một ngày?", "hr", "nd145-2020"),
    ("Điều kiện để đăng ký trả góp qua thẻ tín dụng VietinBank là gì?", "credit", "vtb-dkdk-tra-gop-the-tin-dung"),
    ("Chủ thẻ tín dụng phải thanh toán tối thiểu bao nhiêu mỗi kỳ sao kê?", "credit", "vtb-dkdk-the-tin-dung"),
    ("Tổ chức tín dụng không được cho vay đối với những nhu cầu vốn nào?", "credit", "tt39-2016-vbhn86"),
]
# Questions aimed at the two superseded documents (nd74-2024 -> nd293-2025, tt39-2016-vbhn06 -> vbhn86).
SUPERSEDED_QUESTIONS = [
    "Mức lương tối thiểu vùng áp dụng từ ngày 1/7/2024 theo Nghị định 74/2024/NĐ-CP là bao nhiêu?",
    "Mức lương tối thiểu tháng vùng I hiện nay là bao nhiêu?",
    "Văn bản hợp nhất 06/VBHN-NHNN quy định hoạt động cho vay của tổ chức tín dụng như thế nào?",
    "Tổ chức tín dụng không được cho vay đối với những nhu cầu vốn nào?",
]
# (question, asker's department, confidential document it is about)
CONFIDENTIAL_QUESTIONS = [
    ("Mức lương tối thiểu tháng vùng I hiện nay là bao nhiêu?", "hr", "nd293-2025"),
    ("Điều kiện để đăng ký trả góp qua thẻ tín dụng VietinBank là gì?", "credit", "vtb-dkdk-tra-gop-the-tin-dung"),
]
PUBLIC_QUESTION = ("Phí rút tiền mặt bằng thẻ tín dụng quốc tế VietinBank là bao nhiêu?", "public")


def manifest_rows() -> list[dict]:
    with MANIFEST.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


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


def count(corpus, **payload) -> int:
    connection, name = corpus
    must = [models.FieldCondition(key=key, match=models.MatchValue(value=value)) for key, value in payload.items()]
    return connection.count(name, count_filter=models.Filter(must=must), exact=True).count


# The index carries the manifest's labels


def test_manifest_labels_at_least_four_documents_internal_or_confidential():
    labels = {row["doc_id"]: row["classification"] for row in manifest_rows()}
    sensitive = {doc for doc, label in labels.items() if label != "public"}
    assert len(sensitive) >= 4
    assert {"internal", "confidential"} <= set(labels.values())
    superseded = {row["doc_id"] for row in manifest_rows() if row["superseded_by"]}
    assert not {doc for doc, label in labels.items() if label == "confidential"} & superseded  # still answerable


def test_every_indexed_chunk_has_its_manifest_department_and_classification(corpus):
    stale = []
    for row in manifest_rows():
        total = count(corpus, doc_id=row["doc_id"])
        labelled = count(
            corpus, doc_id=row["doc_id"], department=row["department"], classification=row["classification"]
        )
        if total == 0 or labelled != total:
            stale.append(f"{row['doc_id']}: {labelled}/{total} chunks {row['department']}/{row['classification']}")
    assert not stale, "re-run scripts/ingest.py --only <doc_id>: " + "; ".join(stale)


# NFR-06: 0 chunks of another department in the top k


@pytest.mark.parametrize("question,owner,doc_id", CROSS_DEPARTMENT)
def test_owner_department_retrieves_the_document(corpus, question, owner, doc_id):
    assert doc_id in {h.doc_id for h in ask(corpus, question, owner, "hybrid")}


@pytest.mark.parametrize("mode", MODES)
def test_no_chunk_of_another_department_in_any_mode(corpus, mode):
    leaks = []
    for question, _, _ in CROSS_DEPARTMENT:
        for department in DEPARTMENTS:
            for hit in ask(corpus, question, department, mode):
                if hit.department not in {department, "public"}:
                    leaks.append(f"{department} <- {hit.doc_id} ({hit.department}): {question}")
    assert leaks == []


@pytest.mark.parametrize("mode", ["dense", "hybrid"])
def test_credit_never_sees_hr_deep_in_the_ranking(corpus, mode):
    for question, owner, _ in CROSS_DEPARTMENT:
        if owner == "hr":
            assert {h.department for h in ask(corpus, question, "credit", mode, k=50)} <= {"credit", "public"}


# FR-02: superseded documents are indexed but never retrieved or cited


def test_superseded_documents_are_indexed(corpus):
    superseded = [row["doc_id"] for row in manifest_rows() if row["superseded_by"]]
    assert len(superseded) >= 2
    assert all(count(corpus, doc_id=doc) > 0 for doc in superseded)  # the filter hides them, not their absence


@pytest.mark.parametrize("mode", MODES)
def test_superseded_documents_are_never_cited(corpus, mode):
    rows = manifest_rows()
    superseded = {row["doc_id"] for row in rows if row["superseded_by"]}
    superseded_files = {row["file"] for row in rows if row["superseded_by"]}
    connection, name = corpus

    def real(question, user, k, m):
        return retrieve(question, user, k, m, client=connection, collection=name)

    for question in SUPERSEDED_QUESTIONS:
        for department in DEPARTMENTS:
            assert not superseded & {h.doc_id for h in ask(corpus, question, department, mode)}
            llm = FakeLLM("Theo tài liệu [1][2][3][4][5].")  # cites every hit it was given
            result = RagAnswerer(real, llm).answer(question, User(f"u-{department}", department), mode)
            assert not superseded_files & {c.source for c in result.citations}, (question, department)


# FR-04b: a confidential chunk sends the question to the local model


@pytest.mark.parametrize("question,department,doc_id", CONFIDENTIAL_QUESTIONS)
@pytest.mark.parametrize("mode", MODES)
def test_question_about_a_confidential_document_routes_local(corpus, mode, question, department, doc_id):
    connection, name = corpus
    seen = []

    def real(q, user, k, m):
        hits = retrieve(q, user, k, m, client=connection, collection=name)
        seen.extend(hits)
        return hits

    llm = FakeLLM("Theo tài liệu [1].")
    result = RagAnswerer(real, llm).answer(question, User(f"u-{department}", department), mode)
    assert doc_id in {h.doc_id for h in seen if h.classification == "confidential"}
    assert result.route == "local"
    assert [alias for _, alias in llm.calls] == ["local-chat"]


@pytest.mark.parametrize("mode", MODES)
def test_public_question_stays_on_cloud(corpus, mode):
    connection, name = corpus
    question, department = PUBLIC_QUESTION
    seen = []

    def real(q, user, k, m):
        hits = retrieve(q, user, k, m, client=connection, collection=name)
        seen.extend(hits)
        return hits

    llm = FakeLLM("Theo tài liệu [1].")
    result = RagAnswerer(real, llm).answer(question, User(f"u-{department}", department), mode)
    assert seen and {h.classification for h in seen} <= {"public", "internal"}
    assert result.route == "cloud" and [alias for _, alias in llm.calls] == ["cloud-chat"]
