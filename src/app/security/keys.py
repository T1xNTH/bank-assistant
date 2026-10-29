"""Shared registry validation for provisioning and authentication."""

from __future__ import annotations

import json
import re
from pathlib import Path

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
