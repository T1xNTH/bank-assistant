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

A conversion docling reports as failed, or that leaves a page of the PDF without
any result, raises ``ParseError`` rather than silently returning fewer pages.
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
MIN_KEPT_FIGURES = 0.5  # a table whose figures the image copy mostly lost is kept from the original
MIN_WORD_TOKENS = 0.35  # garbage-layer tables are ~0.45+ words (no accents); OCR noise of a stamp or scribble ~0.17
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
_WORD = re.compile(r"[^\W\d_]{2,}")
_NUMBER = re.compile(r"[\d.,%/()-]+")
# Amounts, rates, dates (22.700.000, 0,5%, 4%, 2025); not the stray one- or two-digit noise of an OCR'd form grid.
_FIGURE = re.compile(r"\d+(?:[.,]\d+)+%?|\d+%|\d{3,}")

_VI_DIACRITICS = re.compile(
    "[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", re.IGNORECASE
)


class ParseError(RuntimeError):
    """Docling failed on the PDF, or some of its pages have no parse result."""


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


def _all_text(page: dict) -> str:
    return page["text"] + "\n" + "\n".join(page["tables"])


def _letters(page: dict) -> int:
    return sum(c.isalpha() for c in _all_text(page))


def looks_garbled(page: dict) -> bool:
    """True for an OCR'd page with plenty of characters but almost no real Vietnamese words."""
    if _letters(page) < MIN_GARBLED_LETTERS:
        return False
    return common_word_ratio(_all_text(page)) < MIN_COMMON_WORD_RATIO


def _page_count(path: str) -> int:
    import pypdfium2

    pdf = pypdfium2.PdfDocument(path)
    try:
        return len(pdf)
    finally:
        pdf.close()


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
        return _require_all_pages(doc_to_pages(_convert(path, False), source), _page_count(path), source)
    with tempfile.TemporaryDirectory() as tmp:
        original = _ocr_pages(path, source, Path(tmp))
        images = _ocr_pages(str(_image_only_pdf(path, Path(tmp) / "pages.pdf")), source, Path(tmp))
        # The original keeps table structure best; the bi-level image copy has no
        # garbage text layer and OCRs some rotated pages better. Use the copy only
        # where the original page, or one of its tables, reads as garbage, keeping
        # any original table whose figures the copy lost.
        pages = _require_all_pages(choose_pages(original, images), _page_count(path), source)
        return [_repair(path, p, Path(tmp)) for p in pages]


def _convert(path: str, full_page_ocr: bool) -> DoclingDocument:
    result = _converter(full_page_ocr).convert(path)
    # PARTIAL_SUCCESS drops the pages that failed; _require_all_pages reports any still missing.
    if result.status.value not in ("success", "partial_success"):
        errors = "; ".join(e.error_message for e in result.errors)[:500]
        raise ParseError(f"{Path(path).name}: docling {result.status.value}: {errors}")
    return result.document


def _require_all_pages(pages: list[dict], page_count: int, source: str) -> list[dict]:
    missing = sorted(set(range(1, page_count + 1)) - {p["page"] for p in pages})
    if missing:
        raise ParseError(f"{source}: no parse result for pages {missing}")
    return pages


def choose_pages(original: list[dict], images: list[dict]) -> list[dict]:
    """Per page number, the image-copy result where the original reads as garbage and the copy reads better.

    A page only one of the two passes produced is taken from that pass.
    """
    orig = {p["page"]: p for p in original}
    copy = {p["page"]: p for p in images}
    chosen = []
    for no in sorted(orig.keys() | copy.keys()):
        p, c = orig.get(no), copy.get(no)
        if p is None or c is None:
            chosen.append(p or c)
        elif _garbage_in(p) and _score(c) > _score(p):
            chosen.append(_with_lost_tables(p, c))
        else:
            chosen.append(p)
    return chosen


def _score(page: dict) -> float:
    return common_word_ratio(_all_text(page))


def _figures(text: str) -> set[str]:
    return {re.sub(r"[.,]", "", f) for f in _FIGURE.findall(text)}


def _reads_as_words(table: str) -> bool:
    """True for a table of (possibly unaccented) words; False for OCR noise whose stray digits look like figures."""
    tokens = [t for t in re.findall(r"[^\s|]+", table) if not _NUMBER.fullmatch(t)]
    return sum(bool(_WORD.fullmatch(t.strip(".,:;()"))) for t in tokens) >= MIN_WORD_TOKENS * max(len(tokens), 1)


def _with_lost_tables(original: dict, copy: dict) -> dict:
    """The copy, plus any table of the readable original whose figures the copy lost.

    Dropping a garbage-text table raises the copy's score, so a better score alone cannot
    tell a cleaner read from lost amounts and rates. A table is kept from the original
    when the copy has fewer than half of its figures anywhere on the page; its words may
    be garbage, but its figures came from the text layer. A garbled original has nothing
    readable to keep, and a table without figures (e.g. the empty grid of a blank form)
    or without words (OCR noise) is not content.
    """
    if looks_garbled(original):
        return copy
    have = _figures(_all_text(copy))
    lost = [
        t
        for t in original["tables"]
        if (figs := _figures(t)) and len(figs & have) < MIN_KEPT_FIGURES * len(figs) and _reads_as_words(t)
    ]
    return {**copy, "tables": copy["tables"] + lost} if lost else copy


def _garbage_in(page: dict) -> bool:
    return looks_garbled(page) or any(
        sum(c.isalpha() for c in t) >= MIN_TABLE_LETTERS
        and (common_word_ratio(t) < MIN_COMMON_WORD_RATIO or _diacritic_ratio(t) < MIN_DIACRITIC_RATIO)
        for t in page["tables"]
    )


def _ocr_pages(path: str, source: str, tmp: Path) -> list[dict]:
    doc = _convert(path, True)
    pages = doc_to_pages(doc, source)
    for page in pages:
        extra = _ocr_empty_tables(path, doc, page["page"], tmp)
        page["text"] = "\n\n".join(t for t in [page["text"], *extra] if t)
    return pages


def _tesseract(img, file: Path, psm: int | None = None) -> str:
    img.save(file)
    cmd = ["tesseract", str(file), "-", "-l", "+".join(OCR_LANGS)] + (["--psm", str(psm)] if psm else [])
    # Tesseract writes UTF-8 whatever the locale (Windows pipes default to cp1252).
    done = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", check=False)
    if done.returncode != 0:
        raise RuntimeError(f"tesseract failed ({done.returncode}): {done.stderr.strip()[-500:]}")
    return done.stdout.strip()


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
            return {**page, "text": text, "tables": []}  # the page OCR already includes any table text
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
    best, best_score = page, common_word_ratio(_all_text(page))
    for rotate in (90, 180, 270):
        one = _rotated_page_pdf(path, page["page"], rotate, tmp / f"rot{page['page']}-{rotate}.pdf")
        cands = doc_to_pages(_convert(str(one), True), page["source"])
        if not cands:
            continue
        cand = cands[0]
        score = common_word_ratio(_all_text(cand))
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
