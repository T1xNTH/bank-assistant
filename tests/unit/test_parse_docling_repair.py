"""Scan repair paths of parse_docling (CR-007) without OCR models: runs in CI."""

import subprocess
from types import SimpleNamespace

import pytest
from docling.backend.docling_parse_backend import ThreadedDoclingParseDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument
from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DoclingDocument,
    ProvenanceItem,
    Size,
    TableCell,
    TableData,
)
from PIL import Image

from app.rag import parse_docling as pd
from tests.pdf_fixtures import write_fee_table_pdf
from tests.unit.test_parse_docling import UPRIGHT_OCR, UPSIDE_DOWN_OCR

GARBAGE = UPSIDE_DOWN_OCR * 2
TEXT_LAYER_TABLE = "| STT | Loqi hinh giao dich | Giao dich loai A | Giao dich loai B | Han muc toi da theo ngay |"
WAGE_TABLE = "| Vùng | Mức lương tối thiểu tháng |\n|---|---|\n| Vùng I | 5.310.000 |"


def _page(no, text="", tables=()):
    return {"source": "x.pdf", "page": no, "text": text, "tables": list(tables)}


def _page_texts(backend, pdf):
    doc = InputDocument(path_or_stream=pdf, format=InputFormat.PDF, backend=backend)
    whole = BoundingBox(l=0, t=0, r=600, b=850)
    try:
        return [page.get_text_in_rect(whole) for page in doc._backend.iter_pages()]
    finally:
        doc._backend.unload()


def test_ocr_only_backend_hides_the_pdf_text_layer(tmp_path):
    pdf = write_fee_table_pdf(tmp_path / "fee.pdf")

    # docling's table models fall back to get_text_in_rect; it must never see the text layer.
    assert pd._ocr_only_backend().supports_random_page_access is False  # pages come from iter_pages()
    assert _page_texts(pd._ocr_only_backend(), pdf) == [""]
    assert "BIỂU PHÍ" in _page_texts(ThreadedDoclingParseDocumentBackend, pdf)[0]  # the patch is what hides it


def test_choose_pages_takes_the_image_copy_only_where_the_original_is_garbage():
    original = [
        _page(1, UPRIGHT_OCR),
        _page(2, UPRIGHT_OCR, [TEXT_LAYER_TABLE]),  # table read from the scanner's text layer
        _page(3, GARBAGE),
        _page(4, GARBAGE),  # copy is missing this page
    ]
    copy = [
        _page(1, UPRIGHT_OCR + " của và các"),  # reads even better, but the original is fine
        _page(2, UPRIGHT_OCR, [WAGE_TABLE]),
        _page(3, GARBAGE + " x"),  # also garbage: not better
    ]

    chosen = pd.choose_pages(original, copy)

    assert [p["page"] for p in chosen] == [1, 2, 3, 4]
    assert chosen[0] is original[0]
    assert chosen[1] is copy[1]
    assert chosen[2] is original[2]
    assert chosen[3] is original[3]


def test_best_rotation_keeps_the_most_readable_orientation(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "_rotated_page_pdf", lambda path, no, rotate, out: f"rot{rotate}")
    monkeypatch.setattr(pd, "_converter", lambda full: SimpleNamespace(convert=lambda p: SimpleNamespace(document=p)))
    monkeypatch.setattr(pd, "doc_to_pages", lambda doc, source: [_page(1, UPRIGHT_OCR if doc == "rot180" else GARBAGE)])

    fixed = pd._best_rotation("scan.pdf", _page(7, GARBAGE), tmp_path)

    assert fixed["page"] == 7
    assert fixed["text"] == UPRIGHT_OCR

    monkeypatch.setattr(pd, "doc_to_pages", lambda doc, source: [_page(1, GARBAGE)])
    unchanged = _page(7, GARBAGE)
    assert pd._best_rotation("scan.pdf", unchanged, tmp_path) is unchanged


def test_table_without_cells_is_ocred_as_a_region(tmp_path, monkeypatch):
    doc = DoclingDocument(name="x")
    doc.add_page(page_no=1, size=Size(width=600, height=800))
    bbox = BoundingBox(l=100, t=700, r=300, b=600, coord_origin=CoordOrigin.BOTTOMLEFT)
    doc.add_table(data=TableData(num_rows=0, num_cols=0, table_cells=[]),
                  prov=ProvenanceItem(page_no=1, bbox=bbox, charspan=(0, 0)))
    cell = TableCell(text="a", start_row_offset_idx=0, end_row_offset_idx=1, start_col_offset_idx=0,
                     end_col_offset_idx=1)
    doc.add_table(data=TableData(num_rows=1, num_cols=1, table_cells=[cell]),
                  prov=ProvenanceItem(page_no=1, bbox=bbox, charspan=(0, 0)))
    crops = []

    def fake_tesseract(img, file, psm=None):
        crops.append((img.size, psm))
        return "Vùng I 5.310.000"

    monkeypatch.setattr(pd, "_render", lambda path, no: Image.new("L", (1667, 2222), 255))
    monkeypatch.setattr(pd, "_tesseract", fake_tesseract)

    assert pd._ocr_empty_tables("scan.pdf", doc, 1, tmp_path) == ["Vùng I 5.310.000"]
    k = pd.RENDER_DPI / 72
    [((w, h), psm)] = crops  # only the cell-less table is OCR'd
    assert psm == 4
    assert abs(w - 200 * k) <= 1 and abs(h - 100 * k) <= 1  # its 200x100 pt box at render resolution


def test_near_empty_page_falls_back_to_plain_ocr_without_duplicate_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "_render", lambda path, no: Image.new("L", (10, 10)))
    monkeypatch.setattr(pd, "_tesseract", lambda img, file, psm=None: UPRIGHT_OCR)

    fixed = pd._repair("scan.pdf", _page(3, "Ký tên", ["| a |"]), tmp_path)

    assert fixed == _page(3, UPRIGHT_OCR)


def test_tesseract_failure_is_raised_not_swallowed(tmp_path, monkeypatch):
    failed = subprocess.CompletedProcess([], 1, stdout="", stderr="Failed loading language 'vie'")
    monkeypatch.setattr(pd.subprocess, "run", lambda *a, **kw: failed)

    with pytest.raises(RuntimeError, match="vie"):
        pd._tesseract(Image.new("L", (10, 10)), tmp_path / "x.png")
