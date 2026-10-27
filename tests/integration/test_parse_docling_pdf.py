"""Real docling runs (layout, TableFormer, Tesseract vie). Downloads models on first run."""

import shutil

import pytest

from app.rag.parse_docling import parse
from tests.pdf_fixtures import FEE_ROWS, write_fee_table_pdf, write_scanned_pdf

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("tesseract") is None, reason="needs tesseract-ocr + tesseract-ocr-vie"),
]


def test_digital_fee_schedule_table_as_markdown(tmp_path):
    pages = parse(str(write_fee_table_pdf(tmp_path / "bieu-phi.pdf")))

    assert [p["page"] for p in pages] == [1]
    assert "BIỂU PHÍ DỊCH VỤ THẺ" in pages[0]["text"]
    assert len(pages[0]["tables"]) == 1
    table = pages[0]["tables"][0]
    for row in FEE_ROWS:
        assert all(cell in table for cell in row)


def test_scanned_page_yields_vietnamese_text(tmp_path):
    pages = parse(str(write_scanned_pdf(tmp_path / "scan.pdf")))

    text = pages[0]["text"]
    assert text.strip()
    assert "PHÍ" in text and "66.000" in text
