"""chunk_pages: structure-aware text chunking (CR-009) and table chunking on hand-made pages."""

import json
from pathlib import Path

import pytest

from app.rag.chunk import chunk_pages

SENTENCE = "Người sử dụng lao động phải trả lương không thấp hơn mức lương tối thiểu vùng."
HEADER = "| Vùng | Mức lương tối thiểu tháng (đồng) | Mức lương tối thiểu giờ (đồng) |\n|---|---|---|"
ROWS = [f"| Vùng {i} | {5_310_000 - i * 500_000:,} | {25_500 - i * 2_000:,} |".replace(",", ".") for i in range(1, 41)]


def _page(no, text="", tables=()):
    return {"source": "nd293.pdf", "page": no, "text": text, "tables": list(tables)}


def test_long_text_respects_size_and_overlaps_at_word_boundaries():
    chunks = chunk_pages([_page(1, " ".join([SENTENCE] * 30))], size=300, overlap=60)

    assert len(chunks) > 1
    assert all(len(c["text"]) <= 300 for c in chunks)
    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        first_line = nxt["text"].split("\n")[0]
        assert 0 < len(first_line) <= 60 and prev["text"].endswith(first_line)  # overlap is the previous tail
    words = set(SENTENCE.replace(".", "").split())
    assert all(w.strip(".") in words for c in chunks for w in c["text"].split())  # no word was cut


def test_paragraphs_are_kept_together_when_they_fit():
    text = "## Điều 3. Mức lương tối thiểu\n\n- Vùng I: 5.310.000 đồng/tháng.\n\n- Vùng II: 4.730.000 đồng/tháng."

    [chunk] = chunk_pages([_page(2, text)], size=800, overlap=100)

    lines = ["Điều 3. Mức lương tối thiểu", "- Vùng I: 5.310.000 đồng/tháng.", "- Vùng II: 4.730.000 đồng/tháng."]
    assert chunk["text"] == "\n".join(lines)  # the heading leads, paragraphs one per line


def test_small_table_is_one_chunk():
    table = "\n".join([HEADER, *ROWS[:3]])

    chunks = chunk_pages([_page(1, tables=[table])])

    assert [c["text"] for c in chunks] == [table]


def test_large_table_splits_between_rows_and_repeats_the_header():
    table = "\n".join([HEADER, *ROWS])

    chunks = chunk_pages([_page(1, tables=[table])], size=400, overlap=50)

    assert len(chunks) > 1
    seen = []
    for c in chunks:
        lines = c["text"].split("\n")
        assert "\n".join(lines[:2]) == HEADER  # every part is a readable table
        assert all(line in ROWS for line in lines[2:])  # rows are whole, never cut
        assert len(c["text"]) <= 400
        seen += lines[2:]
    assert seen == ROWS  # every row once, in order, no overlap


def test_row_longer_than_size_stays_whole():
    long_row = "| Ghi chú | " + "x" * 500 + " |"
    table = "\n".join([HEADER, ROWS[0], long_row, ROWS[1]])

    chunks = chunk_pages([_page(1, tables=[table])], size=200, overlap=0)

    assert any(long_row in c["text"] for c in chunks)
    assert all(c["text"].startswith(HEADER) for c in chunks)


def test_metadata_and_chunk_index_run_across_pages():
    pages = [_page(1, SENTENCE), _page(2), _page(3, SENTENCE, ["\n".join([HEADER, ROWS[0]])])]

    chunks = chunk_pages(pages)

    # Text without headings is one section across the page break; it is cited from the page it starts on.
    assert [(c["source"], c["page"], c["chunk_index"]) for c in chunks] == [
        ("nd293.pdf", 1, 0),
        ("nd293.pdf", 3, 1),
    ]
    assert chunks[0]["text"] == f"{SENTENCE}\n{SENTENCE}"


@pytest.mark.parametrize(("size", "overlap"), [(0, 0), (100, 100), (100, -1)])
def test_rejects_bad_size_or_overlap(size, overlap):
    with pytest.raises(ValueError):
        chunk_pages([_page(1, SENTENCE)], size=size, overlap=overlap)


def test_table_alignment_padding_is_removed():
    padded = (
        "| Vùng           | Mức lương tối thiểu tháng   |\n"
        "|----------------|-----------------------------|\n"
        "| Vùng I         | 5.310.000                   |"
    )

    [chunk] = chunk_pages([_page(1, tables=[padded])])

    assert chunk["text"] == "| Vùng | Mức lương tối thiểu tháng |\n|---|---|\n| Vùng I | 5.310.000 |"


def test_full_stop_never_pushes_a_piece_over_size_or_leaves_an_empty_chunk():
    chunks = chunk_pages([_page(1, "aaaaaaaaaa. bbbb")], size=10, overlap=0)

    assert [c["text"] for c in chunks] == ["aaaaaaaaaa", "bbbb"]


@pytest.mark.parametrize("size", [50, 120, 300, 800])
def test_text_chunks_are_non_empty_and_within_size(size):
    text = "\n\n".join(
        f"## Điều {i}. Quy định chung\n- Khoản {i}: {SENTENCE} " + " ".join([SENTENCE] * (i % 7)) + "."
        for i in range(1, 40)
    )

    chunks = chunk_pages([_page(1, text)], size=size, overlap=size // 5)

    assert chunks and all(c["text"].strip() and len(c["text"]) <= size for c in chunks)


def test_data_row_of_dashes_is_not_taken_for_the_separator():
    table = "| Phí | Mức |\n|:----|----:|\n| ---   | 4%   |\n| Rút tiền | 1.100 |"

    [chunk] = chunk_pages([_page(1, tables=[table])])

    assert chunk["text"] == "| Phí | Mức |\n|---|---|\n| --- | 4% |\n| Rút tiền | 1.100 |"


def test_overlap_keeps_the_whole_tail_when_it_starts_on_a_word():
    words = " ".join(f"w{i:02d}" for i in range(40))  # every word is 3 chars + a space

    chunks = chunk_pages([_page(1, words)], size=40, overlap=8)

    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        assert nxt["text"].split("\n")[0] == prev["text"][-7:]  # "wNN wNN": the full 8-char overlap, whole words


def test_words_are_only_cut_when_longer_than_size():
    long_word = "x" * 25

    texts = [c["text"] for c in chunk_pages([_page(1, f"aaaaaaaaaa. bbbb {long_word}")], size=10, overlap=3)]

    assert "aaaaaaaaaa" in texts  # fits in size: kept whole although it leaves no room for overlap
    assert "".join(t for t in texts if set(t) == {"x"}) == long_word  # only the 25-char word is cut
    assert all(0 < len(t) <= 10 for t in texts)


@pytest.mark.parametrize("size", [800, 500, 300])
def test_single_row_table_over_size_is_kept_whole(size):
    # Docling represents a one-row table as header + separator, even when the
    # first row contains data rather than column labels.
    label = ("Transfer service conditions and applicable charges " * 20).strip()
    table = f"| {label} | 22.700.000 |\n|---|---|"

    [chunk] = chunk_pages([_page(3, tables=[table])], size=size, overlap=0)

    assert chunk == {"source": "nd293.pdf", "page": 3, "chunk_index": 0, "text": table}
    assert len(chunk["text"]) > size  # same deliberate exception as an oversized data row


@pytest.mark.parametrize(("size", "overlap"), [(500, 50), (300, 30), (100, 0)])
def test_real_single_row_page_is_not_lost_when_size_is_reduced(size, overlap):
    fixture = Path(__file__).parents[1] / "fixtures/chunk/52-nd-cp-page-56.json"
    page = json.loads(fixture.read_text(encoding="utf-8"))["page"]
    assert page["text"] == "" and len(page["tables"]) == 1

    [chunk] = chunk_pages([page], size=size, overlap=overlap)

    assert (chunk["source"], chunk["page"], chunk["chunk_index"]) == ("52-nd-cp.signed.pdf", 56, 0)
    assert "Phương án được một tổ chức" in chunk["text"]
    assert "Quyền và trách nhiệm" in chunk["text"]
    assert len(chunk["text"].splitlines()) == 2


def test_empty_table_still_produces_no_chunk():
    assert chunk_pages([_page(1, tables=[" \n\t"])]) == []


# --- CR-009: sections at headings, heading line on every chunk ---


def _texts(chunks):
    return [c["text"] for c in chunks]


def test_an_article_across_a_page_break_is_one_section_cited_from_its_first_page():
    pages = [
        _page(4, f"## Điều 5. Mức tham chiếu\n\n- {SENTENCE}"),
        _page(5, f"- {SENTENCE}\n\n## Điều 6. Đăng ký tham gia\n\n- Người lao động nộp tờ khai."),
    ]

    chunks = chunk_pages(pages)

    assert [(c["page"], c["text"]) for c in chunks] == [
        (4, f"Điều 5. Mức tham chiếu\n- {SENTENCE}\n- {SENTENCE}"),
        (5, "Điều 6. Đăng ký tham gia\n- Người lao động nộp tờ khai."),
    ]


def test_every_chunk_of_a_long_article_starts_with_its_heading_and_fits():
    body = "\n\n".join(f"- Khoản {i}: {SENTENCE}" for i in range(1, 30))

    chunks = chunk_pages([_page(1, f"## Chương II QUY ĐỊNH CỤ THỂ\n\n## Điều 7. Tiền lương\n\n{body}")], 300, 60)

    assert len(chunks) > 1
    assert all(c["text"].startswith("Chương II QUY ĐỊNH CỤ THỂ › Điều 7. Tiền lương\n") for c in chunks)
    assert all(len(c["text"]) <= 300 for c in chunks)
    joined = "\n".join(c["text"] for c in chunks)
    assert all(f"Khoản {i}:" in joined for i in range(1, 30))  # nothing lost


def test_overlap_stays_inside_the_section_and_page_follows_the_first_new_line():
    pages = [_page(1, "## Điều 1. A\n\n" + " ".join([SENTENCE] * 5)), _page(2, " ".join([SENTENCE] * 5))]

    chunks = chunk_pages(pages, size=300, overlap=60)

    assert {c["page"] for c in chunks} == {1, 2}
    for c in chunks:
        lines = c["text"].split("\n")
        assert lines[0] == "Điều 1. A" and len(c["text"]) <= 300


def test_a_new_chapter_clears_the_article_and_a_section_can_start_without_a_chapter():
    text = (
        "## Điều 1. Phạm vi\n\nNội dung một.\n\n## Chương II MỤC TIÊU\n\nGiới thiệu.\n\n"
        "## Mục 1 Chung\n\n## Điều 2. Đối tượng\n\nNội dung hai."
    )

    assert _texts(chunk_pages([_page(1, text)])) == [
        "Điều 1. Phạm vi\nNội dung một.",
        "Chương II MỤC TIÊU\nGiới thiệu.",
        "Chương II MỤC TIÊU › Mục 1 Chung › Điều 2. Đối tượng\nNội dung hai.",
    ]


def test_ocr_headings_without_markdown_markers_are_recognised():
    text = (
        "Điều 4. Bản sao các giấy tờ\n\nBản sao được cơ quan bảo hiểm xã hội xác nhận.\n\n"
        "Điều 5: Mức tham chiếu\n\nBằng mức lương cơ sở."
    )

    assert _texts(chunk_pages([_page(1, text)])) == [
        "Điều 4. Bản sao các giấy tờ\nBản sao được cơ quan bảo hiểm xã hội xác nhận.",
        "Điều 5: Mức tham chiếu\nBằng mức lương cơ sở.",
    ]


def test_references_to_articles_inside_a_sentence_are_not_headings():
    body = ["Điều 31 của Luật Bảo hiểm xã hội quy định tiền lương đóng.", "Chương này áp dụng chung."]

    [chunk] = chunk_pages([_page(1, "## Điều 7. Tiền lương\n\n" + "\n\n".join(body))])

    assert chunk["text"] == "\n".join(["Điều 7. Tiền lương", *body])


def test_preamble_has_no_heading_and_boilerplate_headings_of_a_legal_text_stay_body():
    text = (
        "CHÍNH PHỦ\n\n## CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM Độc lập - Tự do - Hạnh phúc\n\n## NGHỊ ĐỊNH\n\n"
        "Căn cứ Bộ luật Lao động;\n\n## Điều 1. Phạm vi điều chỉnh\n\nNghị định này quy định mức lương tối thiểu."
    )

    first, second = _texts(chunk_pages([_page(1, text)]))

    assert first.startswith("CHÍNH PHỦ\n") and "\nNGHỊ ĐỊNH\n" in first and "Căn cứ Bộ luật Lao động;" in first
    assert "##" not in first  # docling's marker is dropped from lines that are not section headings
    assert second == "Điều 1. Phạm vi điều chỉnh\nNghị định này quy định mức lương tối thiểu."


def test_a_document_without_legal_headings_uses_docling_headings():
    pages = [
        _page(1, "## BIỂU PHÍ DỊCH VỤ TÀI KHOẢN\n\n(Từ 01/08/2025)", ["\n".join([HEADER, ROWS[0]])]),
        _page(2, "## Phụ lục 1\n\nGhi chú.\n\n## THẺ GHI NỢ\n\nPhí phát hành thẻ."),
    ]

    assert _texts(chunk_pages(pages)) == [
        "BIỂU PHÍ DỊCH VỤ TÀI KHOẢN\n(Từ 01/08/2025)",
        f"BIỂU PHÍ DỊCH VỤ TÀI KHOẢN\n{HEADER}\n{ROWS[0]}",
        "Phụ lục 1\nGhi chú.",
        "THẺ GHI NỢ\nPhí phát hành thẻ.",
    ]


def test_tables_get_the_heading_in_effect_at_the_end_of_their_page_and_stay_within_size():
    table = "\n".join([HEADER, *ROWS])
    chunks = chunk_pages([_page(2, "## Điều 3. Mức lương tối thiểu\n\nTheo vùng như sau:", [table])], size=400)

    tables = [c for c in chunks if HEADER in c["text"]]
    assert len(tables) > 1
    assert all(c["text"].startswith(f"Điều 3. Mức lương tối thiểu\n{HEADER}\n") for c in tables)
    assert all(len(c["text"]) <= 400 for c in tables)
    assert [r for c in tables for r in c["text"].split("\n")[3:]] == ROWS


def test_a_long_heading_path_keeps_the_innermost_heading_within_a_quarter_of_size():
    chapter = "## Chương III " + "QUY ĐỊNH VỀ QUẢN LÝ " * 10
    article = "## Điều 12. " + "Trách nhiệm của tổ chức tín dụng " * 5

    first, chunk = chunk_pages([_page(1, f"{chapter}\n\n{article}\n\nNội dung.")], size=400)

    header = chunk["text"].split("\n")[0]
    assert len(header) <= 100 and header.startswith("Điều 12.") and header.endswith("…")
    assert chunk["text"].endswith("\nNội dung.")
    # Neither heading survives whole in a path, so each one's words start the text of a chunk.
    assert " ".join(chunk["text"].split("\n")[1:-1]) == article.removeprefix("## ").strip()
    assert " ".join(first["text"].split("\n")[1:]) == chapter.removeprefix("## ").strip()


def test_an_untitled_fee_schedule_takes_its_first_line_as_the_title_of_every_chunk():
    title = "Biểu phí thẻ Ghi nợ nội địa (doanh nghiệp)"
    pages = [
        _page(1, f"{title}\n\n(Hiệu lực từ ngày 22/4/2026)", ["\n".join([HEADER, ROWS[0]])]),
        _page(2, "Phí cấp lại PIN.", ["\n".join([HEADER, ROWS[1]])]),
        _page(3, "## Tệp đính kèm\n\nMẫu đề nghị."),
    ]

    assert _texts(chunk_pages(pages)) == [
        f"{title}\n(Hiệu lực từ ngày 22/4/2026)\nPhí cấp lại PIN.",
        f"{title}\n{HEADER}\n{ROWS[0]}",
        f"{title}\n{HEADER}\n{ROWS[1]}",
        f"{title} › Tệp đính kèm\nMẫu đề nghị.",
    ]


def test_a_document_of_plain_text_keeps_its_first_line_as_text_only():
    [chunk] = chunk_pages([_page(1, f"{SENTENCE}\n\nCâu thứ hai.")])

    assert chunk["text"] == f"{SENTENCE}\nCâu thứ hai."


def test_a_heading_without_text_is_kept_as_a_chunk_of_its_own():
    text = (
        "## Điều 8. Bãi bỏ Điều 32c và Điều 32h\n\n## Điều 9. Hiệu lực thi hành\n\nThông tư có hiệu lực từ 01/7/2026."
    )

    assert _texts(chunk_pages([_page(1, text)])) == [
        "Điều 8. Bãi bỏ Điều 32c và Điều 32h",
        "Điều 9. Hiệu lực thi hành\nThông tư có hiệu lực từ 01/7/2026.",
    ]


def test_a_heading_carried_by_the_next_path_is_not_repeated_on_its_own():
    text = "## Chương I NHỮNG QUY ĐỊNH CHUNG\n\n## Điều 1. Phạm vi điều chỉnh\n\nNghị định này quy định chi tiết."

    assert _texts(chunk_pages([_page(1, text)])) == [
        "Chương I NHỮNG QUY ĐỊNH CHUNG › Điều 1. Phạm vi điều chỉnh\nNghị định này quy định chi tiết."
    ]


def test_a_repealed_article_at_the_end_of_the_document_is_kept():
    text = "## Điều 5. Phạm vi\n\nNội dung.\n\n## Điều 6. (được bãi bỏ)"

    assert _texts(chunk_pages([_page(1, text)]))[-1] == "Điều 6. (được bãi bỏ)"


def test_consecutive_headings_of_a_fee_schedule_nest():
    text = (
        "## Dịch vụ ngân hàng điện tử\n\n## BIỂU PHÍ DỊCH VỤ ÁP DỤNG CHO KHÁCH HÀNG TỔ CHỨC\n\n"
        "## DỊCH VỤ NGÂN HÀNG ĐIỆN TỬ\n\nPhí duy trì.\n\n## Phí khác\n\nPhí in sao kê."
    )

    assert _texts(chunk_pages([_page(1, text)])) == [
        "Dịch vụ ngân hàng điện tử › BIỂU PHÍ DỊCH VỤ ÁP DỤNG CHO KHÁCH HÀNG TỔ CHỨC › DỊCH VỤ NGÂN HÀNG ĐIỆN TỬ\n"
        "Phí duy trì.",
        "Phí khác\nPhí in sao kê.",
    ]


@pytest.mark.parametrize(
    ("line", "path"),
    [
        ("Chương IH CHẾ ĐỘ BẢO HIỂM XÃ HỘI", "Chương IH CHẾ ĐỘ BẢO HIỂM XÃ HỘI"),
        ("Chương VỊ. - QUY ĐỊNH CHUYỂN TIẾP", "Chương VỊ. - QUY ĐỊNH CHUYỂN TIẾP"),
        ("Chương H QUẢN LÝ LAO ĐỘNG", "Chương H QUẢN LÝ LAO ĐỘNG"),
        ("Phụ lục EV", "Phụ lục EV"),
        ("## - Chương X - - NHỮNG QUY ĐỊNH RIÊNG", "Chương X - - NHỮNG QUY ĐỊNH RIÊNG"),
    ],
)
def test_ocr_misread_roman_numerals_still_open_a_chapter(line, path):
    text = f"## Chương I NHỮNG QUY ĐỊNH CHUNG\n\n## Điều 1. Phạm vi\n\nA.\n\n{line}\n\n## Điều 13. Mức đóng\n\nB."

    assert _texts(chunk_pages([_page(1, text)]))[-1] == f"{path} › Điều 13. Mức đóng\nB."


@pytest.mark.parametrize(
    "line",
    [
        "Phụ lục II ban hành kèm theo Nghị định số 135/2020/NĐ-CP",
        "Chương II của Nghị định này được sửa đổi",
        "Mục 1: Số dư tiền mặt tại thời điểm cuối ngày",
        "Mục 1.1: Tiền gửi không kỳ hạn",
        "- Chương II quy định về hợp đồng",  # a list item, not a marked heading
    ],
)
def test_body_lines_that_start_like_headings_stay_text(line):
    text = f"## Chương I NHỮNG QUY ĐỊNH CHUNG\n\n## Điều 1. Phạm vi\n\n{line}\n\nCâu tiếp theo."

    assert _texts(chunk_pages([_page(1, text)])) == [
        f"Chương I NHỮNG QUY ĐỊNH CHUNG › Điều 1. Phạm vi\n{line}\nCâu tiếp theo."
    ]


def test_a_short_first_line_without_tables_is_not_a_title():
    assert _texts(chunk_pages([_page(1, "Lưu ý chung\n\nNội dung.\n\n## Phí khác\n\nPhí in sao kê.")])) == [
        "Lưu ý chung\nNội dung.",
        "Phí khác\nPhí in sao kê.",
    ]


def test_a_first_line_longer_than_a_quarter_of_size_is_not_a_title():
    first = "Biểu phí áp dụng cho khách hàng " * 3  # > 200 // 4
    chunks = chunk_pages([_page(1, f"{first}\n\nNội dung.", ["\n".join([HEADER, ROWS[0]])])], size=200, overlap=0)

    assert chunks[-1]["text"] == f"{HEADER}\n{ROWS[0]}"


def test_the_national_motto_is_not_a_heading_of_a_fee_schedule():
    text = "## Biểu phí thẻ\n\nA.\n\n## CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n\nB."

    assert _texts(chunk_pages([_page(1, text)])) == ["Biểu phí thẻ\nA.\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nB."]


def test_a_marked_line_longer_than_300_characters_is_text():
    long = "Phí dịch vụ " * 30  # > 300 characters
    text = f"## Biểu phí thẻ\n\nA.\n\n## {long}"

    assert _texts(chunk_pages([_page(1, text)], size=2000)) == [f"Biểu phí thẻ\nA.\n{long.strip()}"]


def test_a_heading_closing_the_page_does_not_head_its_tables():
    pages = [_page(1, "## Biểu phí chuyển tiền\n\nPhí trong nước.\n\n## Tệp đính kèm", ["\n".join([HEADER, ROWS[0]])])]

    assert _texts(chunk_pages(pages)) == [
        "Biểu phí chuyển tiền\nPhí trong nước.",
        "Tệp đính kèm",
        f"Biểu phí chuyển tiền\n{HEADER}\n{ROWS[0]}",
    ]


# T-038: fee schedules keep each row's context when a table is split or continues on the next page

FEE_HEADER = "| STT | Mã phí | Nội dung | Mức phí | Tối thiểu |\n|---|---|---|---|---|"
FEE_ROWS = [
    "| 1 | | Chuyển tiền VND cùng hệ thống | | |",
    "| 1.1 | B101 | Chuyển khoản VND (TK - TK) | 0,01% | 10.000 đ |",
    "| 2 | | Chuyển tiền VND trong nước khác hệ thống | | |",
    *[f"| | B11{i} | - Trước 15h, mức {i} | 0,0{i}% | 20.000 đ |" for i in range(1, 6)],
    "| | B116 | - Từ 15h trở đi | 0,04% | 25.000 đ |",
    "| 9 | | Chuyển tiền ngoại tệ khác hệ thống | | |",
    "| 9.1 | | Chuyển tiền đi | | |",
    "| 9.1.1 | B131 | Chuyển tiền đi trong nước | 0,03% | 2 USD |",
    "| 9.1.2 | B133 | Chuyển tiền đi nước ngoài | 0,2% | 5 USD |",
]


def _part_with(chunks, marker):
    [text] = [c["text"] for c in chunks if marker in c["text"].split("\n", 3)[-1] or c["text"].endswith(marker)]
    return text.split("\n")


def test_a_split_fee_table_repeats_the_rows_each_part_sits_under():
    chunks = chunk_pages([_page(1, tables=["\n".join([FEE_HEADER, *FEE_ROWS])])], size=300)

    assert len(chunks) > 2
    for c in chunks:
        lines = c["text"].split("\n")
        assert "\n".join(lines[:2]) == FEE_HEADER and len(c["text"]) <= 300
        assert all(line in FEE_ROWS for line in lines[2:])
    late = next(c["text"].split("\n") for c in chunks if "B116" in c["text"])
    assert "| 2 | | Chuyển tiền VND trong nước khác hệ thống | | |" in late  # sub-item under its parent
    assert "| 1 | | Chuyển tiền VND cùng hệ thống | | |" not in late  # a closed branch is not repeated
    abroad = next(c["text"].split("\n") for c in chunks if "B133" in c["text"])
    i = abroad.index("| 9.1.2 | B133 | Chuyển tiền đi nước ngoài | 0,2% | 5 USD |")
    assert (
        abroad.index("| 9 | | Chuyển tiền ngoại tệ khác hệ thống | | |")
        < abroad.index("| 9.1 | | Chuyển tiền đi | | |")
        < i
    )
    assert "| 2 | | Chuyển tiền VND trong nước khác hệ thống | | |" not in abroad  # 9 closed 2


def test_every_row_still_appears_once_as_its_own_row_and_context_is_only_ever_an_earlier_row():
    chunks = chunk_pages([_page(1, tables=["\n".join([FEE_HEADER, *FEE_ROWS])])], size=300)

    seen = []
    for c in chunks:
        body = c["text"].split("\n")[2:]
        fresh = [row for row in body if row not in seen]
        assert body[len(body) - len(fresh) :] == fresh  # repeated context rows come first
        seen += fresh
    assert seen == FEE_ROWS


def test_context_rows_are_dropped_outermost_first_when_they_do_not_fit():
    rows = [
        "| 9 | | " + "Chuyển tiền ngoại tệ khác hệ thống " * 3 + "| |",
        "| 9.1 | | Chuyển tiền đi | |",
        *[f"| 9.1.{i} | B13{i} | Mục {i} | 0,{i}% |" for i in range(1, 8)],
    ]
    table = "\n".join(["| STT | Mã | Nội dung | Phí |", "|---|---|---|---|", *rows])

    chunks = chunk_pages([_page(1, tables=[table])], size=200)

    for c in chunks:
        assert len(c["text"]) <= 200
    last = chunks[-1]["text"].split("\n")
    assert "| 9.1 | | Chuyển tiền đi | |" in last and rows[0] not in last


def test_a_section_row_across_the_columns_heads_the_rows_below_it():
    section = "| | THẺ CORPORATE | THẺ CORPORATE | THẺ CORPORATE |"
    rows = [section, *[f"| {i} | Phí {i} | {i}0.000 đ | |" for i in range(1, 15)]]
    table = "\n".join(["| STT | Nội dung | Mức phí | Tối thiểu |", "|---|---|---|---|", *rows])

    chunks = chunk_pages([_page(1, tables=[table])], size=200)

    merged = "| | THẺ CORPORATE | | |"  # docling's merged cell, kept once
    assert len(chunks) > 1 and all(merged in c["text"].split("\n") for c in chunks)
    assert section not in chunks[0]["text"]


def test_a_merged_label_is_kept_once_but_equal_values_stay():
    table = "| STT | Nội dung | Mức phí | Tối thiểu |\n|---|---|---|---|\n| 1 | Phát hành | 0 đ | 0 đ |"

    [chunk] = chunk_pages([_page(1, tables=[table])])

    assert chunk["text"].endswith("| 1 | Phát hành | 0 đ | 0 đ |")


def test_a_table_continued_on_a_text_free_page_keeps_the_open_rows():
    page1 = "\n".join([FEE_HEADER, *FEE_ROWS[:3]])
    # docling drops an empty column on the next page and reads its first data row as the header
    page2 = "\n".join(["| | B111 | - Trước 15h | 0,03% |", "|---|---|---|---|", "| | B116 | - Từ 15h trở đi | 0,04% |"])

    chunks = chunk_pages([_page(1, tables=[page1]), _page(2, "", [page2])])

    [second] = [c["text"].split("\n") for c in chunks if c["page"] == 2]
    assert second == [
        "| 2 | | Chuyển tiền VND trong nước khác hệ thống | | |",
        "| | B111 | - Trước 15h | 0,03% |",
        "| | B116 | - Từ 15h trở đi | 0,04% |",
    ]  # no misaligned header from page 1, and the first row is data


def test_a_continuation_with_the_same_columns_reuses_the_header():
    page1 = "\n".join([FEE_HEADER, *FEE_ROWS[:3]])
    page2 = "\n".join(["| | B111 | - Trước 15h | 0,03% | 20.000 đ |", "|---|---|---|---|---|"])

    chunks = chunk_pages([_page(1, tables=[page1]), _page(2, "Ghi chú cuối trang", [page2])])

    [second] = [c["text"] for c in chunks if c["page"] == 2 and "B111" in c["text"]]
    parent = "| 2 | | Chuyển tiền VND trong nước khác hệ thống | | |"
    assert second.endswith(f"{FEE_HEADER}\n{parent}\n| | B111 | - Trước 15h | 0,03% | 20.000 đ |")


def test_a_new_table_after_text_on_the_page_is_not_a_continuation():
    page1 = "\n".join([FEE_HEADER, *FEE_ROWS[:3]])
    other = "| Hạng | Hạn mức |\n|---|---|\n| Chuẩn | 50 triệu |"

    chunks = chunk_pages([_page(1, tables=[page1]), _page(2, "Hạn mức thẻ", [other])])

    [second] = [c["text"] for c in chunks if c["page"] == 2 and "Chuẩn" in c["text"]]
    assert second.endswith(other)


def test_only_the_nearest_numbered_parent_is_repeated():
    # Repeating "9" on every part of section 9 made those parts outrank section 2 (test_ask case 10).
    rows = [
        "| 9 | | Chuyển tiền ngoại tệ khác hệ thống | |",
        "| 9.1 | | Chuyển tiền đi | |",
        *[f"| 9.1.{i} | B13{i} | Mục {i} | 0,{i}% |" for i in range(1, 9)],
    ]
    table = "\n".join(["| STT | Mã | Nội dung | Phí |", "|---|---|---|---|", *rows])

    chunks = chunk_pages([_page(1, tables=[table])], size=160)

    assert len(chunks) > 2
    for c in chunks[1:]:
        body = c["text"].split("\n")[2:]
        assert body[0] == "| 9.1 | | Chuyển tiền đi | |" and rows[0] not in body


def test_a_page_repeating_the_column_names_keeps_its_header_even_with_merged_columns():
    # T-038 review F-02 (vtb-bieu-phi-tai-khoan p3): OCR merged "TT | MÃ PHÍ", the page has no text.
    page1 = "\n".join([FEE_HEADER, *FEE_ROWS[:3]])
    own = "| STT Mã phí | Nội dung | Mức phí | Tối thiểu |\n|---|---|---|---|"
    page2 = "\n".join([own, "| B118 | Chuyển tiền theo lô | 6.000 đ | |"])

    chunks = chunk_pages([_page(1, tables=[page1]), _page(2, "", [page2])])

    [second] = [c["text"] for c in chunks if c["page"] == 2]
    assert second == "\n".join([own, "| B118 | Chuyển tiền theo lô | 6.000 đ | |"])


def test_a_row_with_digits_is_never_promoted_to_header():
    # T-038 review F-02 (tt50-2024 p29): "| I1 | Giao dịch loại A |" is data, not a second header line.
    rows = ["| I1 | Giao dịch loại A | Mã PIN |", "| 1 | Giao dịch loại B | OTP |", "| 2 | Giao dịch loại C | OTP |"]
    table = "\n".join(["| STT | Giao dịch | Xác thực |", "|---|---|---|", *rows])

    chunks = chunk_pages([_page(1, tables=[table])], size=80, overlap=10)

    assert all(rows[0] not in c["text"] for c in chunks[1:])


def test_a_long_carried_header_is_not_repeated_past_size():
    # T-038 review F-03 (nd52-2024 p56): a header longer than a quarter of the chunk is not carried over.
    long_header = "| " + "Nội dung yêu cầu của hồ sơ " * 4 + "| Ghi chú |\n|---|---|"
    page1 = "\n".join([long_header, "| a | b |"])
    page2 = "\n".join(["| " + "x " * 150 + "| y |", "|---|---|", "| c | d |"])

    chunks = chunk_pages([_page(1, tables=[page1]), _page(2, "", [page2])], size=400)

    assert all(long_header not in c["text"] for c in chunks if c["page"] == 2)
    assert all(len(c["text"]) <= 400 for c in chunks)
