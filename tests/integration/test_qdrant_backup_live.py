"""Opt-in recovery drill; only deletes its randomly named synthetic collection."""

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import httpx2 as httpx
import pytest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


def test_snapshot_survives_collection_deletion(tmp_path):
    if os.getenv("QDRANT_BACKUP_LIVE") != "1":
        pytest.skip("Set QDRANT_BACKUP_LIVE=1 with local Qdrant running")
    collection = f"t040-drill-{uuid4().hex}"
    url = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
    command = [
        sys.executable, str(ROOT / "scripts/qdrant_backup.py"),
        "backup", "--url", url, "--collection", collection, "--backup-dir", str(tmp_path),
    ]
    with httpx.Client(base_url=url, timeout=60, trust_env=False) as client:
        response = client.put(f"/collections/{collection}", json={"vectors": {"size": 2, "distance": "Cosine"}})
        response.raise_for_status()
        try:
            points = [{"id": n, "vector": [1.0, 0.0], "payload": {"synthetic": n}} for n in range(1, 4)]
            response = client.put(f"/collections/{collection}/points?wait=true", json={"points": points})
            response.raise_for_status()
            subprocess.run(command, check=True, timeout=330)
            response = client.delete(f"/collections/{collection}")
            response.raise_for_status()
            command[2] = "restore"
            subprocess.run(command, check=True, timeout=330)
            response = client.post(
                f"/collections/{collection}/points/scroll",
                json={"limit": 10, "with_payload": True, "with_vector": True},
            )
            response.raise_for_status()
            assert response.json()["result"]["points"] == points
        finally:
            client.delete(f"/collections/{collection}").raise_for_status()
