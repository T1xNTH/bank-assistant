"""Real Qdrant 1.12.x tests, each using a disposable, uniquely named collection."""

import os
from uuid import uuid4

import pytest
from qdrant_client import QdrantClient, models

from app.rag.store import ensure_collection, point_id, replace_document, upsert_chunks

pytestmark = pytest.mark.integration


def chunk(index=0, **updates):
    return {
        "doc_id": "synthetic-doc",
        "source": "synthetic.pdf",
        "page": 1,
        "chunk_index": index,
        "text": f"Synthetic policy chunk {index}",
        "department": "public",
        "classification": "public",
        "effective_date": "2026-01-01",
        "superseded_by": None,
        "dense": [1.0] + [0.0] * 1023,
        "sparse": {"indices": [4, 8], "values": [0.4, 0.8]},
    } | updates


@pytest.fixture
def store(monkeypatch):
    url = os.getenv("QDRANT_TEST_URL", "http://127.0.0.1:6333")
    name = "test_bank_docs_" + uuid4().hex
    connection = QdrantClient(url=url, timeout=10)
    # Integration mode is explicit: an unavailable service fails rather than silently skipping.
    connection.get_collections()
    monkeypatch.setenv("QDRANT_URL", url)
    monkeypatch.setenv("QDRANT_COLLECTION", name)
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    try:
        yield connection, name
    finally:
        if connection.collection_exists(name):
            connection.delete_collection(name)
        connection.close()


def test_collection_vectors_and_keyword_indexes_are_repeatable(store):
    connection, name = store
    ensure_collection()
    ensure_collection()
    info = connection.get_collection(name)
    assert info.config.params.vectors["dense"].size == 1024
    assert info.config.params.vectors["dense"].distance == models.Distance.COSINE
    assert "sparse" in info.config.params.sparse_vectors
    assert all(
        info.payload_schema[field].data_type == models.PayloadSchemaType.KEYWORD
        for field in ("department", "classification", "superseded_by")
    )


def test_upsert_twice_keeps_count_stable_across_batches_and_updates_payload(store):
    connection, name = store
    chunks = [chunk(index) for index in range(65)]  # crosses the 64-point batch boundary
    assert upsert_chunks(chunks) == 65
    first = connection.count(name, exact=True).count
    assert upsert_chunks(chunks) == 65
    assert connection.count(name, exact=True).count == first == 65
    assert upsert_chunks([chunk(text="Replacement", superseded_by="new-doc")]) == 1
    assert connection.count(name, exact=True).count == first
    stored = connection.retrieve(name, [point_id("synthetic-doc", 0)], with_vectors=True)[0]
    assert stored.payload["text"] == "Replacement"
    assert stored.payload["superseded_by"] == "new-doc"
    assert set(stored.vector) == {"dense", "sparse"}
    assert stored.vector["sparse"].indices == [4, 8]
    assert stored.vector["sparse"].values == pytest.approx([0.4, 0.8])
    current = connection.count(
        name,
        count_filter=models.Filter(
            must=[
                models.FieldCondition(key="department", match=models.MatchValue(value="public")),
                models.FieldCondition(key="classification", match=models.MatchValue(value="public")),
                models.IsNullCondition(is_null=models.PayloadField(key="superseded_by")),
            ]
        ),
        exact=True,
    )
    assert current.count == 64


def test_reingesting_fewer_superseded_chunks_leaves_none_retrievable(store):
    connection, name = store
    replace_document("synthetic-doc", [chunk(index) for index in range(70)])
    upsert_chunks([chunk(doc_id="other-doc")])
    assert replace_document("synthetic-doc", [chunk(index, superseded_by="new-doc") for index in range(3)]) == 3
    assert connection.count(name, exact=True).count == 4
    current = connection.count(
        name,
        count_filter=models.Filter(
            must=[
                models.FieldCondition(key="department", match=models.MatchAny(any=["credit", "public"])),
                models.IsNullCondition(is_null=models.PayloadField(key="superseded_by")),
            ]
        ),
        exact=True,
    )
    assert current.count == 1  # only other-doc


def test_incompatible_existing_vectors_leave_data_untouched(store):
    connection, name = store
    connection.create_collection(name, vectors_config={"dense": models.VectorParams(size=8, distance="Cosine")})
    connection.upsert(
        name, [models.PointStruct(id=1, vector={"dense": [1.0] * 8}, payload={"text": "keep"})], wait=True
    )
    with pytest.raises(ValueError, match="incompatible"):
        upsert_chunks([chunk()])
    assert connection.count(name, exact=True).count == 1
    assert connection.retrieve(name, [1])[0].payload == {"text": "keep"}


def test_incompatible_payload_index_is_not_silently_replaced(store):
    connection, name = store
    connection.create_collection(
        name,
        vectors_config={"dense": models.VectorParams(size=1024, distance="Cosine")},
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
    )
    connection.create_payload_index(name, "department", field_schema=models.PayloadSchemaType.INTEGER, wait=True)
    with pytest.raises(ValueError, match="incompatible"):
        ensure_collection()
    assert connection.get_collection(name).payload_schema["department"].data_type == models.PayloadSchemaType.INTEGER
