"""X-API-Key (hashed) -> User; role checks.

Owner: B — Epic E-006. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path

from fastapi import Depends, Header, HTTPException

from app.config import get_settings
from app.contracts import User


def load_api_keys(path: Path) -> dict[str, User]:
    """Read a digest -> identity map; reject malformed registries as a whole."""
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, dict):
        raise ValueError("Invalid API key registry")
    users = {}
    for digest, record in records.items():
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or not isinstance(record, dict):
            raise ValueError("Invalid API key record")
        if (
            set(record) != {"user_id", "department", "role"}
            or not isinstance(record["user_id"], str)
            or not record["user_id"].strip()
            or record["department"] not in ("public", "credit", "hr")
            or record["role"] not in ("staff", "approver", "service")
        ):
            raise ValueError("Invalid API key identity")
        users[digest] = User(**record)
    return users


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
