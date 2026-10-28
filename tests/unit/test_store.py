from copy import deepcopy
from uuid import UUID

import pytest
from qdrant_client import QdrantClient, models

from app.rag.store import ensure_collection, point_id, upsert_chunks


def sample_chunk(**updates):
    chunk = {
        "doc_id": "public-doc",
        "source": "public.pdf",
        "page": 1,
        "chunk_index": 0,
        "text": "Public policy text",
        "department": "public",
        "classification": "public",
        "effective_date": "2026-01-01",
        "superseded_by": None,
        "dense": [1.0] + [0.0] * 1023,
        "sparse": {"indices": [4, 8], "values": [0.4, 0.8]},
    }
    return chunk | updates


@pytest.fixture
def client():
    connection = QdrantClient(":memory:")
    yield connection
    connection.close()


pytestmark = pytest.mark.filterwarnings("ignore:Payload indexes have no effect in the local Qdrant")


def test_point_identity_is_stable_and_uses_document_and_chunk_index():
    assert UUID(point_id("a", 0)).version == 5
    assert point_id("a", 0) == point_id("a", 0)
    assert len({point_id("a", 0), point_id("a", 1), point_id("b", 0)}) == 3
    assert point_id("a:1", 2) != point_id("a", 12)


def test_upsert_overwrites_same_identity_without_mutating_input(client):
    chunks = [sample_chunk(), sample_chunk(chunk_index=1, text="Second chunk")]
    original = deepcopy(chunks)
    assert upsert_chunks(chunks, client=client) == 2
    assert upsert_chunks(chunks, client=client) == 2
    assert client.count("bank_docs", exact=True).count == 2
    upsert_chunks([sample_chunk(text="Updated text")], client=client)
    stored = client.retrieve("bank_docs", [point_id("public-doc", 0)], with_vectors=True)[0]
    assert stored.payload["text"] == "Updated text"
    assert set(stored.vector) == {"dense", "sparse"}
    assert "dense" not in stored.payload and "sparse" not in stored.payload
    assert chunks == original


def test_empty_input_does_not_create_collection(client):
    assert upsert_chunks([], client=client) == 0
    assert not client.collection_exists("bank_docs")


@pytest.mark.parametrize(
    "updates",
    [
        {"department": None},
        {"classification": "unknown"},
        {"doc_id": ""},
        {"page": 0},
        {"chunk_index": -1},
        {"chunk_index": True},
        {"effective_date": "2026-02-30"},
        {"dense": [1.0]},
        {"dense": [float("nan")] * 1024},
        {"sparse": {"indices": [1, 1], "values": [0.1, 0.2]}},
        {"sparse": {"indices": [1], "values": []}},
        {"sparse": {"indices": [-1], "values": [1.0]}},
        {"sparse": {"indices": [1], "values": [float("inf")]}},
    ],
)
def test_invalid_chunks_fail_before_writing_any_batch(client, updates):
    with pytest.raises(ValueError):
        upsert_chunks([sample_chunk(), sample_chunk(**updates)], client=client)
    assert not client.collection_exists("bank_docs")


def test_missing_security_metadata_is_rejected(client):
    chunk = sample_chunk()
    del chunk["classification"]
    with pytest.raises(ValueError):
        upsert_chunks([chunk], client=client)
    assert not client.collection_exists("bank_docs")


def test_empty_superseded_field_becomes_null_and_extra_metadata_is_omitted(client):
    upsert_chunks([sample_chunk(superseded_by="", private_extra="omit")], client=client)
    payload = client.retrieve("bank_docs", [point_id("public-doc", 0)])[0].payload
    assert payload["superseded_by"] is None
    assert "private_extra" not in payload


def test_incompatible_collection_is_not_recreated(client):
    client.create_collection("bank_docs", vectors_config={"dense": models.VectorParams(size=8, distance="Cosine")})
    with pytest.raises(ValueError, match="incompatible"):
        ensure_collection(client=client)
    assert client.get_collection("bank_docs").config.params.vectors["dense"].size == 8


def test_named_collection_and_repeated_ensure_are_supported(client):
    ensure_collection(client=client, collection="isolated")
    ensure_collection(client=client, collection="isolated")
    assert not client.collection_exists("bank_docs")
    info = client.get_collection("isolated").config.params
    assert info.vectors["dense"].size == 1024
    assert info.vectors["dense"].distance == models.Distance.COSINE
    assert "sparse" in info.sparse_vectors
