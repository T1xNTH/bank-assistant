"""Scan repair paths of parse_docling (CR-007) without OCR models: runs in CI."""

import os
import subprocess
import sys
import textwrap
from types import SimpleNamespace

import pytest
from docling.backend.docling_parse_backend import ThreadedDoclingParseDocumentBackend
from docling.datamodel.base_models import ConversionStatus, InputFormat
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
    monkeypatch.setattr(pd, "_convert", lambda path, full: path)
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


def test_choose_pages_takes_pages_only_the_image_copy_has():
    chosen = pd.choose_pages([_page(1, UPRIGHT_OCR), _page(3, UPRIGHT_OCR)], [_page(n, UPRIGHT_OCR) for n in (1, 2, 3)])

    assert [p["page"] for p in chosen] == [1, 2, 3]


def test_choose_pages_keeps_the_original_table_when_the_copy_loses_its_amounts():
    # The garbage table (no diacritics) marks the page, and the copy scores higher only
    # because the table is gone: its figures must not be traded for readability.
    table = (
        "| Muc | So tien |\n|---|---|\n"
        "| Luong co ban thang mot nam nay | 22.700.000 |\n| Phu cap trach nhiem cong viec | 3.000.000 |"
    )
    copy = _page(1, UPRIGHT_OCR)

    [chosen] = pd.choose_pages([_page(1, UPRIGHT_OCR, [table])], [copy])

    assert chosen["text"] == copy["text"]
    assert chosen["tables"] == [table]


def test_choose_pages_keeps_a_table_of_short_rates_the_copy_lost():
    table = (
        "| Loai phi | Muc phi |\n|---|---|\n"
        "| Phi rut tien mat tai cay ATM ngoai he thong | 4% |\n| Phi chuyen doi ngoai te khi giao dich | 5% |"
    )

    [chosen] = pd.choose_pages([_page(1, UPRIGHT_OCR, [table])], [_page(1, UPRIGHT_OCR)])

    assert chosen["tables"] == [table]


def test_choose_pages_keeps_the_original_table_when_the_copy_table_has_no_amounts():
    # Same number of tables, but the copy's table lost every amount.
    table = (
        "| Muc | So tien |\n|---|---|\n"
        "| Phi phat hanh the tin dung quoc te hang vang | 22.700.000 |\n| Phi thuong nien the chinh | 1.000.000 |"
    )
    generic = "| Phí | Theo quy định |\n|---|---|\n| Phí phát hành thẻ | Theo biểu phí hiện hành |"

    [chosen] = pd.choose_pages([_page(1, UPRIGHT_OCR, [table])], [_page(1, UPRIGHT_OCR + " của và các", [generic])])

    assert chosen["tables"] == [generic, table]


def test_choose_pages_does_not_duplicate_a_table_whose_figures_the_copy_kept():
    table = (
        "| Vung | Muc luong toi thieu thang theo quy dinh |\n|---|---|\n"
        "| Vung I cac quan noi thanh | 5.310.000 |\n| Vung II cac huyen ngoai thanh | 4.730.000 |"
    )
    read = "| Vùng | Mức lương tối thiểu tháng |\n|---|---|\n| Vùng I | 5.310.000 |"
    copy = _page(1, UPRIGHT_OCR + " của và các", [read])

    [chosen] = pd.choose_pages([_page(1, UPRIGHT_OCR, [table])], [copy])

    assert chosen is copy  # half the figures survive: the copy's read of the table stands


def test_choose_pages_drops_a_garbage_table_without_figures():
    # The empty grid of a blank form: noise, not content the copy must keep.
    grid = (
        "| i n khich hirng so til | Ptay tny then loai giiy lil tiry than | v!t Ngnv thrng nIm sinh |\n"
        "|---|---|---|\n| t2) | 6 | 11 |"
    )
    copy = _page(1, UPRIGHT_OCR + " của và các")

    [chosen] = pd.choose_pages([_page(1, UPRIGHT_OCR, [grid])], [copy])

    assert chosen is copy


def test_choose_pages_drops_an_ocr_noise_table_with_a_stray_figure():
    # 77-nhnn p.13: scribble OCR'd into a "table" whose noise happens to contain 124.
    noise = (
        "| | 0 i |\n|---|---|\n| .i5 E:r oe | a te tc |\n"
        "| --o!nl- XoE-BE. -ita5o-o '. L.l' .9,E' If c-9' a) 2>S | o |\n"
        "| ra - O r.J = = Or o- - = e /'\\ F nE$=rx;Y$r€gE8. - i Ftiee'ilE=S-aF |\n"
        "| E3€a, Eg 1+ A *a.22 124 :o E= | := - j |"
    )
    copy = _page(1, UPRIGHT_OCR + " của và các")

    [chosen] = pd.choose_pages([_page(1, UPRIGHT_OCR, [noise])], [copy])

    assert chosen is copy


def _conversion(status, pages, errors=()):
    return SimpleNamespace(convert=lambda path: SimpleNamespace(status=status, errors=list(errors), document=pages))


def test_partial_conversion_missing_a_page_is_an_error(monkeypatch):
    monkeypatch.setattr(pd, "_text_layer", lambda path: UPRIGHT_OCR)
    monkeypatch.setattr(pd, "_page_count", lambda path: 3)
    monkeypatch.setattr(pd, "_converter", lambda full: _conversion(ConversionStatus.PARTIAL_SUCCESS, [1, 3]))
    monkeypatch.setattr(pd, "doc_to_pages", lambda doc, source: [_page(n, UPRIGHT_OCR) for n in doc])

    with pytest.raises(pd.ParseError, match=r"pages \[2\]"):
        pd.parse("digital.pdf")


def test_failed_conversion_is_an_error(monkeypatch):
    failed = _conversion(ConversionStatus.FAILURE, None, [SimpleNamespace(error_message="page 2: boom")])
    monkeypatch.setattr(pd, "_converter", lambda full: failed)

    with pytest.raises(pd.ParseError, match="failure: page 2: boom"):
        pd._convert("x.pdf", True)


def test_scan_page_missing_from_both_passes_is_an_error(monkeypatch):
    monkeypatch.setattr(pd, "_text_layer", lambda path: "")
    monkeypatch.setattr(pd, "_page_count", lambda path: 3)
    monkeypatch.setattr(pd, "_image_only_pdf", lambda path, out: out)
    monkeypatch.setattr(pd, "_ocr_pages", lambda path, source, tmp: [_page(1, UPRIGHT_OCR), _page(3, UPRIGHT_OCR)])

    with pytest.raises(pd.ParseError, match=r"pages \[2\]"):
        pd.parse("scan.pdf")


@pytest.mark.skipif(sys.platform == "win32", reason="fake tesseract is a POSIX script")
def test_tesseract_output_is_decoded_as_utf8_under_a_non_utf8_locale(tmp_path):
    # Windows decodes pipes as cp1252; an ASCII C locale reproduces that failure on Linux.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "tesseract"
    fake.write_text(f"#!{sys.executable}\nimport sys\nsys.stdout.buffer.write('Ngân hàng'.encode())\n")
    fake.chmod(0o755)
    script = textwrap.dedent(f"""
        from pathlib import Path
        from PIL import Image
        from app.rag import parse_docling as pd
        print(pd._tesseract(Image.new("L", (10, 10)), Path({str(tmp_path / "x.png")!r})).encode("utf-8").hex())
    """)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "LC_ALL": "C",
           "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0", "PYTHONPATH": os.pathsep.join(sys.path)}

    done = subprocess.run([sys.executable, "-c", script], capture_output=True, env=env, check=False)

    assert done.returncode == 0, done.stderr.decode(errors="replace")
    assert bytes.fromhex(done.stdout.decode().strip()).decode("utf-8") == "Ngân hàng"
