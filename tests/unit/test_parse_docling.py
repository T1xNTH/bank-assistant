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

from app.rag.parse_docling import _text_layer, common_word_ratio, doc_to_pages, looks_garbled, needs_full_page_ocr
from tests.pdf_fixtures import FEE_ROWS, write_fee_table_pdf, write_scanned_pdf


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


# First lines of the text layer of a real scanned NHNN circular (scanner garbage).
GARBAGE_LAYER = (
    "NcANEANcNEA NrIOc ceNcHoAxAEOr cr0NctrAvr$r NAM vET NAM Dfc I{p - Ts do - Epnh phic "
    "sdvl,f /2026ITT-NHNN HdNAi, ngayl?.Lthrng I *m zozo TE6NGTtI Sfra d6i, b5 sung nQt s6 "
    "ili6u cte Th6ng tu s6 22/2019/IT-NHYN quy dinh crlc gi6i hp, ti l$ bto tttm an toln"
)
GOOD_LAYER = (
    "Biểu phí áp dụng cho nghiệp vụ thanh toán thẻ quốc tế. Rút tiền mặt tại ATM của ngân hàng: "
    "thẻ do ngân hàng khác phát hành chịu phí 4%, tối thiểu 80.000 đồng, thu tự động."
)


def test_full_page_ocr_only_for_scans_and_garbage_text_layers():
    assert needs_full_page_ocr(GARBAGE_LAYER)
    assert needs_full_page_ocr("")
    assert needs_full_page_ocr("  12  ")
    assert not needs_full_page_ocr(GOOD_LAYER)


def test_text_layer_check_on_generated_pdfs(tmp_path):
    assert not needs_full_page_ocr(_text_layer(str(write_fee_table_pdf(tmp_path / "fee.pdf"))))
    assert needs_full_page_ocr(_text_layer(str(write_scanned_pdf(tmp_path / "scan.pdf"))))


# OCR of a page scanned upside down (real output from a NHNN consolidated circular).
UPSIDE_DOWN_OCR = (
    "## I 3uonq2 ## ĐNñH2 HNỈG Af1Ò ## 8uủp dự 8uôn) top gA q13 nạtp A trẻqJ '¡ nạtq "
    "- '8uyu (2p lọA tọp (8ưäp un 2nd2 ọì gị tỏổ Ấẹp nes) rẹoẩu 2onu 8ượu uy8u quyqu t2 "
    "'8ưäp uI 2nd2 Ọi en2 ÁeA o2 8uộp yẻou ạA quịp Ánb Áẹu m 8uoq[ '| '8ưủp un anu2 1 9p2 pn[8 "
    "ÁpA oqo 8uộp tẻo tọA iọp qurq2 nạtp 8uou Áeu nị 8uoq[ '£ ## 19} (31 IE12) '£ nạtq"
)
UPRIGHT_OCR = (
    "## Chương I ## QUY ĐỊNH CHUNG ## Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng "
    "- Thông tư này quy định về hoạt động cho vay của tổ chức tín dụng, chi nhánh ngân hàng "
    "nước ngoài đối với khách hàng là pháp nhân, cá nhân. Hoạt động cho vay theo quy định "
    "của Thông tư này được thực hiện theo nguyên tắc thỏa thuận giữa các bên."
)


def test_rotated_ocr_is_flagged_but_real_text_is_not():
    assert common_word_ratio(UPSIDE_DOWN_OCR) < common_word_ratio(UPRIGHT_OCR)
    assert looks_garbled({"text": UPSIDE_DOWN_OCR * 2, "tables": []})  # a full page holds more of it
    assert not looks_garbled({"text": UPRIGHT_OCR, "tables": []})
    assert not looks_garbled({"text": "Ký tên, đóng dấu", "tables": []})  # too little text to judge
