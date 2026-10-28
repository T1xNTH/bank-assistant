"""Chunk pages (recursive + table-aware), keeping source/page metadata.

Owner: A — Epic E-003. See docs/00-project/product-plan.md.

Input is ``parse_docling.parse()`` output; each chunk is
``{"source", "page", "chunk_index", "text"}``. ``chunk_index`` counts from 0
across the whole document, so ``(doc_id, chunk_index)`` is unique. Sizes are in
characters. Chunks never span pages.

- Text is split recursively (paragraphs, lines, sentences, words) into pieces of
  at most ``size`` characters, packed greedily one per line, and each chunk after the first
  starts with up to ``overlap`` characters (whole words) from the end of the
  previous one.
- Table cells lose docling's alignment padding. A table is never cut inside a
  row: one that fits becomes one chunk; a larger
  one is split between rows and every part repeats the header and separator
  rows. A single row longer than ``size`` stays whole. Tables get no overlap.
"""

from __future__ import annotations

import re

_SEPARATORS = ["\n\n", "\n", ". ", " "]
_TABLE_SEPARATOR = re.compile(r"^\|?(\s*:?-{3,}:?\s*\|)*\s*:?-{3,}:?\s*\|?$")  # only |, -, : and spaces
_SPACES = re.compile(r" {2,}")


def chunk_pages(pages: list[dict], size: int = 800, overlap: int = 100) -> list[dict]:
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError(f"need size > 0 and 0 <= overlap < size, got size={size}, overlap={overlap}")
    chunks: list[dict] = []
    for page in pages:
        pieces = _text_chunks(page["text"], size, overlap)
        for table in page["tables"]:
            pieces += _table_chunks(table, size)
        for text in pieces:
            chunks.append({"source": page["source"], "page": page["page"], "chunk_index": len(chunks), "text": text})
    return chunks


def _text_chunks(text: str, size: int, overlap: int) -> list[str]:
    # Pieces leave room for the overlap carried into the next chunk.
    pieces = _split(text.strip(), size - overlap - 1 if overlap else size, _SEPARATORS, size)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        joined = f"{current}\n{piece}" if current else piece
        if len(joined) <= size:
            current = joined
            continue
        if current:
            chunks.append(current)
        tail = _tail(current, overlap)
        current = f"{tail}\n{piece}" if tail and len(tail) + 1 + len(piece) <= size else piece
    if current:
        chunks.append(current)
    return chunks


def _split(text: str, size: int, separators: list[str], hard: int) -> list[str]:
    """Pieces of at most ``size`` characters: parts at the coarsest separator, merged back while they fit.

    A single word is only cut when it is longer than ``hard`` (the real chunk size).
    """
    if len(text) <= size:
        return [text] if text else []
    if not separators:
        if len(text) <= hard:
            return [text]
        return [text[i : i + hard] for i in range(0, len(text), hard)]
    sep, rest = separators[0], separators[1:]
    parts = [p.strip() for p in text.split(sep) if p.strip()]
    if len(parts) <= 1:
        return _split(text, size, rest, hard)
    end = sep.strip()  # ". " keeps its full stop where a piece is cut
    out: list[str] = []
    current = ""
    for part in parts:
        joined = f"{current}{sep}{part}" if current else part
        if len(joined) <= size:
            current = joined
            continue
        if current:
            closes = end and not current.endswith(end) and len(current) + len(end) <= size
            out.append(current + end if closes else current)
        if len(part) <= size:
            current = part
        else:
            out += _split(part, size, rest, hard)
            current = ""
    if current:
        out.append(current)
    return out


def _tail(text: str, overlap: int) -> str:
    if overlap == 0 or len(text) <= overlap:
        return "" if overlap == 0 else text
    cut = text[-overlap:]
    if text[-overlap - 1].isspace():
        return cut.strip()  # already starts at a word boundary
    gap = re.search(r"\s", cut)
    return cut[gap.end() :].strip() if gap else ""  # start at the next word boundary


def _compact(line: str, separator: bool) -> str:
    """docling pads cells to align columns; the padding is only noise for search and the size limit."""
    if separator:
        return "|" + "|".join("---" for _ in line.strip().strip("|").split("|")) + "|"
    return _SPACES.sub(" ", line.strip())


def _table_chunks(table: str, size: int) -> list[str]:
    lines = table.strip().splitlines()
    sep_row = 1 if len(lines) > 1 and _TABLE_SEPARATOR.match(lines[1].strip()) else -1  # Markdown: 2nd line only
    table = "\n".join(_compact(line, i == sep_row) for i, line in enumerate(lines))
    if not table:
        return []
    if len(table) <= size:
        return [table]
    lines = table.splitlines()
    head_len = 2 if sep_row == 1 else 0
    head, rows = lines[:head_len], lines[head_len:]
    chunks: list[str] = []
    current: list[str] = []
    for row in rows:
        if current and len("\n".join([*head, *current, row])) > size:
            chunks.append("\n".join([*head, *current]))
            current = []
        current.append(row)
    if current:
        chunks.append("\n".join([*head, *current]))
    return chunks
