"""Check data/manifest.csv against T-005 and docs/05-database/schema.md.

Usage: python scripts/check_manifest.py [--manifest data/manifest.csv] [--expect 30]
Prints every problem found and exits 1 if there is any, 0 otherwise. Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

COLUMNS = ["doc_id", "file", "department", "classification", "effective_date", "superseded_by", "source_url"]
DEPARTMENTS = {"public", "credit", "hr"}
CLASSIFICATIONS = {"public", "internal", "confidential"}
DOC_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def check(manifest: Path, expect: int | None = 30) -> list[str]:
    if not manifest.is_file():
        return [f"{manifest}: không tìm thấy file"]
    with manifest.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != COLUMNS:
            return [f"header phải là {','.join(COLUMNS)}, đang là {','.join(reader.fieldnames or [])}"]
        rows = list(reader)

    errors: list[str] = []
    if expect is not None and len(rows) != expect:
        errors.append(f"cần {expect} dòng, đang có {len(rows)}")

    ids = [r["doc_id"] for r in rows]
    for n, r in enumerate(rows, start=2):  # line 1 is the header
        where = f"dòng {n} ({r['doc_id'] or '?'})"
        if not DOC_ID.match(r["doc_id"]):
            errors.append(f"{where}: doc_id phải gồm chữ thường, số, dấu '-'")
        elif ids.count(r["doc_id"]) > 1:
            errors.append(f"{where}: doc_id bị trùng")
        if not r["file"].lower().endswith(".pdf"):
            errors.append(f"{where}: file phải là .pdf")
        elif not (manifest.parent / r["file"]).is_file():
            errors.append(f"{where}: không có file {manifest.parent / r['file']}")
        if r["department"] not in DEPARTMENTS:
            errors.append(f"{where}: department phải thuộc {sorted(DEPARTMENTS)}")
        if r["classification"] not in CLASSIFICATIONS:
            errors.append(f"{where}: classification phải thuộc {sorted(CLASSIFICATIONS)}")
        try:
            date.fromisoformat(r["effective_date"])
        except ValueError:
            errors.append(f"{where}: effective_date phải là ngày ISO YYYY-MM-DD, đang là '{r['effective_date']}'")
        sup = r["superseded_by"]
        if sup and (sup not in ids or sup == r["doc_id"]):
            errors.append(f"{where}: superseded_by '{sup}' phải là doc_id khác có trong manifest")
        if not r["source_url"].startswith(("https://", "http://")):
            errors.append(f"{where}: source_url phải là link http(s) tải được")

    files = [r["file"] for r in rows]
    for f in sorted({f for f in files if files.count(f) > 1}):
        errors.append(f"file {f} xuất hiện nhiều lần")
    missing = DEPARTMENTS - {r["department"] for r in rows}
    if missing:
        errors.append(f"thiếu department: {', '.join(sorted(missing))}")
    if not any(r["superseded_by"] for r in rows):
        errors.append("cần ít nhất 1 cặp văn bản mới thay thế văn bản cũ (superseded_by)")
    errors += _tracked_pdfs(manifest.parent)
    return errors


def _tracked_pdfs(data_dir: Path) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "--", str(data_dir)], capture_output=True, text=True, check=True
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return []  # not a git checkout: nothing to check
    return [f"PDF không được commit: {f}" for f in out if f.lower().endswith(".pdf")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument("--expect", type=int, default=30, help="số dòng mong đợi; 0 để bỏ qua")
    args = parser.parse_args(argv)
    errors = check(args.manifest, args.expect or None)
    for e in errors:
        print(f"LỖI  {e}")
    print(f"{'FAIL' if errors else 'OK'}  {args.manifest}: {len(errors)} lỗi")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
