"""Check eval/golden.jsonl against T-022 and docs/12-ai/ai-design.md.

Usage: python eval/check_golden.py [--golden eval/golden.jsonl] [--manifest data/manifest.csv]
       [--parsed data/parsed] [--expect 50]
Prints every problem found and exits 1 if there is any, 0 otherwise. Stdlib only.

Categories: ``fact`` and ``table`` (one document), ``multi_hop`` (several passages),
``cross_department`` (a credit or hr document together with a public one), ``superseded``
(the answer changed when a document was replaced; only the replacement is cited) and
``out_of_scope`` (not answerable from the corpus; the reference is the API refusal).
Retrieval shows a user their own department plus ``public``, so no question may need both
credit and hr documents. Pages are checked against ``data/parsed`` when it exists (it is not
committed, so CI checks everything else).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

FIELDS = ["user_input", "reference", "sources", "category", "difficulty", "in_scope"]
CATEGORIES = {"fact", "table", "multi_hop", "cross_department", "superseded", "out_of_scope"}
DIFFICULTIES = {"easy", "medium", "hard"}
MINIMA = {"out_of_scope": 10, "cross_department": 5, "superseded": 3}
REFUSAL = "Không tìm thấy thông tin này trong tài liệu nội bộ hiện có."  # app.contracts.REFUSAL
_PAGE = re.compile(r"^## Trang (\d+)\s*$", re.MULTILINE)


def check(
    golden: Path,
    manifest: Path,
    expect: int | None = 50,
    minima: dict[str, int] = MINIMA,
    parsed: Path | None = None,
) -> list[str]:
    if not golden.is_file():
        return [f"{golden}: không tìm thấy file"]
    if not manifest.is_file():
        return [f"{manifest}: không tìm thấy file"]
    with manifest.open(newline="", encoding="utf-8") as fh:
        docs = {r["file"]: r for r in csv.DictReader(fh)}
    replacements = {r["superseded_by"] for r in docs.values() if r["superseded_by"]}
    pages = _page_counts(parsed, docs) if parsed and parsed.is_dir() else {}

    errors: list[str] = []
    rows: list[dict] = []
    seen: dict[str, int] = {}
    for n, line in enumerate(golden.read_text(encoding="utf-8").splitlines(), start=1):
        where = f"dòng {n}"
        if not line.strip():
            errors.append(f"{where}: dòng trống")
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"{where}: JSON không hợp lệ ({e.msg})")
            continue
        if not isinstance(r, dict):
            errors.append(f"{where}: mỗi dòng phải là một object JSON")
            continue
        if sorted(r) != sorted(FIELDS):
            errors.append(f"{where}: trường phải là {', '.join(FIELDS)}, đang là {', '.join(r)}")
            continue
        rows.append(r)
        errors += [f"{where}: {e}" for e in _row_errors(r, docs, replacements, pages)]
        if isinstance(r["user_input"], str) and r["user_input"].strip():
            key = " ".join(r["user_input"].lower().split())
            if key in seen:
                errors.append(f"{where}: user_input trùng với dòng {seen[key]}")
            seen.setdefault(key, n)

    if expect is not None and len(rows) != expect:
        errors.append(f"cần {expect} câu, đang có {len(rows)}")
    for category, minimum in minima.items():
        count = sum(r["category"] == category for r in rows)
        if count < minimum:
            errors.append(f"cần ≥ {minimum} câu {category}, đang có {count}")
    return errors


def _row_errors(r: dict, docs: dict[str, dict], replacements: set[str], pages: dict[str, int]) -> list[str]:
    errors = []
    for name in ("user_input", "reference"):
        if not isinstance(r[name], str) or not r[name].strip():
            errors.append(f"{name} phải là chuỗi không rỗng")
    if r["category"] not in CATEGORIES:
        errors.append(f"category phải thuộc {sorted(CATEGORIES)}")
    if r["difficulty"] not in DIFFICULTIES:
        errors.append(f"difficulty phải thuộc {sorted(DIFFICULTIES)}")
    if not isinstance(r["in_scope"], bool):
        errors.append("in_scope phải là true/false")
    if not isinstance(r["sources"], list):
        return [*errors, "sources phải là danh sách {file, page}"]

    cited: list[dict] = []
    for i, s in enumerate(r["sources"]):
        if not (isinstance(s, dict) and sorted(s) == ["file", "page"]):
            errors.append(f"sources[{i}] phải có đúng hai trường file, page")
            continue
        if type(s["page"]) is not int or s["page"] < 1:
            errors.append(f"sources[{i}]: page phải là số nguyên ≥ 1")
        doc = docs.get(s["file"])
        if doc is None:
            errors.append(f"sources[{i}]: {s['file']} không có trong manifest")
            continue
        if doc["superseded_by"]:
            errors.append(f"sources[{i}]: {s['file']} đã bị thay thế bởi {doc['superseded_by']}, không được trích")
        if s["file"] in pages and type(s["page"]) is int and s["page"] > pages[s["file"]]:
            errors.append(f"sources[{i}]: {s['file']} chỉ có {pages[s['file']]} trang")
        cited.append(doc)
    pairs = [(s.get("file"), s.get("page")) for s in r["sources"] if isinstance(s, dict)]
    if len(set(pairs)) < len(pairs):
        errors.append("sources có nguồn trùng")

    departments = {d["department"] for d in cited}
    if {"credit", "hr"} <= departments:
        errors.append("nguồn gồm cả credit và hr: không user nào truy xuất được cả hai")
    out = r["category"] == "out_of_scope"
    if out != (r["in_scope"] is False):
        errors.append("category out_of_scope khi và chỉ khi in_scope là false")
    if r["in_scope"] is False:
        if r["sources"]:
            errors.append("câu ngoài phạm vi không có nguồn")
        if r["reference"] != REFUSAL:
            errors.append(f"reference của câu ngoài phạm vi phải là câu từ chối: {REFUSAL!r}")
    elif r["in_scope"] is True and not r["sources"]:
        errors.append("câu trong phạm vi cần ít nhất 1 nguồn")
    if r["category"] == "cross_department" and not ("public" in departments and len(departments) == 2):
        errors.append("câu cross_department cần nguồn của public và đúng một phòng (credit hoặc hr)")
    if r["category"] == "superseded" and not any(d["doc_id"] in replacements for d in cited):
        errors.append("câu superseded phải trích văn bản thay thế (doc là superseded_by của văn bản cũ)")
    return errors


def _page_counts(parsed: Path, docs: dict[str, dict]) -> dict[str, int]:
    counts = {}
    for file in docs:
        md = parsed / f"{Path(file).stem}.md"
        if md.is_file():
            found = [int(p) for p in _PAGE.findall(md.read_text(encoding="utf-8"))]
            if found:
                counts[file] = max(found)
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--golden", type=Path, default=Path("eval/golden.jsonl"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument("--parsed", type=Path, default=Path("data/parsed"), help="bỏ qua nếu thư mục không có")
    parser.add_argument("--expect", type=int, default=50, help="số câu mong đợi; 0 để bỏ qua")
    args = parser.parse_args(argv)
    errors = check(args.golden, args.manifest, args.expect or None, parsed=args.parsed)
    for e in errors:
        print(f"LỖI  {e}")
    print(f"{'FAIL' if errors else 'OK'}  {args.golden}: {len(errors)} lỗi")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
