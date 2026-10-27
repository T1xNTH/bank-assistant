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
Vietnamese diacritics), is OCR'd page by page instead.
"""

from __future__ import annotations

import re
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

_VI_DIACRITICS = re.compile(
    "[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", re.IGNORECASE
)


def needs_full_page_ocr(text_layer: str) -> bool:
    """True when the PDF's own text cannot be trusted for Vietnamese content."""
    letters = sum(c.isalpha() for c in text_layer)
    if letters < MIN_LETTERS:
        return True
    return len(_VI_DIACRITICS.findall(text_layer)) / letters < MIN_DIACRITIC_RATIO


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
    doc = _converter(needs_full_page_ocr(_text_layer(path))).convert(path).document
    return doc_to_pages(doc, source=Path(path).name)


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
