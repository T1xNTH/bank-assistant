#!/usr/bin/env python3
"""Back up one quiesced Qdrant collection; restore only into an absent collection."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import httpx2 as httpx


def count(client, collection):
    response = client.post(f"/collections/{quote(collection, safe='')}/points/count", json={"exact": True})
    response.raise_for_status()
    return response.json()["result"]["count"]


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def backup(client, collection, directory):
    directory.mkdir(parents=True, exist_ok=True)
    base = f"/collections/{quote(collection, safe='')}/snapshots"
    before = count(client, collection)
    response = client.post(base, params={"wait": "true"})
    response.raise_for_status()
    remote = response.json()["result"]["name"]
    snapshot = directory / f"{uuid4().hex}.snapshot"
    temporary = snapshot.with_suffix(".partial")
    try:
        with client.stream("GET", f"{base}/{quote(remote, safe='')}") as download:
            download.raise_for_status()
            with temporary.open("xb") as target:
                for chunk in download.iter_bytes():
                    target.write(chunk)
        if count(client, collection) != before:
            raise ValueError("Collection changed during backup; stop writers and retry")
        temporary.replace(snapshot)
        manifest = {
            "version": 1, "collection": collection, "points_count": before,
            "snapshot": snapshot.name, "sha256": digest(snapshot),
        }
        pending = directory / f"{uuid4().hex}.json.partial"
        try:
            pending.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            pending.replace(directory / "backup.json")
        finally:
            pending.unlink(missing_ok=True)
    finally:
        temporary.unlink(missing_ok=True)
        try:
            response = client.delete(f"{base}/{quote(remote, safe='')}")
            response.raise_for_status()
        except httpx.HTTPError:
            print("Warning: snapshot cleanup failed; snapshot may remain on the server", file=sys.stderr)
    return before


def restore(client, collection, directory):
    manifest = json.loads((directory / "backup.json").read_text(encoding="utf-8"))
    if manifest.get("version") != 1 or manifest.get("collection") != collection:
        raise ValueError("Backup version or collection does not match")
    name = manifest["snapshot"]
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(".snapshot"):
        raise ValueError("Invalid snapshot filename")
    snapshot = directory / name
    if snapshot.is_symlink() or digest(snapshot) != manifest["sha256"]:
        raise ValueError("Snapshot checksum does not match")
    expected = manifest["points_count"]
    if type(expected) is not int or expected < 0:
        raise ValueError("Invalid point count")
    base = f"/collections/{quote(collection, safe='')}"
    response = client.get(base)
    if response.status_code != 404:
        response.raise_for_status()
        raise ValueError("Collection already exists; restore to an empty Qdrant instance")
    with snapshot.open("rb") as source:
        response = client.post(
            f"{base}/snapshots/upload", params={"priority": "snapshot", "wait": "true"},
            files={"snapshot": (snapshot.name, source, "application/octet-stream")},
        )
    response.raise_for_status()
    actual = count(client, collection)
    if actual != expected:
        raise ValueError(f"Restored count mismatch: expected {expected}, got {actual}")
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore"])
    parser.add_argument("--url", default=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"))
    parser.add_argument("--collection", default=os.getenv("QDRANT_COLLECTION", "bank_docs"))
    parser.add_argument("--backup-dir", type=Path, default=Path("data/backups/qdrant"))
    args = parser.parse_args()
    headers = {"api-key": os.environ["QDRANT_API_KEY"]} if os.getenv("QDRANT_API_KEY") else {}
    try:
        with httpx.Client(base_url=args.url.rstrip("/"), headers=headers, timeout=300, trust_env=False) as client:
            action = backup if args.action == "backup" else restore
            points = action(client, args.collection, args.backup_dir)
        print(f"{args.action}: verified {points} points (backup.json)")
    except (httpx.HTTPError, OSError, ValueError, KeyError, TypeError):
        print(f"{args.action} failed; check Qdrant availability, collection and backup integrity", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
