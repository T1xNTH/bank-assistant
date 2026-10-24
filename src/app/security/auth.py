"""X-API-Key (hashed) -> User; role checks.

Owner: B — Epic E-006. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

from app.contracts import User


def get_current_user() -> User:
    raise NotImplementedError("E-006")
