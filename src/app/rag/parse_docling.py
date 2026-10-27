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
Vietnamese diacritics), is OCR'd page by page instead. Its pages are first
rendered to an image-only PDF, so docling cannot fall back to the garbage text
layer (it does for table cells without an OCR match). A page whose OCR output
has almost no common Vietnamese words was likely scanned rotated; it is retried
at 90/180/270 degrees and the most readable orientation is kept. A page that
comes back nearly empty (e.g. TableFormer found a table but no cells) falls back
to plain Tesseract text of the page image when that reads more.
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
    letters = sum(c.isalpha() for c in text_layer)
    if letters < MIN_LETTERS:
        return True
    return len(_VI_DIACRITICS.findall(text_layer)) / letters < MIN_DIACRITIC_RATIO


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


@lru_cache(maxsize=2)
def _converter(full_page_ocr: bool) -> DocumentConverter:
    # Imported lazily: docling pulls in torch, which the API process must not load.
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import OcrMode, PdfPipelineOptions, TesseractCliOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    ocr = TesseractCliOcrOptions(lang=OCR_LANGS, mode=OcrMode.FULL_PAGE if full_page_ocr else OcrMode.DEFAULT)
    options = PdfPipelineOptions(do_ocr=True, do_table_structure=True, ocr_options=ocr)
    return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})


def parse(path: str) -> list[dict]:
    source = Path(path).name
    if not needs_full_page_ocr(_text_layer(path)):
        return doc_to_pages(_converter(False).convert(path).document, source)
    with tempfile.TemporaryDirectory() as tmp:
        images = _image_only_pdf(path, Path(tmp) / "pages.pdf")
        pages = doc_to_pages(_converter(True).convert(str(images)).document, source)
        return [_repair(path, p, Path(tmp)) for p in pages]


def _repair(path: str, page: dict, tmp: Path) -> dict:
    if looks_garbled(page):
        return _best_rotation(path, page, tmp)
    if _letters(page) < MIN_GARBLED_LETTERS:
        img = tmp / f"plain{page['page']}.png"
        _render(path, page["page"]).save(img)
        text = subprocess.run(
            ["tesseract", str(img), "-", "-l", "+".join(OCR_LANGS)], capture_output=True, text=True, check=False
        ).stdout.strip()
        if sum(c.isalpha() for c in text) > _letters(page):
            return {**page, "text": text}
    return page


def _render(path: str, page_no: int, rotate: int = 0):
    import pypdfium2

    pdf = pypdfium2.PdfDocument(path)
    try:
        img = pdf[page_no - 1].render(scale=RENDER_DPI / 72).to_pil().convert("L")
    finally:
        pdf.close()
    return img.rotate(-rotate, expand=True) if rotate else img


def _image_only_pdf(path: str, out: Path) -> Path:
    """Same pages as images only; one page in memory at a time."""
    import pypdfium2

    src = pypdfium2.PdfDocument(path)
    n = len(src)
    src.close()
    merged = pypdfium2.PdfDocument.new()
    for no in range(1, n + 1):
        one = out.with_name(f"p{no}.pdf")
        _render(path, no).save(one, "PDF", resolution=RENDER_DPI)
        page_pdf = pypdfium2.PdfDocument(str(one))
        merged.import_pages(page_pdf)
        page_pdf.close()
        one.unlink()
    merged.save(str(out))
    merged.close()
    return out


def _best_rotation(path: str, page: dict, tmp: Path) -> dict:
    best, best_score = page, common_word_ratio(page["text"] + "\n".join(page["tables"]))
    for rotate in (90, 180, 270):
        one = tmp / f"rot{page['page']}-{rotate}.pdf"
        _render(path, page["page"], rotate).save(one, "PDF", resolution=RENDER_DPI)
        cand = doc_to_pages(_converter(True).convert(str(one)).document, page["source"])[0]
        score = common_word_ratio(cand["text"] + "\n".join(cand["tables"]))
        if score > best_score:
            best, best_score = {**cand, "page": page["page"]}, score
    return best


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
