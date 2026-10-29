"""Rotation selection must improve recognition, not just a noisy language score."""

import json
from pathlib import Path

from app.rag import parse_docling as pd


def test_plain_ocr_keeps_a_sparse_financial_table_even_when_it_reads_more_text(tmp_path, monkeypatch):
    table = "| STT | So tien |\n|---|---|\n| 1 | 22.700.000 |\n| 2 | 3.000.000 |"
    original = {"source": "scan.pdf", "page": 3, "text": "Ký tên", "tables": [table]}
    text = "Ngân hàng xác nhận chữ ký của người đại diện."
    monkeypatch.setattr(pd, "_render", lambda *args: object())
    monkeypatch.setattr(pd, "_tesseract", lambda *args: text)

    fixed = pd._repair("scan.pdf", original, tmp_path)

    assert fixed == {**original, "text": text}
    assert original["text"] == "Ký tên"


def test_plain_ocr_keeps_table_associations_even_if_it_mentions_the_same_amounts(tmp_path, monkeypatch):
    table = "| Dịch vụ | Phí |\n|---|---|\n| Rút tiền | 4 % |\n| Chuyển tiền | 5 % |"
    original = {"source": "scan.pdf", "page": 3, "text": "", "tables": [table]}
    text = "Ngân hàng xác nhận chữ ký của người đại diện. Chuyển tiền 4%, rút tiền 5%."
    monkeypatch.setattr(pd, "_render", lambda *args: object())
    monkeypatch.setattr(pd, "_tesseract", lambda *args: text)

    assert pd._repair("scan.pdf", original, tmp_path)["tables"] == [table]


def _mock_rotations(monkeypatch, candidates):
    monkeypatch.setattr(pd, "_rotated_page_pdf", lambda path, no, angle, out: angle)
    monkeypatch.setattr(pd, "_convert", lambda angle, full: angle)
    monkeypatch.setattr(pd, "doc_to_pages", lambda angle, source: candidates[int(angle)])


def test_upright_province_table_is_not_replaced_by_a_marginally_better_transposed_table(tmp_path, monkeypatch):
    # Captured from real Docling/Tesseract output, PDF page 109 (printed page 16).
    fixture = Path(__file__).parents[1] / "fixtures/ocr/145-page-109.json"
    captured = json.loads(fixture.read_text(encoding="utf-8"))
    original, rotated = captured["selected"], captured["bad_rotation"]
    assert pd.looks_garbled(original)
    assert pd._score(rotated) > pd._score(original)  # old selection loses the upright table
    assert len(original["tables"][0].splitlines()) == 32
    assert len(rotated["tables"][0].splitlines()) == 4
    _mock_rotations(monkeypatch, {90: [rotated], 180: [], 270: [rotated]})

    fixed = pd._repair("145.signed.pdf", original, tmp_path)

    assert fixed is original
    assert fixed["page"] == 109


def test_noisy_rotation_does_not_replace_even_noisier_text(tmp_path, monkeypatch):
    original = {"source": "scan.pdf", "page": 7, "text": "xyz " * 100, "tables": []}
    rotated = {**original, "page": 1, "text": "của " + "xyz " * 100}
    _mock_rotations(monkeypatch, {90: [rotated], 180: [rotated], 270: [rotated]})

    assert pd._repair("scan.pdf", original, tmp_path) is original


def test_readable_rotation_still_recovers_a_page_after_a_noisy_candidate(tmp_path, monkeypatch):
    original = {"source": "scan.pdf", "page": 7, "text": "xyz " * 100, "tables": []}
    noisy = {**original, "page": 1, "text": "của " + "xyz " * 100}
    readable = {**original, "page": 1, "text": "Ngân hàng quy định phí thanh toán dịch vụ. " * 10}
    _mock_rotations(monkeypatch, {90: [noisy], 180: [readable], 270: []})

    assert pd._repair("scan.pdf", original, tmp_path) == {**readable, "page": 7}
