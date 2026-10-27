"""Parse PDFs with parse_docling and write one Markdown file per PDF for eyeballing.

Usage: PYTHONPATH=src .venv/bin/python scripts/parse_preview.py [file.pdf ...]
Default: every data/*.pdf. Output: data/parsed/<name>.md (git-ignored).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from app.rag.parse_docling import parse


def main(args: list[str]) -> int:
    out_dir = Path("data/parsed")
    out_dir.mkdir(parents=True, exist_ok=True)
    files = [Path(a) for a in args] or sorted(Path("data").glob("*.pdf"))
    failed = 0
    for f in files:
        start = time.time()
        try:
            pages = parse(str(f))
        except Exception as e:  # report and keep going: one bad PDF must not stop the batch
            print(f"LỖI  {f.name}: {e}", flush=True)
            failed += 1
            continue
        md = [f"# {f.name}\n"]
        for p in pages:
            md.append(f"\n---\n## Trang {p['page']}\n\n{p['text']}\n")
            md += [f"\n{table}\n" for table in p["tables"]]
        (out_dir / f"{f.stem}.md").write_text("".join(md), encoding="utf-8")
        tables = sum(len(p["tables"]) for p in pages)
        empty = sum(1 for p in pages if not p["text"] and not p["tables"])
        print(
            f"OK   {f.name}: {len(pages)} trang, {tables} bảng, {empty} trang rỗng, {time.time() - start:.0f}s",
            flush=True,
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
