"""chunk_pages: text and table chunking on hand-made pages."""

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
