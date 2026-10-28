"""Qdrant dense/sparse storage; input is payload metadata plus ``dense`` and ``sparse``.

Owner: A — Epic E-003. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Annotated, Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.rag.embed import DIM

COLLECTION = "bank_docs"
BATCH_SIZE = 64
_INDEX_FIELDS = ("department", "classification", "superseded_by")
_NonEmpty = Annotated[str, Field(min_length=1)]
_TokenId = Annotated[int, Field(strict=True, ge=0, le=2**32 - 1)]


class _Sparse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    indices: list[_TokenId]
    values: list[FiniteFloat]

    @model_validator(mode="after")
    def consistent(self) -> _Sparse:
        if len(self.indices) != len(self.values) or len(set(self.indices)) != len(self.indices):
            raise ValueError("Sparse indices must be unique and match values")
        return self


class _Chunk(BaseModel):
    # Whitelist payload fields; never infer public access when security metadata is missing.
    model_config = ConfigDict(strict=True, extra="ignore")
    doc_id: _NonEmpty
    source: _NonEmpty
    page: Annotated[int, Field(ge=1)]
    chunk_index: Annotated[int, Field(ge=0)]
    text: _NonEmpty
    department: Literal["public", "credit", "hr"]
    classification: Literal["public", "internal", "confidential"]
    effective_date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    superseded_by: _NonEmpty | None
    dense: Annotated[list[FiniteFloat], Field(min_length=DIM, max_length=DIM)]
    sparse: _Sparse

    @field_validator("effective_date")
    @classmethod
    def valid_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value

    @field_validator("superseded_by", mode="before")
    @classmethod
    def empty_means_current(cls, value: object) -> object:
        return None if value == "" else value


def point_id(doc_id: str, chunk_index: int) -> str:
    """Stable UUID for document/chunk identity; content changes replace the same point."""
    identity = json.dumps(["bank-assistant", doc_id, chunk_index], ensure_ascii=False, separators=(",", ":"))
    return str(uuid5(NAMESPACE_URL, identity))


@contextmanager
def _connection(client: QdrantClient | None) -> Iterator[QdrantClient]:
    connection = (
        client
        if client is not None
        else QdrantClient(
            url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"),
            api_key=os.getenv("QDRANT_API_KEY") or None,
            timeout=10,
        )
    )
    try:
        yield connection
    finally:
        if client is None:
            connection.close()


def _collection_name(collection: str | None) -> str:
    return collection if collection is not None else os.getenv("QDRANT_COLLECTION", COLLECTION)


def ensure_collection(*, client: QdrantClient | None = None, collection: str | None = None) -> None:
    """Create/validate the collection and keyword indexes without deleting existing data."""
    name = _collection_name(collection)
    with _connection(client) as connection:
        if not connection.collection_exists(name):
            try:
                connection.create_collection(
                    collection_name=name,
                    vectors_config={"dense": models.VectorParams(size=DIM, distance=models.Distance.COSINE)},
                    sparse_vectors_config={"sparse": models.SparseVectorParams()},
                )
            except UnexpectedResponse as exc:
                if exc.status_code != 409:  # Another ingester may have created it concurrently.
                    raise
        info = connection.get_collection(name)
        vectors = info.config.params.vectors
        sparse = info.config.params.sparse_vectors or {}
        if (
            not isinstance(vectors, dict)
            or "dense" not in vectors
            or vectors["dense"].size != DIM
            or vectors["dense"].distance != models.Distance.COSINE
            or "sparse" not in sparse
        ):
            raise ValueError("Existing collection has incompatible dense/sparse vector configuration")
        for field in _INDEX_FIELDS:
            if (
                field in info.payload_schema
                and info.payload_schema[field].data_type != models.PayloadSchemaType.KEYWORD
            ):
                raise ValueError("Existing collection has incompatible payload index type")
        for field in _INDEX_FIELDS:
            if field not in info.payload_schema:
                connection.create_payload_index(name, field, field_schema=models.PayloadSchemaType.KEYWORD, wait=True)


def upsert_chunks(chunks: list[dict], *, client: QdrantClient | None = None, collection: str | None = None) -> int:
    """Validate all input, then upsert in batches; return chunks submitted, not new-point count.

    Existing IDs are replaced. This does not remove stale chunks after re-chunking a document.
    Each batch waits for completion; transport failure can leave earlier batches committed.
    Replaying the same input converges to the same points.
    """
    points = []
    for raw in chunks:
        chunk = _Chunk.model_validate(raw)
        points.append(
            models.PointStruct(
                id=point_id(chunk.doc_id, chunk.chunk_index),
                payload=chunk.model_dump(exclude={"dense", "sparse"}),
                vector={"dense": chunk.dense, "sparse": models.SparseVector(**chunk.sparse.model_dump())},
            )
        )
    if not points:
        return 0
    name = _collection_name(collection)
    with _connection(client) as connection:
        ensure_collection(client=connection, collection=name)
        for start in range(0, len(points), BATCH_SIZE):
            connection.upsert(name, points=points[start : start + BATCH_SIZE], wait=True)
    return len(points)
