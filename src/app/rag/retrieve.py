"""Dense and hybrid (RRF) retrieval with RBAC and superseded filters.

``retrieve(question, user, k, mode)`` embeds the question with bge-m3 and queries Qdrant:
``dense`` ranks by cosine on the dense vector; ``hybrid`` fuses the dense and sparse rankings
with reciprocal rank fusion inside Qdrant (query API, ``Fusion.RRF``). Both apply the access
filter in the query itself, never afterwards (docs/02-architecture/architecture.md):
``department`` in {user's department, "public"} and ``superseded_by`` is null. ``hybrid_rerank``
is ``hybrid`` followed by ``rerank.rerank`` (T-017).

Owner: A — Epic E-004 / E-010. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

from typing import get_args

from qdrant_client import QdrantClient, models

from app.contracts import Department, Hit, RetrievalMode, User
from app.rag import embed
from app.rag.store import _collection_name, _connection

# Candidates each of dense and sparse contributes to the fusion; RRF needs more than k from
# each branch so that a chunk ranked well by only one of them can still reach the top k.
PREFETCH = 20
_DEPARTMENTS = set(get_args(Department))


def retrieve(
    question: str,
    user: User,
    k: int = 5,
    mode: RetrievalMode = "hybrid",
    *,
    client: QdrantClient | None = None,
    collection: str | None = None,
) -> list[Hit]:
    """Return the top ``k`` chunks ``user`` may read, best first."""
    if k < 1:
        raise ValueError(f"k must be at least 1, got {k}")
    if mode == "hybrid_rerank":
        raise NotImplementedError("hybrid_rerank: hybrid + rerank.rerank, T-017")
    if mode not in ("dense", "hybrid"):
        raise ValueError(f"Unknown retrieval mode {mode!r}")
    flt = access_filter(user)
    [dense], [sparse] = embed.embed([question])
    with _connection(client) as connection:
        if mode == "dense":
            response = connection.query_points(
                _collection_name(collection), query=dense, using="dense", query_filter=flt, limit=k, with_payload=True
            )
        else:
            limit = max(PREFETCH, k)  # each branch is filtered: the fusion only sees permitted chunks
            response = connection.query_points(
                _collection_name(collection),
                prefetch=[
                    models.Prefetch(query=dense, using="dense", filter=flt, limit=limit),
                    models.Prefetch(query=models.SparseVector(**sparse), using="sparse", filter=flt, limit=limit),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=k,
                with_payload=True,
            )
    return [_hit(point) for point in response.points]


def access_filter(user: User) -> models.Filter:
    """Chunks of the user's department or public, and still in force."""
    if user.department not in _DEPARTMENTS:  # fail closed: an unknown department sees nothing extra
        raise ValueError(f"Unknown department {user.department!r}")
    departments = sorted({user.department, "public"})
    return models.Filter(
        must=[
            models.FieldCondition(key="department", match=models.MatchAny(any=departments)),
            models.IsNullCondition(is_null=models.PayloadField(key="superseded_by")),
        ]
    )


def _hit(point: models.ScoredPoint) -> Hit:
    p = point.payload
    return Hit(
        doc_id=p["doc_id"],
        source=p["source"],
        page=p["page"],
        text=p["text"],
        score=point.score,
        department=p["department"],
        classification=p["classification"],
    )
