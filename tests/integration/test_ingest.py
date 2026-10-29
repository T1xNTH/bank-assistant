"""scripts/ingest.py end to end: real docling, bge-m3 and Qdrant 1.12.x on generated PDFs."""

import csv
import os
import random
from uuid import uuid4

import pytest
from qdrant_client import QdrantClient

from scripts import ingest
from scripts.check_manifest import COLUMNS
from tests.pdf_fixtures import write_fee_table_pdf

pytestmark = pytest.mark.integration

SCHEMA_FIELDS = {
    "doc_id", "source", "page", "chunk_index", "text",
    "department", "classification", "effective_date", "superseded_by",
}  # docs/05-database/schema.md


@pytest.fixture
def qdrant(monkeypatch):
    url = os.getenv("QDRANT_TEST_URL", "http://127.0.0.1:6333")
    name = "test_bank_docs_" + uuid4().hex
    connection = QdrantClient(url=url, timeout=10)
    connection.get_collections()  # an unavailable service fails rather than silently skipping
    monkeypatch.setenv("QDRANT_URL", url)
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    try:
        yield connection, name
    finally:
        if connection.collection_exists(name):
            connection.delete_collection(name)
        connection.close()


def test_ingest_indexes_real_pdfs_with_full_payloads(tmp_path, qdrant):
    connection, name = qdrant
    rows = [
        ("fee-old", "fee-old.pdf", "public", "public", "2024-01-01", "fee-new"),
        ("fee-new", "fee-new.pdf", "credit", "public", "2026-01-01", ""),
        ("hr-fee", "hr-fee.pdf", "hr", "internal", "2026-01-01", ""),
    ]
    with (tmp_path / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(COLUMNS)
        writer.writerows(r + (f"https://example.vn/{r[1]}",) for r in rows)
    for row in rows:
        write_fee_table_pdf(tmp_path / row[1])

    assert ingest.main(["--data", str(tmp_path), "--collection", name]) == 0

    points, _ = connection.scroll(name, limit=1000, with_payload=True, with_vectors=True)
    assert {p.payload["doc_id"] for p in points} == {"fee-old", "fee-new", "hr-fee"}
    for point in random.Random(0).sample(points, min(5, len(points))):
        assert set(point.payload) == SCHEMA_FIELDS
        assert point.payload["text"].strip() and point.payload["page"] == 1
        assert len(point.vector["dense"]) == 1024 and point.vector["sparse"].indices
    assert any("| " in p.payload["text"] for p in points)  # the fee table is stored as Markdown
    assert {p.payload["superseded_by"] for p in points if p.payload["doc_id"] == "fee-old"} == {"fee-new"}

    # A second run is served from the cache and converges to the same points.
    assert ingest.main(["--data", str(tmp_path), "--collection", name]) == 0
    assert connection.count(name, exact=True).count == len(points)
