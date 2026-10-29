"""scripts/ingest.py with a fake parser and embedder and an in-memory Qdrant."""

import csv
import json
from pathlib import Path

import pytest
import qdrant_client
from qdrant_client import QdrantClient

from app.rag import chunk as chunking
from app.rag import embed as emb
from app.rag import parse_docling
from scripts import ingest
from scripts.check_manifest import COLUMNS

pytestmark = pytest.mark.filterwarnings("ignore:Payload indexes have no effect in the local Qdrant")

COLLECTION = "test_bank_docs"
# check_manifest needs every department and one replacement already in force.
ROWS = [
    ("fee-2025", "fee.pdf", "public", "public", "2025-01-01", "", "https://example.vn/fee.pdf"),
    ("loan-old", "loan-old.pdf", "credit", "public", "2021-02-15", "loan-new", "https://example.vn/loan-old.pdf"),
    ("loan-new", "loan-new.pdf", "credit", "public", "2026-01-01", "", "https://example.vn/loan-new.pdf"),
    ("wage-2026", "wage.pdf", "hr", "internal", "2026-01-01", "", "https://example.vn/wage.pdf"),
]
TEXT = "Phí rút tiền mặt tại ATM là 4%, tối thiểu 80.000 đồng. " * 30  # ~1700 chars: 3 chunks


@pytest.fixture
def corpus(tmp_path):
    with (tmp_path / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(COLUMNS)
        writer.writerows(ROWS)
    for row in ROWS:
        (tmp_path / row[1]).write_bytes(b"%PDF-1.7\n" + row[0].encode())
    return tmp_path


@pytest.fixture
def calls(monkeypatch):
    seen = {"parse": [], "embed": 0}

    def parse(path):
        seen["parse"].append(path)
        name = Path(path).name  # not "/": Windows paths use backslashes
        return [
            {"source": name, "page": 1, "text": TEXT, "tables": []},
            {"source": name, "page": 2, "text": "", "tables": ["| Vùng | Mức |\n|---|---|\n| I | 5.310.000 |"]},
        ]

    def embed(texts):
        seen["embed"] += 1
        return [[1.0] + [0.0] * (emb.DIM - 1) for _ in texts], [{"indices": [7], "values": [0.5]} for _ in texts]

    monkeypatch.setattr(parse_docling, "parse", parse)
    monkeypatch.setattr(emb, "embed", embed)
    return seen


@pytest.fixture
def client(monkeypatch):
    connection = QdrantClient(":memory:")
    monkeypatch.setattr(qdrant_client, "QdrantClient", lambda **kwargs: connection)
    monkeypatch.setattr(connection, "close", lambda: None)  # main() closes its client; keep the data to inspect
    yield connection


def payloads(client):
    points, _ = client.scroll(COLLECTION, limit=1000, with_payload=True)
    return [p.payload for p in points]


def test_every_document_is_indexed_with_the_schema_payload(corpus, calls, client, capsys):
    assert ingest.main(["--data", str(corpus), "--collection", COLLECTION]) == 0

    stored = payloads(client)
    assert len(stored) == 4 * 4  # 4 documents x (3 text chunks + 1 table chunk)
    assert set(stored[0]) == {
        "doc_id", "source", "page", "chunk_index", "text",
        "department", "classification", "effective_date", "superseded_by",
    }
    by_doc = {p["doc_id"]: p for p in stored}
    assert by_doc["loan-old"]["superseded_by"] == "loan-new"
    assert by_doc["fee-2025"]["superseded_by"] is None  # empty CSV cell, not ""
    assert (by_doc["wage-2026"]["department"], by_doc["wage-2026"]["classification"]) == ("hr", "internal")
    assert by_doc["wage-2026"]["source"] == "wage.pdf"
    assert sorted(p["chunk_index"] for p in stored if p["doc_id"] == "fee-2025") == [0, 1, 2, 3]
    assert "OK  4/4 tài liệu, 8 trang, 16 chunk; collection test_bank_docs: 16 point" in capsys.readouterr().out


def test_second_run_reuses_the_cache_and_converges(corpus, calls, client):
    ingest.main(["--data", str(corpus), "--collection", COLLECTION])
    ingest.main(["--data", str(corpus), "--collection", COLLECTION])

    assert len(calls["parse"]) == 4 and calls["embed"] == 4  # nothing recomputed on the second run
    assert len(payloads(client)) == 16


def test_a_changed_pdf_is_parsed_again(corpus, calls, client):
    ingest.main(["--data", str(corpus), "--collection", COLLECTION])
    (corpus / "fee.pdf").write_bytes(b"%PDF-1.7\nnew edition")

    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"])

    assert len(calls["parse"]) == 5 and Path(calls["parse"][-1]).name == "fee.pdf"
    assert calls["embed"] == 4  # same chunk texts: the embedding cache still applies


def test_no_cache_recomputes(corpus, calls, client):
    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"])
    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025", "--no-cache"])

    assert len(calls["parse"]) == 2 and calls["embed"] == 2


def test_a_failing_document_is_reported_and_the_rest_are_indexed(corpus, calls, client, monkeypatch, capsys):
    real = parse_docling.parse

    def parse(path):
        if Path(path).name == "loan-new.pdf":
            raise parse_docling.ParseError("loan-new.pdf: no parse result for pages [2]")
        return real(path)

    monkeypatch.setattr(parse_docling, "parse", parse)

    assert ingest.main(["--data", str(corpus), "--collection", COLLECTION]) == 1

    out = capsys.readouterr().out
    assert "LỖI  loan-new: ParseError" in out and "FAIL  3/4 tài liệu" in out
    assert {p["doc_id"] for p in payloads(client)} == {"fee-2025", "loan-old", "wage-2026"}


def test_reingesting_fewer_chunks_leaves_no_stale_points(corpus, calls, client, monkeypatch):
    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"])
    short = [{"source": "fee.pdf", "page": 1, "text": "Ngắn.", "tables": []}]
    monkeypatch.setattr(parse_docling, "parse", lambda path: short)

    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025", "--no-cache"])

    assert [p["text"] for p in payloads(client)] == ["Ngắn."]


def test_invalid_manifest_stops_before_any_work(corpus, calls, client, capsys):
    (corpus / "wage.pdf").unlink()

    assert ingest.main(["--data", str(corpus), "--collection", COLLECTION]) == 1

    assert "LỖI  manifest:" in capsys.readouterr().out
    assert calls["parse"] == [] and not client.collection_exists(COLLECTION)


def test_unknown_only_doc_id_is_an_error(corpus, calls, client, capsys):
    assert ingest.main(["--data", str(corpus), "--only", "ghost"]) == 1
    assert "ghost" in capsys.readouterr().out and calls["parse"] == []


@pytest.mark.parametrize("content", ["{not json", "[]", "key without value"])
def test_corrupt_cache_entry_is_recomputed(corpus, calls, client, content):
    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"])
    entry = corpus / "cache/parsed/fee-2025.json"
    if content == "key without value":  # the right key, so only the shape check makes it a miss
        content = json.dumps({"key": json.loads(entry.read_text(encoding="utf-8"))["key"]})
    entry.write_text(content, encoding="utf-8")

    assert ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"]) == 0
    assert len(calls["parse"]) == 2


def test_changed_chunk_texts_are_embedded_again_with_the_cache_on(corpus, calls, client, monkeypatch):
    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"])
    # The parse cache still applies; only a different chunker (as CR-009) changes the texts.
    real = chunking.chunk_pages
    renamed = lambda pages: [{**c, "text": "Mới: " + c["text"]} for c in real(pages)]  # noqa: E731
    monkeypatch.setattr(chunking, "chunk_pages", renamed)

    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"])

    assert len(calls["parse"]) == 1 and calls["embed"] == 2
    assert all(p["text"].startswith("Mới: ") for p in payloads(client))


def test_a_parser_change_parses_again(corpus, calls, client, monkeypatch):
    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"])
    monkeypatch.setattr(ingest, "_parser_version", lambda: "another parser")

    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"])

    assert len(calls["parse"]) == 2


def test_a_renamed_file_is_cited_by_its_new_name(corpus, calls, client):
    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"])
    (corpus / "fee.pdf").rename(corpus / "bieu-phi.pdf")
    manifest = (corpus / "manifest.csv").read_text(encoding="utf-8").replace(",fee.pdf,", ",bieu-phi.pdf,")
    (corpus / "manifest.csv").write_text(manifest, encoding="utf-8")

    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"])

    assert len(calls["parse"]) == 1  # same bytes: served from the cache
    assert {p["source"] for p in payloads(client)} == {"bieu-phi.pdf"}


def test_summary_is_printed_when_every_document_fails(corpus, calls, client, monkeypatch, capsys):
    monkeypatch.setattr(parse_docling, "parse", lambda path: (_ for _ in ()).throw(RuntimeError("boom")))

    assert ingest.main(["--data", str(corpus), "--collection", COLLECTION]) == 1

    out = capsys.readouterr().out
    assert "FAIL  0/4 tài liệu" in out and "0 point" in out


def _replace_cached_value(entry, value):
    stored = json.loads(entry.read_text(encoding="utf-8"))
    entry.write_text(json.dumps({"key": stored["key"], "value": value}), encoding="utf-8")


@pytest.mark.parametrize(
    "value",
    [
        [],  # PR47-F01: an empty parse would replace the document with no points
        {"page": 1},
        [{"source": "fee.pdf", "page": 1, "text": "x"}],  # no tables
        [{"source": "fee.pdf", "page": "1", "text": "x", "tables": []}],
        [{"source": "fee.pdf", "page": 1, "text": "x", "tables": [None]}],
        [{"source": "fee.pdf", "page": 1, "text": "x", "tables": []}] * 2,  # duplicate page
    ],
)
def test_malformed_cached_pages_are_parsed_again(corpus, calls, client, value):
    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"])
    _replace_cached_value(corpus / "cache/parsed/fee-2025.json", value)

    assert ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"]) == 0

    assert len(calls["parse"]) == 2
    assert len(payloads(client)) == 4  # the indexed document is kept, not emptied


@pytest.mark.parametrize(
    "value",
    [
        {"dense": [], "sparse": []},  # PR47-F01: fewer vectors than chunks
        {"dense": [[1.0] * 3] * 4, "sparse": [{"indices": [7], "values": [0.5]}] * 4},  # wrong dimension
        {"dense": [[1.0] * 1024] * 4, "sparse": [{"indices": [7]}] * 4},
        {"dense": [[1.0] * 1024] * 4, "sparse": [{"indices": [7, 8], "values": [0.5]}] * 4},
        {"dense": [[1.0] * 1024] * 4},
        [[1.0] * 1024] * 4,
    ],
)
def test_malformed_cached_embeddings_are_embedded_again(corpus, calls, client, value):
    ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"])
    _replace_cached_value(corpus / "cache/embedded/fee-2025.json", value)

    assert ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"]) == 0
    assert ingest.main(["--data", str(corpus), "--collection", COLLECTION, "--only", "fee-2025"]) == 0

    assert calls["embed"] == 2  # recomputed once, then the repaired entry is a hit
    assert len(payloads(client)) == 4
