"""System prompt, context builder, canary and prompt version.

Owner: A — Epic E-004. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

SYSTEM = ""  # TODO E-004
CANARY = ""  # TODO E-004 (security canary, see docs/06-security)
PROMPT_VERSION = "0"


def build_context(hits: list) -> str:
    raise NotImplementedError("E-004")
