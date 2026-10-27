"""doc_to_pages on a hand-built DoclingDocument: no models, runs in CI."""

from docling_core.types.doc import (
    BoundingBox,
    DocItemLabel,
    DoclingDocument,
    ProvenanceItem,
    Size,
    TableCell,
    TableData,
)

from app.rag.parse_docling import doc_to_pages
from tests.pdf_fixtures import FEE_ROWS


def _prov(page: int, text: str = "") -> ProvenanceItem:
    return ProvenanceItem(page_no=page, bbox=BoundingBox(l=0, t=0, r=1, b=1), charspan=(0, len(text)))


def _fee_table() -> TableData:
    cells = [
        TableCell(
            text=text,
            start_row_offset_idx=r,
            end_row_offset_idx=r + 1,
            start_col_offset_idx=c,
            end_col_offset_idx=c + 1,
            column_header=r == 0,
        )
        for r, row in enumerate(FEE_ROWS)
        for c, text in enumerate(row)
    ]
    return TableData(num_rows=len(FEE_ROWS), num_cols=len(FEE_ROWS[0]), table_cells=cells)


def _fee_schedule() -> DoclingDocument:
    doc = DoclingDocument(name="bieu-phi")
    for no in (1, 2, 3):
        doc.add_page(page_no=no, size=Size(width=595, height=842))
    doc.add_heading("Biểu phí dịch vụ thẻ", prov=_prov(1))
    doc.add_text(label=DocItemLabel.TEXT, text="Áp dụng từ 01/01/2026.", prov=_prov(1))
    doc.add_table(data=_fee_table(), prov=_prov(1))
    doc.add_list_item("Phí đã gồm VAT", prov=_prov(3), parent=doc.add_list_group())
    doc.add_text(label=DocItemLabel.TEXT, text="   ", prov=_prov(3))
    return doc


def test_fee_table_becomes_markdown_rows():
    page = doc_to_pages(_fee_schedule(), source="bieu-phi.pdf")[0]

    assert len(page["tables"]) == 1
    lines = page["tables"][0].splitlines()
    assert len(lines) == len(FEE_ROWS) + 1  # header + separator + data rows
    assert set(lines[1]) <= {"|", "-", ":", " "}
    for line, row in zip([lines[0], *lines[2:]], FEE_ROWS, strict=True):
        assert [cell.strip() for cell in line.strip("|").split("|")] == list(row)


def test_pages_keep_source_page_and_reading_order():
    pages = doc_to_pages(_fee_schedule(), source="bieu-phi.pdf")

    assert [(p["source"], p["page"]) for p in pages] == [("bieu-phi.pdf", n) for n in (1, 2, 3)]
    assert pages[0]["text"] == "## Biểu phí dịch vụ thẻ\n\nÁp dụng từ 01/01/2026."
    assert "Rut tien" not in pages[0]["text"]  # table content only in tables
    assert pages[1] == {"source": "bieu-phi.pdf", "page": 2, "text": "", "tables": []}
    assert pages[2]["text"] == "- Phí đã gồm VAT"
