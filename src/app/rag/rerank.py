"""bge-reranker-v2-m3 CrossEncoder reranking with the refusal threshold.

Owner: A — Epic E-004. See docs/00-project/product-plan.md.

``rerank(question, hits, k)`` scores every (question, chunk text) pair with the
cross-encoder, maps the logit through a sigmoid to (0, 1), and returns the best
``k`` hits at or above the refusal threshold, best first, each with its rerank
score. An empty list means nothing relevant was found: the answerer refuses
(docs/12-ai/ai-design.md). The threshold is ``REFUSAL_THRESHOLD`` from the
environment, or ``DEFAULT_THRESHOLD`` when it is unset or blank. The model runs on
CPU (fp32) and is loaded once per process, on first use. Pairs are scored in one
forward pass per batch: FlagEmbedding's ``compute_score`` (1.4.2) scores its first
batch twice to probe the batch size, which doubles the cost of a 5-candidate rerank.
"""

from __future__ import annotations

import dataclasses
import os
import threading

from app.contracts import Hit

MODEL = "BAAI/bge-reranker-v2-m3"
BATCH_SIZE = 8
MAX_LENGTH = 1024  # tokens for question + chunk; chunks are ~800 characters, long table rows ~2100
QUESTION_MAX_LENGTH = MAX_LENGTH * 3 // 4  # as FlagReranker: a long question leaves room for the chunk
# Midway between the lowest top score of in-scope sample questions (0.74) and the highest of
# out-of-scope ones (0.34), with 5 candidates on bank_docs, 2026-10-30; see docs/07-development/rerank.md.
DEFAULT_THRESHOLD = 0.5

_instance = None
_lock = threading.Lock()


def rerank(question: str, hits: list[Hit], k: int, threshold: float | None = None) -> list[Hit]:
    """The best ``k`` of ``hits`` scoring at least ``threshold`` (default: refusal_threshold())."""
    if k < 1:
        raise ValueError(f"k must be at least 1, got {k}")
    cutoff = refusal_threshold() if threshold is None else threshold
    if not hits:
        return []
    scores = _model().score([(question, hit.text) for hit in hits])
    ranked = sorted(zip(scores, hits, strict=True), key=lambda pair: -pair[0])  # stable: ties keep fusion order
    return [dataclasses.replace(hit, score=float(score)) for score, hit in ranked if score >= cutoff][:k]


def refusal_threshold() -> float:
    """``REFUSAL_THRESHOLD`` as a probability in [0, 1]; a malformed value is an error, not a silent default."""
    raw = os.getenv("REFUSAL_THRESHOLD", "").strip()
    if not raw:
        return DEFAULT_THRESHOLD
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"REFUSAL_THRESHOLD must be a number in [0, 1], got {raw!r}") from None
    if not 0.0 <= value <= 1.0:  # also rejects nan
        raise ValueError(f"REFUSAL_THRESHOLD must be a number in [0, 1], got {raw!r}")
    return value


class _CrossEncoder:
    """Tokenizer and sequence-classification head of the reranker; ``score`` returns sigmoid scores."""

    def __init__(self) -> None:
        # Imported lazily: transformers pulls in torch.
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(MODEL)
        self.model = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()

    def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        import torch

        scores: list[float] = []
        with torch.inference_mode():
            for start in range(0, len(pairs), BATCH_SIZE):
                batch = pairs[start : start + BATCH_SIZE]
                inputs = self.tokenizer(
                    [self._question(q) for q, _ in batch],
                    [t for _, t in batch],
                    padding=True,
                    truncation="only_second",
                    max_length=MAX_LENGTH,
                    return_tensors="pt",
                )
                scores += torch.sigmoid(self.model(**inputs).logits.view(-1).float()).tolist()
        return scores

    def _question(self, question: str) -> str:
        """The question cut to QUESTION_MAX_LENGTH tokens, as FlagReranker 1.4.2 does on transformers 5.

        Truncating only the chunk fails when the question alone fills MAX_LENGTH, and /ask accepts
        2,000 characters (2,000 characters of emoji or punctuation are ~2,000 tokens).
        """
        ids = self.tokenizer(question, add_special_tokens=False)["input_ids"]
        if len(ids) <= QUESTION_MAX_LENGTH:
            return question
        return self.tokenizer.decode(ids[:QUESTION_MAX_LENGTH])


def _load() -> _CrossEncoder:
    return _CrossEncoder()


def _model():
    """The process-wide model; concurrent first calls load it once (2.3 GB)."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:  # another thread may have loaded it while we waited
                _instance = _load()
    return _instance
