"""bge-m3 dense + sparse embeddings.

Owner: A — Epic E-003. See docs/00-project/product-plan.md.

``embed(texts)`` returns one dense vector (1024 floats, L2-normalised, for the
``dense`` named vector with cosine distance) and one sparse vector
``{"indices": [...], "values": [...]}`` (bge-m3 lexical weights by token id, for
the ``sparse`` vector) per text, in input order. Documents and queries must go
through this same function so both sides use one model and settings. The model
runs on CPU (fp32) and is loaded once per process, on first use.
"""

from __future__ import annotations

import threading

MODEL = "BAAI/bge-m3"
DIM = 1024
BATCH_SIZE = 16
MAX_LENGTH = 2048  # tokens; chunks are ~800 characters, the longest table rows ~2100

_instance = None
_lock = threading.Lock()


def _load():
    # Imported lazily: FlagEmbedding pulls in torch.
    from FlagEmbedding import BGEM3FlagModel

    return BGEM3FlagModel(MODEL, use_fp16=False, devices="cpu", normalize_embeddings=True)


def _model():
    """The process-wide model; concurrent first calls load it once (2.2 GB, ~1 min)."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:  # another thread may have loaded it while we waited
                _instance = _load()
    return _instance


def embed(texts: list[str]) -> tuple[list[list[float]], list[dict]]:
    if not texts:
        return [], []
    out = _model().encode(
        list(texts),
        batch_size=BATCH_SIZE,
        max_length=MAX_LENGTH,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )
    dense = [[float(x) for x in vec] for vec in out["dense_vecs"]]
    sparse = [to_sparse(weights) for weights in out["lexical_weights"]]
    return dense, sparse


def to_sparse(weights: dict) -> dict:
    """bge-m3 lexical weights ({token id as str: weight}) as sorted Qdrant sparse-vector fields."""
    items = sorted((int(token), float(weight)) for token, weight in weights.items() if float(weight) > 0)
    return {"indices": [token for token, _ in items], "values": [weight for _, weight in items]}
