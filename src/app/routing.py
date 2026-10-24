"""Decide cloud vs local model from PII types and chunk classification.

Owner: A — Epic E-010. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.contracts import Route


@dataclass(frozen=True)
class RouteDecision:
    route: Route
    alias: str
    reason: str


def decide_route(pii_types: list[str], classifications: list[str], force_local: bool = False) -> RouteDecision:
    raise NotImplementedError("E-010")
