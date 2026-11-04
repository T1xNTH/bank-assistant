#!/usr/bin/env python3
"""Verify Make snapshot recovery using only a disposable synthetic collection."""

import os
import subprocess
import sys
import tempfile
from uuid import uuid4

import httpx2 as httpx


def main():
    collection = f"t040-smoke-{uuid4().hex}"
    url = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
    with tempfile.TemporaryDirectory() as directory, httpx.Client(base_url=url, timeout=60, trust_env=False) as client:
        base = f"/collections/{collection}"
        client.put(base, json={"vectors": {"size": 2, "distance": "Cosine"}}).raise_for_status()
        try:
            points = [{"id": n, "vector": [1.0, 0.0], "payload": {"synthetic": n}} for n in range(1, 8)]
            client.put(f"{base}/points?wait=true", json={"points": points}).raise_for_status()
            settings = [
                f"PY={sys.executable}", f"QDRANT_URL={url}",
                f"QDRANT_COLLECTION={collection}", f"BACKUP_DIR={directory}",
            ]
            subprocess.run(["make", "backup", *settings], check=True, timeout=330)
            client.delete(base).raise_for_status()
            subprocess.run(["make", "restore", *settings], check=True, timeout=330)
            response = client.post(
                f"{base}/points/scroll", json={"limit": 10, "with_payload": True, "with_vector": True},
            )
            response.raise_for_status()
            if response.json()["result"]["points"] != points:
                raise RuntimeError("Restored points, vectors or payloads differ")
            print("MAKE_RECOVERY_PASS: 7 points, vectors and payloads match")
        finally:
            client.delete(base).raise_for_status()


if __name__ == "__main__":
    main()
