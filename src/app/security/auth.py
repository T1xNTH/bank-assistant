"""X-API-Key (hashed) -> User; role checks.

Owner: B — Epic E-006. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

from fastapi import Depends, Header, HTTPException

from app.config import get_settings
from app.contracts import User
from app.security.keys import load_api_keys


def get_current_user(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> User:
    settings = get_settings()
    if settings.auth_backend == "fake":
        return User(user_id="dev", department="public")
    if settings.auth_backend != "apikey":
        raise HTTPException(status_code=503, detail="Authentication unavailable")
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        users = load_api_keys(Path(settings.api_keys_file))
    except (OSError, ValueError):
        raise HTTPException(status_code=503, detail="Authentication unavailable") from None
    user = users.get(hashlib.sha256(x_api_key.encode("utf-8")).hexdigest())
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def require_role(role: str) -> Callable[..., User]:
    """Return a dependency that authenticates and requires an exact role."""
    def check_role(user: User = Depends(get_current_user)) -> User:
        if user.role != role:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return check_role
