"""Parse PDFs with docling (tables as Markdown, OCR) into pages.

Owner: A — Epic E-003. See docs/00-project/product-plan.md.

Each page is ``{"source", "page", "text", "tables"}``: ``page`` counts from 1,
``text`` is the page's non-table text in reading order (headings as ``## ``,
list items as ``- ``), ``tables`` holds one Markdown table per table on the page.
Every page of the PDF is returned, including empty ones. An item that spans pages
(e.g. a table continued on the next page) is placed on the page where it starts.
Text docling nests inside pictures (e.g. OCR of an embedded scan) is included.

OCR uses the Tesseract CLI with the Vietnamese model (``tesseract-ocr-vie``).
A PDF whose text layer is usable is read from that layer; OCR then only covers
images. A scanned PDF, or one whose text layer is scanner garbage (no
Vietnamese diacritics), is OCR'd page by page instead, with a PDF backend whose
text-layer lookup returns nothing: docling's table model otherwise falls back to
the garbage text layer for cells without an OCR match. A page whose OCR output
has almost no common Vietnamese words was likely scanned rotated; it is retried
at 90/180/270 degrees (PDF /Rotate, lossless) and the most readable orientation
is kept. A page that
comes back nearly empty (e.g. TableFormer found a table but no cells) falls back
to plain Tesseract text of the page image when that reads more. A table that
TableFormer detects but cannot split into cells is OCR'd as a region instead,
so its rows survive as text lines.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docling.document_converter import DocumentConverter
    from docling_core.types.doc import DoclingDocument

OCR_LANGS = ["vie"]
SAMPLE_PAGES = 3
MIN_LETTERS = 100  # fewer letters than this on the sampled pages: treat as a scan
MIN_DIACRITIC_RATIO = 0.05  # real Vietnamese text is ~0.2; garbage layers are ~0

RENDER_DPI = 200
MIN_TABLE_LETTERS = 50  # tables with less text (numbers only) are not judged
BW_THRESHOLD = 160  # grey level above which a pixel becomes white
MIN_GARBLED_LETTERS = 200  # pages with less text are not judged (stamps, signatures, blank forms)
MIN_COMMON_WORD_RATIO = 0.04  # share of tokens that are frequent Vietnamese words; real text ~0.2, rotated OCR ~0

# Frequent words in Vietnamese legal and banking text. OCR of a rotated page yields
# diacritics too, but almost never these words.
_VI_COMMON = frozenset(
    "của và các có không là được cho với trong tại về theo này khi đối người một những hoặc "
    "quy định điều khoản thông tư số năm tháng ngày ngân hàng nhà nước tổ chức tín dụng "
    "thực hiện trường hợp dịch vụ thanh toán tài phí tiền lao động đồng sau đây phải".split()
)
_TOKEN = re.compile(r"\w+")

_VI_DIACRITICS = re.compile(
    "[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", re.IGNORECASE
)


def needs_full_page_ocr(text_layer: str) -> bool:
    """True when the PDF's own text cannot be trusted for Vietnamese content."""
    if sum(c.isalpha() for c in text_layer) < MIN_LETTERS:
        return True
    return _diacritic_ratio(text_layer) < MIN_DIACRITIC_RATIO


def _diacritic_ratio(text: str) -> float:
    letters = sum(c.isalpha() for c in text)
    return len(_VI_DIACRITICS.findall(text)) / letters if letters else 0.0


def common_word_ratio(text: str) -> float:
    tokens = _TOKEN.findall(text.lower())
    return sum(t in _VI_COMMON for t in tokens) / len(tokens) if tokens else 0.0


def _letters(page: dict) -> int:
    return sum(c.isalpha() for c in page["text"] + "\n".join(page["tables"]))


def looks_garbled(page: dict) -> bool:
    """True for an OCR'd page with plenty of characters but almost no real Vietnamese words."""
    if _letters(page) < MIN_GARBLED_LETTERS:
        return False
    return common_word_ratio(page["text"] + "\n".join(page["tables"])) < MIN_COMMON_WORD_RATIO


def _text_layer(path: str) -> str:
    import pypdfium2

    pdf = pypdfium2.PdfDocument(path)
    try:
        return " ".join(pdf[i].get_textpage().get_text_range() for i in range(min(SAMPLE_PAGES, len(pdf))))
    finally:
        pdf.close()


def _ocr_only_backend():
    from docling.backend.docling_parse_backend import ThreadedDoclingParseDocumentBackend

    class OcrOnlyBackend(ThreadedDoclingParseDocumentBackend):
        """Pages whose text-layer lookup is empty, so only OCR text reaches tables."""

        def iter_pages(self):
            for page in super().iter_pages():
                page.get_text_in_rect = lambda bbox: ""
                yield page

    return OcrOnlyBackend


@lru_cache(maxsize=2)
def _converter(full_page_ocr: bool) -> DocumentConverter:
    # Imported lazily: docling pulls in torch, which the API process must not load.
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import OcrMode, PdfPipelineOptions, TesseractCliOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    ocr = TesseractCliOcrOptions(lang=OCR_LANGS, mode=OcrMode.FULL_PAGE if full_page_ocr else OcrMode.DEFAULT)
    options = PdfPipelineOptions(do_ocr=True, do_table_structure=True, ocr_options=ocr)
    fmt = PdfFormatOption(pipeline_options=options)
    if full_page_ocr:
        fmt = PdfFormatOption(pipeline_options=options, backend=_ocr_only_backend())
    return DocumentConverter(format_options={InputFormat.PDF: fmt})


def parse(path: str) -> list[dict]:
    source = Path(path).name
    if not needs_full_page_ocr(_text_layer(path)):
        return doc_to_pages(_converter(False).convert(path).document, source)
    with tempfile.TemporaryDirectory() as tmp:
        original = _ocr_pages(path, source, Path(tmp))
        images = _ocr_pages(str(_image_only_pdf(path, Path(tmp) / "pages.pdf")), source, Path(tmp))
        # The original keeps table structure best; the bi-level image copy has no
        # garbage text layer and OCRs some rotated pages better. Use the copy only
        # where the original page, or one of its tables, reads as garbage.
        pairs = zip(original, images, strict=True)
        best = [b if _garbage_in(a) and _score(b) > _score(a) else a for a, b in pairs]
        return [_repair(path, p, Path(tmp)) for p in best]


def _score(page: dict) -> float:
    return common_word_ratio(page["text"] + "\n" + "\n".join(page["tables"]))


def _garbage_in(page: dict) -> bool:
    return looks_garbled(page) or any(
        sum(c.isalpha() for c in t) >= MIN_TABLE_LETTERS
        and (common_word_ratio(t) < MIN_COMMON_WORD_RATIO or _diacritic_ratio(t) < MIN_DIACRITIC_RATIO)
        for t in page["tables"]
    )


def _ocr_pages(path: str, source: str, tmp: Path) -> list[dict]:
    doc = _converter(True).convert(path).document
    pages = doc_to_pages(doc, source)
    for page in pages:
        extra = _ocr_empty_tables(path, doc, page["page"], tmp)
        page["text"] = "\n\n".join(t for t in [page["text"], *extra] if t)
    return pages


def _tesseract(img, file: Path, psm: int | None = None) -> str:
    img.save(file)
    cmd = ["tesseract", str(file), "-", "-l", "+".join(OCR_LANGS)] + (["--psm", str(psm)] if psm else [])
    return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout.strip()


def _ocr_empty_tables(path: str, doc: DoclingDocument, page_no: int, tmp: Path) -> list[str]:
    """Text of tables on the page that TableFormer found but returned without cells."""
    from docling_core.types.doc import TableItem

    boxes = [
        item.prov[0].bbox.to_top_left_origin(page_height=doc.pages[page_no].size.height)
        for item, _level in doc.iterate_items(page_no=page_no)
        if isinstance(item, TableItem) and item.prov and not item.data.table_cells
    ]
    if not boxes:
        return []
    img, k = _render(path, page_no), RENDER_DPI / 72
    texts = [_tesseract(img.crop((b.l * k, b.t * k, b.r * k, b.b * k)), tmp / f"t{page_no}-{i}.png", psm=4)
             for i, b in enumerate(boxes)]
    return [t for t in texts if t]


def _repair(path: str, page: dict, tmp: Path) -> dict:
    if looks_garbled(page):
        return _best_rotation(path, page, tmp)
    if _letters(page) < MIN_GARBLED_LETTERS:
        text = _tesseract(_render(path, page["page"]), tmp / f"plain{page['page']}.png")
        if sum(c.isalpha() for c in text) > _letters(page):
            return {**page, "text": text}
    return page


def _render(path: str, page_no: int):
    import pypdfium2

    pdf = pypdfium2.PdfDocument(path)
    try:
        img = pdf[page_no - 1].render(scale=RENDER_DPI / 72).to_pil().convert("L")
    finally:
        pdf.close()
    return img


def _best_rotation(path: str, page: dict, tmp: Path) -> dict:
    best, best_score = page, common_word_ratio(page["text"] + "\n".join(page["tables"]))
    for rotate in (90, 180, 270):
        one = _rotated_page_pdf(path, page["page"], rotate, tmp / f"rot{page['page']}-{rotate}.pdf")
        cand = doc_to_pages(_converter(True).convert(str(one)).document, page["source"])[0]
        score = common_word_ratio(cand["text"] + "\n".join(cand["tables"]))
        if score > best_score:
            best, best_score = {**cand, "page": page["page"]}, score
    return best


def _image_only_pdf(path: str, out: Path) -> Path:
    """Same pages as lossless black-and-white images, without the text layer.

    Bi-level images are stored without JPEG; JPEG artifacts made TableFormer return tables without cells.
    """
    import pypdfium2

    src = pypdfium2.PdfDocument(path)
    n = len(src)
    src.close()
    merged = pypdfium2.PdfDocument.new()
    for no in range(1, n + 1):
        one = out.with_name(f"p{no}.pdf")
        _render(path, no).point(lambda v: 255 if v > BW_THRESHOLD else 0, "1").save(
            one, "PDF", resolution=RENDER_DPI
        )
        page_pdf = pypdfium2.PdfDocument(str(one))
        merged.import_pages(page_pdf)
        page_pdf.close()
        one.unlink()
    merged.save(str(out))
    merged.close()
    return out


def _rotated_page_pdf(path: str, page_no: int, rotate: int, out: Path) -> Path:
    import pypdfium2

    src, one = pypdfium2.PdfDocument(path), pypdfium2.PdfDocument.new()
    try:
        one.import_pages(src, [page_no - 1])
        one[0].set_rotation((one[0].get_rotation() + rotate) % 360)
        one.save(str(out))
    finally:
        one.close()
        src.close()
    return out


def doc_to_pages(doc: DoclingDocument, source: str) -> list[dict]:
    from docling_core.types.doc import ListItem, SectionHeaderItem, TableItem, TextItem, TitleItem

    pages = {no: {"source": source, "page": no, "text": [], "tables": []} for no in sorted(doc.pages)}
    for item, _level in doc.iterate_items(traverse_pictures=True):
        if not getattr(item, "prov", None):
            continue
        page = pages.setdefault(
            item.prov[0].page_no, {"source": source, "page": item.prov[0].page_no, "text": [], "tables": []}
        )
        if isinstance(item, TableItem):
            md = item.export_to_markdown(doc=doc).strip()
            if md:
                page["tables"].append(md)
        elif isinstance(item, TextItem) and item.text.strip():
            if isinstance(item, TitleItem | SectionHeaderItem):
                page["text"].append(f"## {item.text.strip()}")
            elif isinstance(item, ListItem):
                page["text"].append(f"- {item.text.strip()}")
            else:
                page["text"].append(item.text.strip())
    return [{**p, "text": "\n\n".join(p["text"])} for _, p in sorted(pages.items())]
