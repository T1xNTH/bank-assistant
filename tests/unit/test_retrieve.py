"""retrieve(): mode switching and access filters on an in-memory Qdrant with fake embeddings."""

import pytest
from qdrant_client import QdrantClient, models

from app.contracts import User
from app.rag import embed as emb
from app.rag import retrieve as rag
from app.rag.retrieve import retrieve
from app.rag.store import upsert_chunks

pytestmark = pytest.mark.filterwarnings("ignore:Payload indexes have no effect in the local Qdrant")

COLLECTION = "test_bank_docs"
QUESTION_DENSE = [1.0, 0.0, 0.0]
QUESTION_SPARSE = {"indices": [7], "values": [1.0]}  # token 7: "rút tiền"
HR, CREDIT, PUBLIC = User("u-hr", "hr"), User("u-credit", "credit"), User("u-public", "public")


def dense(*head):
    return list(head) + [0.0] * (emb.DIM - len(head))


def chunk(doc_id, vector, sparse=None, **updates):
    return {
        "doc_id": doc_id,
        "source": f"{doc_id}.pdf",
        "page": 3,
        "chunk_index": 0,
        "text": f"Nội dung {doc_id}",
        "department": "public",
        "classification": "public",
        "effective_date": "2026-01-01",
        "superseded_by": None,
        "dense": dense(*vector),
        "sparse": sparse or {"indices": [99], "values": [0.1]},
    } | updates


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        emb, "embed", lambda texts: ([dense(*QUESTION_DENSE) for _ in texts], [QUESTION_SPARSE] * len(texts))
    )
    connection = QdrantClient(":memory:")
    yield connection
    connection.close()


def ids(hits):
    return [h.doc_id for h in hits]


def run(client, user=PUBLIC, **kwargs):
    return retrieve("phí rút tiền", user, client=client, collection=COLLECTION, **kwargs)


@pytest.fixture
def ranked(client):
    """Dense order: close, near, far, keyword. Only "keyword" matches the question's sparse token."""
    upsert_chunks(
        [
            chunk("close", (1.0, 0.1)),
            chunk("near", (1.0, 0.5)),
            chunk("far", (1.0, 1.0)),
            chunk("keyword", (0.1, 1.0), sparse={"indices": [7], "values": [0.9]}),
        ],
        client=client,
        collection=COLLECTION,
    )
    return client


def test_dense_ranks_by_cosine_only(ranked):
    assert ids(run(ranked, mode="dense", k=4)) == ["close", "near", "far", "keyword"]


def test_hybrid_fuses_dense_and_sparse_with_rrf(ranked):
    hits = run(ranked, mode="hybrid", k=2)
    # Only "keyword" shares a sparse token, so the sparse ranking is ["keyword"]. RRF with any
    # constant c: keyword 1/(c+4) + 1/(c+1) > close 1/(c+1) > near 1/(c+2).
    assert ids(hits) == ["keyword", "close"]
    assert ids(run(ranked, mode="dense", k=2)) == ["close", "near"]


def test_hybrid_is_the_default_mode(ranked):
    assert ids(run(ranked, k=2)) == ids(run(ranked, mode="hybrid", k=2))


def test_hit_carries_the_payload_and_score(ranked):
    [hit] = run(ranked, mode="dense", k=1)
    assert (hit.doc_id, hit.source, hit.page, hit.text) == ("close", "close.pdf", 3, "Nội dung close")
    assert (hit.department, hit.classification) == ("public", "public")
    assert 0.99 < hit.score <= 1.0  # cosine of (1, 0.1) with (1, 0)


@pytest.fixture
def mixed(client):
    upsert_chunks(
        [
            chunk("hr-wage", (1.0, 0.0), department="hr", classification="internal"),
            chunk("credit-loan", (1.0, 0.05), department="credit", classification="confidential"),
            chunk("old-fee", (1.0, 0.1), superseded_by="new-fee"),
            chunk("new-fee", (1.0, 0.5)),
        ],
        client=client,
        collection=COLLECTION,
    )
    return client


@pytest.mark.parametrize("mode", ["dense", "hybrid"])
@pytest.mark.parametrize(
    ("user", "visible"),
    [(HR, {"hr-wage", "new-fee"}), (CREDIT, {"credit-loan", "new-fee"}), (PUBLIC, {"new-fee"})],
)
def test_department_and_superseded_filters(mixed, mode, user, visible):
    assert set(ids(run(mixed, user, mode=mode, k=10))) == visible


@pytest.mark.parametrize("mode", ["dense", "hybrid"])
def test_filter_is_applied_inside_the_query_not_after(mixed, mode):
    # The three best-scoring chunks are hidden from a public user; a post-filter on the top 1 returns nothing.
    assert ids(run(mixed, PUBLIC, mode=mode, k=1)) == ["new-fee"]


@pytest.mark.parametrize("mode", ["dense", "hybrid"])
def test_more_hidden_chunks_than_candidates_do_not_crowd_out_permitted_ones(client, mode):
    hidden = [
        chunk("hr-doc", (1.0, i / 1000), chunk_index=i, department="hr", sparse=QUESTION_SPARSE)
        for i in range(rag.PREFETCH + 5)
    ]
    upsert_chunks([*hidden, chunk("public-doc", (1.0, 0.9))], client=client, collection=COLLECTION)
    assert ids(run(client, PUBLIC, mode=mode, k=3)) == ["public-doc"]


def test_a_chunk_without_superseded_by_is_excluded(client):
    upsert_chunks([chunk("current", (1.0, 0.5))], client=client, collection=COLLECTION)
    legacy = chunk("legacy", (1.0, 0.0))
    client.upsert(
        COLLECTION,
        [
            models.PointStruct(
                id=1,
                payload={k: v for k, v in legacy.items() if k not in ("dense", "sparse", "superseded_by")},
                vector={"dense": legacy["dense"], "sparse": models.SparseVector(**legacy["sparse"])},
            )
        ],
    )
    for mode in ("dense", "hybrid"):
        assert ids(run(client, mode=mode, k=5)) == ["current"]  # fail closed: unknown status is not "in force"


def test_the_question_is_embedded_once(ranked, monkeypatch):
    seen = []
    monkeypatch.setattr(emb, "embed", lambda texts: seen.append(texts) or ([dense(*QUESTION_DENSE)], [QUESTION_SPARSE]))
    run(ranked, mode="hybrid", k=2)
    assert seen == [["phí rút tiền"]]


def test_more_than_prefetch_results_can_be_requested(client):
    upsert_chunks(
        [chunk("doc", (1.0, i / 100), chunk_index=i) for i in range(rag.PREFETCH + 5)],
        client=client,
        collection=COLLECTION,
    )
    assert len(run(client, mode="hybrid", k=rag.PREFETCH + 5)) == rag.PREFETCH + 5


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"k": 0}, ValueError),
        ({"mode": "sparse"}, ValueError),
        ({"mode": "hybrid_rerank"}, NotImplementedError),
    ],
)
def test_invalid_arguments(ranked, kwargs, error):
    with pytest.raises(error):
        run(ranked, **kwargs)


def test_an_unknown_department_is_rejected(ranked):
    with pytest.raises(ValueError, match="department"):
        run(ranked, User("u-x", "treasury"))
