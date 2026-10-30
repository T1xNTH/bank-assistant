"""eval/check_golden.py on small golden sets in a temp dir, and on the committed eval/golden.jsonl."""

import json
from pathlib import Path

import pytest

from app.contracts import REFUSAL as APP_REFUSAL
from eval.check_golden import REFUSAL, check
from scripts.check_manifest import COLUMNS

MANIFEST = [
    ("tt-old", "old.pdf", "credit", "public", "2021-02-15", "tt-new", "https://x/old.pdf"),
    ("tt-new", "new.pdf", "credit", "public", "2026-08-15", "", "https://x/new.pdf"),
    ("bieu-phi", "fee.pdf", "public", "public", "2026-04-22", "", "https://x/fee.pdf"),
    ("luong", "hr.pdf", "hr", "public", "2026-01-01", "", "https://x/hr.pdf"),
]
MINIMA = {"out_of_scope": 1, "cross_department": 1, "superseded": 1}


def row(**fields):
    base = {
        "user_input": "Phí phát hành thẻ là bao nhiêu?",
        "reference": "Miễn phí.",
        "sources": [{"file": "fee.pdf", "page": 1}],
        "category": "fact",
        "difficulty": "easy",
        "in_scope": True,
    }
    return {**base, **fields}


ROWS = [
    row(),
    row(user_input="Lãi suất cho vay tối đa?", reference="5%.", sources=[{"file": "new.pdf", "page": 2}],
        category="superseded", difficulty="medium"),
    row(user_input="Thẻ tín dụng: phí và điều kiện?", reference="...",
        sources=[{"file": "new.pdf", "page": 1}, {"file": "fee.pdf", "page": 1}], category="cross_department"),
    row(user_input="Giá vàng hôm nay?", reference=REFUSAL, sources=[], category="out_of_scope", in_scope=False),
]


def write(tmp_path, rows=ROWS, raw=None):
    with (tmp_path / "manifest.csv").open("w", encoding="utf-8") as fh:
        fh.write(",".join(COLUMNS) + "\n" + "".join(",".join(r) + "\n" for r in MANIFEST))
    golden = tmp_path / "golden.jsonl"
    golden.write_text(raw if raw is not None else "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                      encoding="utf-8")
    return golden, tmp_path / "manifest.csv"


def errors_for(tmp_path, rows=ROWS, **kwargs):
    golden, manifest = write(tmp_path, rows)
    return check(golden, manifest, expect=len(rows), minima=MINIMA, **kwargs)


def test_valid_set_passes(tmp_path):
    assert errors_for(tmp_path) == []


def test_refusal_matches_the_api_contract():
    assert REFUSAL == APP_REFUSAL


def test_counts_and_minimum_coverage(tmp_path):
    golden, manifest = write(tmp_path, ROWS[:1])
    errors = check(golden, manifest, expect=50, minima={"out_of_scope": 10, "cross_department": 5, "superseded": 3})
    assert "cần 50 câu, đang có 1" in errors
    assert "cần ≥ 10 câu out_of_scope, đang có 0" in errors
    assert "cần ≥ 5 câu cross_department, đang có 0" in errors
    assert "cần ≥ 3 câu superseded, đang có 0" in errors


@pytest.mark.parametrize("bad, fragment", [
    ({"extra": 1}, "trường phải là"),
    ({"user_input": "  "}, "user_input"),
    ({"reference": ""}, "reference"),
    ({"category": "trivia"}, "category"),
    ({"difficulty": "extreme"}, "difficulty"),
    ({"in_scope": "true"}, "in_scope"),
    ({"sources": "fee.pdf"}, "sources"),
    ({"sources": []}, "câu trong phạm vi cần ít nhất 1 nguồn"),
    ({"sources": [{"file": "fee.pdf"}]}, "sources[0]"),
    ({"sources": [{"file": "fee.pdf", "page": 0}]}, "page"),
    ({"sources": [{"file": "fee.pdf", "page": True}]}, "page"),
    ({"sources": [{"file": "ghost.pdf", "page": 1}]}, "không có trong manifest"),
    ({"sources": [{"file": "old.pdf", "page": 1}]}, "đã bị thay thế"),
    ({"sources": [{"file": "fee.pdf", "page": 1}, {"file": "fee.pdf", "page": 1}]}, "trùng"),
    ({"sources": [{"file": "new.pdf", "page": 1}, {"file": "hr.pdf", "page": 1}]}, "không user nào"),
])
def test_rejects_bad_rows(tmp_path, bad, fragment):
    errors = errors_for(tmp_path, [row(**bad), *ROWS[1:]])
    assert any(e.startswith("dòng 1") and fragment in e for e in errors), errors



@pytest.mark.parametrize("bad, fragment", [
    ({"category": []}, "category"),
    ({"difficulty": {}}, "difficulty"),
    ({"sources": [{"file": [], "page": 1}]}, "file"),
    ({"sources": [{"file": "fee.pdf", "page": []}]}, "page"),
    ({"sources": [{"file": {}, "page": {}}]}, "file"),
])
def test_unhashable_values_are_reported_not_raised(tmp_path, bad, fragment):
    errors = errors_for(tmp_path, [row(**bad), *ROWS[1:]])
    assert any(e.startswith("dòng 1") and fragment in e for e in errors), errors

@pytest.mark.parametrize("bad, fragment", [
    (row(category="out_of_scope", in_scope=True), "out_of_scope"),
    (row(category="fact", in_scope=False, reference=REFUSAL, sources=[]), "out_of_scope"),
    (row(category="out_of_scope", in_scope=False, reference=REFUSAL), "không có nguồn"),
    (row(category="out_of_scope", in_scope=False, sources=[]), "câu từ chối"),
    (row(category="cross_department"), "public và đúng một phòng"),
    (row(category="cross_department", sources=[{"file": "new.pdf", "page": 1}]), "public và đúng một phòng"),
    (row(category="superseded"), "văn bản thay thế"),
])
def test_category_rules(tmp_path, bad, fragment):
    errors = errors_for(tmp_path, [bad, *ROWS[1:]])
    assert any(e.startswith("dòng 1") and fragment in e for e in errors), errors


def test_duplicate_question_and_broken_json(tmp_path):
    errors = errors_for(tmp_path, [*ROWS, row(user_input=" phí phát hành thẻ là bao nhiêu? ")])
    assert any(e.startswith("dòng 5") and "trùng" in e for e in errors)

    golden, manifest = write(tmp_path, raw=json.dumps(ROWS[0]) + "\n{not json\n\n[]\n")
    errors = check(golden, manifest, expect=None, minima={})
    assert any(e.startswith("dòng 2") and "JSON" in e for e in errors)
    assert any(e.startswith("dòng 3") and "dòng trống" in e for e in errors)
    assert any(e.startswith("dòng 4") and "object" in e for e in errors)


def test_pages_are_checked_against_parsed_text_when_available(tmp_path):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    (parsed / "fee.md").write_text("# fee.pdf\n\n---\n## Trang 1\n\nPhí\n", encoding="utf-8")
    (parsed / "new.md").write_text("## Trang 1\n\nx\n\n## Trang 2\n\ny\n", encoding="utf-8")
    assert errors_for(tmp_path, parsed=parsed) == []

    errors = errors_for(tmp_path, [row(sources=[{"file": "fee.pdf", "page": 3}]), *ROWS[1:]], parsed=parsed)
    assert any(e.startswith("dòng 1") and "fee.pdf chỉ có 1 trang" in e for e in errors)


def test_committed_golden_set_passes():
    root = Path(__file__).resolve().parents[2]
    assert check(root / "eval/golden.jsonl", root / "data/manifest.csv") == []
