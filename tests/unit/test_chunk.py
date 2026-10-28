"""chunk_pages: text and table chunking on hand-made pages."""

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

    assert chunk["text"] == text


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

    assert [(c["source"], c["page"], c["chunk_index"]) for c in chunks] == [
        ("nd293.pdf", 1, 0),
        ("nd293.pdf", 3, 1),
        ("nd293.pdf", 3, 2),
    ]


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
