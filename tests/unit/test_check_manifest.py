"""scripts/check_manifest.py on small manifests in a temp dir."""

import csv

from scripts.check_manifest import COLUMNS, check

ROWS = [
    ("tt-old", "old.pdf", "credit", "public", "2021-02-15", "tt-new", "https://sbv.gov.vn/old.pdf"),
    ("tt-new", "new.pdf", "credit", "public", "2026-11-02", "", "https://sbv.gov.vn/new.pdf"),
    ("bieu-phi", "fee.pdf", "public", "public", "2026-04-22", "", "https://www.vietinbank.vn/fee.pdf"),
    ("quy-che-luong", "hr.pdf", "hr", "internal", "2025-01-01", "", "https://example.org/hr.pdf"),
]


def _manifest(tmp_path, rows=ROWS, header=COLUMNS):
    with (tmp_path / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    for r in rows:
        (tmp_path / r[1]).write_bytes(b"%PDF-1.4\n")
    return tmp_path / "manifest.csv"


def test_valid_manifest_passes(tmp_path):
    assert check(_manifest(tmp_path), expect=4) == []


def test_reports_row_count_and_missing_coverage(tmp_path):
    errors = check(_manifest(tmp_path, rows=ROWS[1:3]), expect=30)

    assert "cần 30 dòng, đang có 2" in errors
    assert "thiếu department: hr" in errors
    assert any("superseded_by" in e for e in errors)


def test_reports_bad_fields_per_row(tmp_path):
    bad = ("Bad ID", "nope.pdf", "sales", "secret", "22/4/2026", "ghost", "")
    path = _manifest(tmp_path, rows=[*ROWS, bad])
    (tmp_path / "nope.pdf").unlink()

    errors = "\n".join(check(path, expect=5))

    for fragment in ("doc_id", "không có file", "department", "classification", "effective_date",
                     "superseded_by 'ghost'", "source_url"):
        assert fragment in errors


def test_rejects_wrong_header_and_duplicates(tmp_path):
    assert check(_manifest(tmp_path, header=COLUMNS[::-1]), expect=4)[0].startswith("header")

    dup = [*ROWS, ROWS[2]]
    errors = check(_manifest(tmp_path, rows=dup), expect=5)
    assert any("doc_id bị trùng" in e for e in errors)
    assert "file fee.pdf xuất hiện nhiều lần" in errors
