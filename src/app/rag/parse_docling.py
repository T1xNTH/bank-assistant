"""Parse PDFs with docling (tables as Markdown, OCR) into pages.

Owner: A — Epic E-003. See docs/00-project/product-plan.md.

Each page is ``{"source", "page", "text", "tables"}``: ``page`` counts from 1,
``text`` is the page's non-table text in reading order (headings as ``## ``,
list items as ``- ``), ``tables`` holds one Markdown table per table on the page.
Every page of the PDF is returned, including empty ones.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docling.document_converter import DocumentConverter
    from docling_core.types.doc import DoclingDocument

OCR_LANGS = ["vi", "en"]


@lru_cache(maxsize=1)
def _converter() -> DocumentConverter:
    # Imported lazily: docling pulls in torch, which the API process must not load.
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True,
        ocr_options=EasyOcrOptions(lang=OCR_LANGS),
    )
    return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})


def parse(path: str) -> list[dict]:
    doc = _converter().convert(path).document
    return doc_to_pages(doc, source=Path(path).name)


def doc_to_pages(doc: DoclingDocument, source: str) -> list[dict]:
    from docling_core.types.doc import ListItem, SectionHeaderItem, TableItem, TextItem, TitleItem

    pages = {no: {"source": source, "page": no, "text": [], "tables": []} for no in sorted(doc.pages)}
    for item, _level in doc.iterate_items():
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
