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


def check(manifest: Path, expect: int | None = 30, as_of: date | None = None) -> list[str]:
    """Problems in the manifest. ``as_of`` (default today) decides which replacements are already in force."""
    as_of = as_of or date.today()
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
    by_id = {r["doc_id"]: r for r in rows}
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
        elif not _is_pdf(manifest.parent / r["file"]):
            errors.append(f"{where}: {r['file']} không phải PDF; xem docs/07-development/corpus.md")
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
        elif sup:
            errors += _replacement_errors(where, r, by_id[sup], as_of)
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


def _is_pdf(path: Path) -> bool:
    with path.open("rb") as fh:
        return fh.read(5) == b"%PDF-"


def _replacement_errors(where: str, row: dict, new: dict, as_of: date) -> list[str]:
    """Retrieval drops a row as soon as superseded_by is set, so the replacement must already be in force."""
    try:
        old_date, new_date = date.fromisoformat(row["effective_date"]), date.fromisoformat(new["effective_date"])
    except ValueError:
        return []  # reported per row already
    if new_date > as_of:
        return [f"{where}: superseded_by '{new['doc_id']}' chưa có hiệu lực ({new_date}); chỉ đánh dấu từ ngày đó"]
    if new_date <= old_date:
        return [f"{where}: '{new['doc_id']}' ({new_date}) phải có hiệu lực sau văn bản bị thay ({old_date})"]
    return []


def _tracked_pdfs(data_dir: Path) -> list[str]:
    try:
        # -z: NUL-separated, unquoted UTF-8 paths (otherwise non-ASCII names come back as "\341..." escapes)
        out = subprocess.run(
            ["git", "-C", str(data_dir), "ls-files", "-z", "--", "."], capture_output=True, check=True
        ).stdout.decode("utf-8").split("\0")
    except (OSError, subprocess.CalledProcessError):
        return []  # not a git checkout: nothing to check
    return [f"PDF không được commit: {data_dir / f}" for f in out if f.lower().endswith(".pdf")]


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
