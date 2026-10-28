"""scripts/check_manifest.py on small manifests in a temp dir."""

import csv
import subprocess
from datetime import date

import pytest

from scripts.check_manifest import COLUMNS, _tracked_pdfs, check

AS_OF = date(2026, 12, 1)  # after every effective_date in ROWS

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
    assert check(_manifest(tmp_path), expect=4, as_of=AS_OF) == []


def test_reports_row_count_and_missing_coverage(tmp_path):
    errors = check(_manifest(tmp_path, rows=ROWS[1:3]), expect=30, as_of=AS_OF)

    assert "cần 30 dòng, đang có 2" in errors
    assert "thiếu department: hr" in errors
    assert any("superseded_by" in e for e in errors)


def test_reports_bad_fields_per_row(tmp_path):
    bad = ("Bad ID", "nope.pdf", "sales", "secret", "22/4/2026", "ghost", "")
    path = _manifest(tmp_path, rows=[*ROWS, bad])
    (tmp_path / "nope.pdf").unlink()

    errors = "\n".join(check(path, expect=5, as_of=AS_OF))

    for fragment in ("doc_id", "không có file", "department", "classification", "effective_date",
                     "superseded_by 'ghost'", "source_url"):
        assert fragment in errors


def test_rejects_wrong_header_and_duplicates(tmp_path):
    assert check(_manifest(tmp_path, header=COLUMNS[::-1]), expect=4, as_of=AS_OF)[0].startswith("header")

    dup = [*ROWS, ROWS[2]]
    errors = check(_manifest(tmp_path, rows=dup), expect=5, as_of=AS_OF)
    assert any("doc_id bị trùng" in e for e in errors)
    assert "file fee.pdf xuất hiện nhiều lần" in errors


def test_replacement_must_already_be_in_force_and_newer(tmp_path):
    path = _manifest(tmp_path)  # tt-new takes effect 2026-11-02

    before = check(path, expect=4, as_of=date(2026, 10, 28))
    assert any("chưa có hiệu lực (2026-11-02)" in e for e in before)
    assert check(path, expect=4, as_of=date(2026, 11, 2)) == []

    backwards = [("tt-old", "old.pdf", "credit", "public", "2026-12-01", "tt-new", "https://x/old.pdf"), *ROWS[1:]]
    errors = check(_manifest(tmp_path, rows=backwards), expect=4, as_of=AS_OF)
    assert any("phải có hiệu lực sau văn bản bị thay" in e for e in errors)


def test_html_saved_as_pdf_is_rejected(tmp_path):
    path = _manifest(tmp_path)
    (tmp_path / "fee.pdf").write_text("<!DOCTYPE html><html>Biểu phí</html>", encoding="utf-8")

    assert any("fee.pdf không phải PDF" in e for e in check(path, expect=4, as_of=AS_OF))


@pytest.mark.parametrize("name", ["biểu-phí.pdf", "plain.PDF"])
def test_tracked_pdf_is_reported_even_with_vietnamese_name(tmp_path, name):
    data = tmp_path / "data"
    data.mkdir()
    (data / name).write_bytes(b"%PDF-1.4\n")
    (data / "manifest.csv").write_text("x", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)

    assert _tracked_pdfs(data) == [f"PDF không được commit: {data / name}"]
