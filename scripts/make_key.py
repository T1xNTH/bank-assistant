"""Generate a key once on stdout; persist only its SHA-256 digest and identity."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--department", choices=("public", "credit", "hr"), required=True)
    parser.add_argument("--role", choices=("staff", "approver", "service"), default="staff")
    parser.add_argument("--file", type=Path, default=Path(os.getenv("API_KEYS_FILE", "config/api_keys.json")))
    args = parser.parse_args()
    if not args.user_id.strip():
        parser.error("user-id must not be blank")
    try:
        records = json.loads(args.file.read_text(encoding="utf-8")) if args.file.exists() else {}
        if not isinstance(records, dict):
            raise ValueError
    except (OSError, ValueError):
        parser.error("Cannot read API key registry")
    key = secrets.token_urlsafe(32)
    records[hashlib.sha256(key.encode()).hexdigest()] = {
        "user_id": args.user_id, "department": args.department, "role": args.role,
    }
    args.file.parent.mkdir(parents=True, exist_ok=True)
    # Same-directory replacement prevents readers from seeing a partial JSON file.
    fd, name = tempfile.mkstemp(dir=args.file.parent, prefix=".api-keys-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(records, stream, indent=2)
            stream.write("\n")
        os.replace(name, args.file)
    finally:
        Path(name).unlink(missing_ok=True)
    print(key)


if __name__ == "__main__":
    main()
