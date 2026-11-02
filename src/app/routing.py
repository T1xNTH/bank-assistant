"""Decide cloud vs local model from PII types and chunk classification.

Policy (docs/06-security/security-design.md, "Routing nhạy cảm"): the question had PII, a retrieved
chunk is ``confidential``, or the caller asked for ``force_local`` -> ``local-chat``. Otherwise every
chunk is ``public`` or ``internal`` and the question had no PII -> ``cloud-chat``. A classification
outside ``public``/``internal`` (unknown or misspelled label) fails closed to local.

Owner: A — Epic E-010. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.contracts import Route

LOCAL_ALIAS = "local-chat"
CLOUD_ALIAS = "cloud-chat"
CLOUD_CLASSIFICATIONS = frozenset({"public", "internal"})


@dataclass(frozen=True)
class RouteDecision:
    route: Route
    alias: str
    reason: str


def decide_route(pii_types: Iterable[str], classifications: Iterable[str], force_local: bool = False) -> RouteDecision:
    pii = sorted(set(pii_types))
    sensitive = sorted(set(classifications) - CLOUD_CLASSIFICATIONS)
    reasons = []
    if force_local:
        reasons.append("force_local")
    if pii:
        reasons.append(f"pii:{','.join(pii)}")
    if sensitive:
        reasons.append(f"classification:{','.join(sensitive) or 'empty'}")
    if reasons:
        return RouteDecision("local", LOCAL_ALIAS, "; ".join(reasons))
    return RouteDecision("cloud", CLOUD_ALIAS, "no pii, chunks public/internal")
