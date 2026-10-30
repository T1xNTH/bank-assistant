"""Answerer implementation: retrieve -> prompt -> llm.chat -> citations / refusal.

``RagAnswerer.answer`` retrieves up to ``k`` hits the user may read. No hits (nothing reached the
rerank threshold) means ``REFUSAL`` without calling the LLM. Otherwise the model answers from the
numbered context and every ``[n]`` marker it writes becomes a ``Citation`` of ``hits[n - 1]``.
Markers outside 1..len(hits) are dropped from the text, so each remaining marker has its citation
(docs/04-api/contract.md). The answer becomes ``REFUSAL`` when it cites nothing (the model refused,
or answered without grounding, and NFR-04 requires a citation on every answer) or when it contains
``CANARY``.

Routing sensitive questions to the local model is E-010; this always uses ``cloud-chat``.

Owner: A — Epic E-004. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import os
import re
import time
from collections.abc import Callable
from typing import get_args

from app.contracts import LLM, REFUSAL, AskResult, Citation, Hit, RetrievalMode, User
from app.prompts import CANARY, SYSTEM, user_message

ALIAS = "cloud-chat"
DEFAULT_K = 5
DEFAULT_MODE: RetrievalMode = "hybrid_rerank"
# [1], [1, 2] and [1;2] all count: models write the grouped forms despite the prompt's example.
# The leading whitespace goes with the marker so dropping an invalid one leaves no double space.
_MARKER = re.compile(r"(\s*)\[\s*\d+(?:\s*[,;]\s*\d+)*\s*\]")
_MAX_DIGITS = 4  # int() refuses over 4300 digits; no context has 10 000 hits

RetrieveFn = Callable[[str, User, int, RetrievalMode], list[Hit]]


def retrieval_mode() -> RetrievalMode:
    """``RETRIEVAL_MODE`` from the environment; blank or unset is ``hybrid_rerank``."""
    raw = os.getenv("RETRIEVAL_MODE", "").strip()
    if not raw:
        return DEFAULT_MODE
    if raw not in get_args(RetrievalMode):
        raise ValueError(f"RETRIEVAL_MODE must be one of {', '.join(get_args(RetrievalMode))}, got {raw!r}")
    return raw  # type: ignore[return-value]


def _default_retrieve(question: str, user: User, k: int, mode: RetrievalMode) -> list[Hit]:
    from app.rag.retrieve import retrieve

    return retrieve(question, user, k, mode)


class RagAnswerer:
    def __init__(self, retrieve: RetrieveFn | None = None, llm: LLM | None = None, k: int = DEFAULT_K) -> None:
        if llm is None:
            from app import llm as gateway

            llm = gateway
        self._retrieve = retrieve or _default_retrieve
        self._llm = llm
        self.k = k

    def answer(self, question: str, user: User, mode: RetrievalMode | None = None) -> AskResult:
        started = time.monotonic()
        mode = mode or retrieval_mode()
        hits = self._retrieve(question, user, self.k, mode)
        text, citations = REFUSAL, []
        if hits:
            messages = [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_message(question, hits)},
            ]
            text, citations = cite(self._llm.chat(messages, ALIAS, temperature=0.0).text, hits)
        latency_ms = round((time.monotonic() - started) * 1000)
        return AskResult(text, bool(citations), citations, mode, "cloud", latency_ms)


def _leaks_canary(text: str) -> bool:
    """Whether ``text`` holds CANARY, ignoring case, whitespace and citation markers split into it."""
    return CANARY.lower() in re.sub(r"\s+", "", _MARKER.sub("", text)).lower()


def cite(reply: str, hits: list[Hit]) -> tuple[str, list[Citation]]:
    """Map ``[n]`` markers in ``reply`` to citations; ``(REFUSAL, [])`` when nothing valid is cited."""
    cited: set[int] = set()

    def keep_valid(match: re.Match[str]) -> str:
        digits = (d.lstrip("0") or "0" for d in re.findall(r"\d+", match.group()))
        numbers = (int(d) for d in digits if len(d) <= _MAX_DIGITS)
        valid = [n for n in dict.fromkeys(numbers) if 1 <= n <= len(hits)]
        cited.update(valid)
        return match.group(1) + "".join(f"[{n}]" for n in valid) if valid else ""

    text = _MARKER.sub(keep_valid, reply).strip()
    # A refusal that still cites a passage is a refusal: the contract pairs found=false with REFUSAL.
    # The canary is checked on the final text, after invalid markers are dropped (PR #62 review).
    if not cited or text.startswith(REFUSAL.rstrip(".")) or _leaks_canary(text):
        return REFUSAL, []
    return text, [Citation(n, hits[n - 1].source, hits[n - 1].page, hits[n - 1].score) for n in sorted(cited)]
