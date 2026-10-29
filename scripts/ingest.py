"""Index the corpus into Qdrant: parse -> chunk -> embed -> replace each document's points.

Usage: python scripts/ingest.py [--data data] [--collection bank_docs] [--only DOC_ID ...] [--no-cache]

Reads ``<data>/manifest.csv`` (checked with scripts/check_manifest.py first), then for each row
parses the PDF, chunks it, embeds the chunks with bge-m3 and makes them the complete set of
points for that ``doc_id`` (re-running converges; a re-chunk leaves no stale points). Parse and
embedding results are cached per document under ``<data>/cache`` (git-ignored) and reused while
the PDF, the parser code and the chunk texts are unchanged: parsing the 30 PDFs takes ~1 h.
A failing document is reported and skipped; the exit code is 1 if any document failed.

Owner: A — Epic E-003. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):  # runnable as a plain script, not only under pytest/PYTHONPATH
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault("TQDM_DISABLE", "1")  # docling and FlagEmbedding progress bars drown the summary

PARSER_SOURCE = ROOT / "src/app/rag/parse_docling.py"
META_FIELDS = ("department", "classification", "effective_date", "superseded_by")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=Path("data"), help="thư mục chứa manifest.csv và các PDF")
    parser.add_argument("--collection", default=None, help="mặc định QDRANT_COLLECTION hoặc bank_docs")
    parser.add_argument("--only", nargs="+", metavar="DOC_ID", help="chỉ ingest các doc_id này")
    parser.add_argument("--no-cache", action="store_true", help="parse và embed lại, bỏ qua cache")
    args = parser.parse_args(argv)
    try:  # Windows writes cp1252 to a redirected stdout; the progress lines are Vietnamese
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    from qdrant_client import QdrantClient

    from app.rag.store import COLLECTION
    from scripts.check_manifest import check

    manifest = args.data / "manifest.csv"
    errors = check(manifest, expect=None)
    if errors:
        for e in errors:
            print(f"LỖI  manifest: {e}")
        return 1
    rows = _rows(manifest)
    if args.only:
        unknown = sorted(set(args.only) - {r["doc_id"] for r in rows})
        if unknown:
            print(f"LỖI  không có trong manifest: {', '.join(unknown)}")
            return 1
        rows = [r for r in rows if r["doc_id"] in args.only]

    collection = args.collection or os.getenv("QDRANT_COLLECTION", COLLECTION)
    cache = None if args.no_cache else args.data / "cache"
    client = QdrantClient(
        url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"), api_key=os.getenv("QDRANT_API_KEY") or None, timeout=60
    )
    try:
        return _run(rows, args.data, collection, cache, client)
    finally:
        client.close()


def _run(rows: list[dict], data: Path, collection: str, cache: Path | None, client) -> int:
    start, pages, chunks, failed = time.time(), 0, 0, []
    for n, row in enumerate(rows, start=1):
        began = time.time()
        try:
            stats = ingest_document(row, data, collection, cache, client)
        except Exception as e:  # report and keep going: one bad PDF must not stop the batch
            print(f"[{n}/{len(rows)}] LỖI  {row['doc_id']}: {type(e).__name__}: {e}", flush=True)
            failed.append(row["doc_id"])
            continue
        pages, chunks = pages + stats["pages"], chunks + stats["chunks"]
        print(
            f"[{n}/{len(rows)}] OK   {row['doc_id']}: {stats['pages']} trang, {stats['chunks']} chunk"
            f" ({stats['cached']}), {time.time() - began:.0f}s",
            flush=True,
        )
    # Every document may have failed before the collection was created.
    total = client.count(collection, exact=True).count if client.collection_exists(collection) else 0
    print(
        f"{'FAIL' if failed else 'OK'}  {len(rows) - len(failed)}/{len(rows)} tài liệu, {pages} trang,"
        f" {chunks} chunk; collection {collection}: {total} point; {(time.time() - start) / 60:.1f} phút"
    )
    if failed:
        print(f"LỖI  {', '.join(failed)}")
    return 1 if failed else 0


def ingest_document(row: dict, data: Path, collection: str, cache: Path | None, client) -> dict:
    """Parse, chunk, embed and store one manifest row; return counts and which steps hit the cache."""
    from app.rag.chunk import chunk_pages
    from app.rag.store import replace_document

    pdf = data / row["file"]
    pages, parse_hit = _parsed(pdf, row["doc_id"], cache)
    pages = [{**p, "source": pdf.name} for p in pages]  # cached pages keep the name the file had when parsed
    chunks = chunk_pages(pages)
    dense, sparse, embed_hit = _embedded([c["text"] for c in chunks], row["doc_id"], cache)
    meta = {k: row[k] for k in META_FIELDS} | {"doc_id": row["doc_id"]}
    points = [c | meta | {"dense": d, "sparse": s} for c, d, s in zip(chunks, dense, sparse, strict=True)]
    replace_document(row["doc_id"], points, client=client, collection=collection)
    hits = [name for name, hit in (("parse", parse_hit), ("embed", embed_hit)) if hit]
    return {"pages": len(pages), "chunks": len(points), "cached": "cache: " + "+".join(hits) if hits else "mới"}


def _parsed(pdf: Path, doc_id: str, cache: Path | None) -> tuple[list[dict], bool]:
    key = _digest(_sha256(pdf), _parser_version())
    cached = _load(cache, "parsed", doc_id, key)
    if cached is not None:
        return cached, True
    from app.rag.parse_docling import parse

    pages = parse(str(pdf))
    _save(cache, "parsed", doc_id, key, pages)
    return pages, False


def _embedded(texts: list[str], doc_id: str, cache: Path | None) -> tuple[list, list, bool]:
    from app.rag import embed

    key = _digest(embed.MODEL, str(embed.MAX_LENGTH), json.dumps(texts, ensure_ascii=False))
    cached = _load(cache, "embedded", doc_id, key)
    if cached is not None:
        return cached["dense"], cached["sparse"], True
    dense, sparse = embed.embed(texts)
    _save(cache, "embedded", doc_id, key, {"dense": dense, "sparse": sparse})
    return dense, sparse, False


def _parser_version() -> str:
    from importlib.metadata import version

    return _digest(PARSER_SOURCE.read_text(encoding="utf-8"), version("docling"))


def _load(cache: Path | None, kind: str, doc_id: str, key: str):
    file = cache / kind / f"{doc_id}.json" if cache else None
    if file is None or not file.is_file():
        return None
    try:
        stored = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None  # a corrupt cache entry is recomputed, not trusted
    if not isinstance(stored, dict) or "value" not in stored:
        return None
    return stored["value"] if stored.get("key") == key else None


def _save(cache: Path | None, kind: str, doc_id: str, key: str, value) -> None:
    if cache is None:
        return
    file = cache / kind / f"{doc_id}.json"
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp = file.with_suffix(".tmp")
    tmp.write_text(json.dumps({"key": key, "value": value}, ensure_ascii=False), encoding="utf-8")
    tmp.replace(file)  # atomic: an interrupted run never leaves a half-written entry


def _rows(manifest: Path) -> list[dict]:
    with manifest.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _digest(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
