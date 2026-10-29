"""Chunk parsed pages by document structure (CR-009), keeping source/page metadata.

Owner: A — Epic E-003. See docs/00-project/product-plan.md.

Input is ``parse_docling.parse()`` output; each chunk is
``{"source", "page", "chunk_index", "text"}``. ``chunk_index`` counts from 0
across the whole document, so ``(doc_id, chunk_index)`` is unique. Sizes are in
characters.

- The text of all pages is read as one document and cut into sections at legal
  headings (Phần, Chương, Mục, Điều, Phụ lục; with or without docling's ``## ``).
  A document without them is cut at docling's other ``## `` headings instead.
  Text before the first heading is a section of its own. A section runs across
  page breaks; a chunk's ``page`` is the page its first new line comes from.
- Every chunk of a section starts with one line naming its heading path, e.g.
  ``Chương II. ... › Điều 5. Mức tham chiếu``, capped at a quarter of ``size``
  (outer levels are dropped first). The line counts towards ``size``.
- Inside a section, paragraphs and list items (khoản, điểm) are packed greedily,
  one per line; longer ones are split recursively (lines, sentences, words), and
  each chunk after the first starts with up to ``overlap`` characters (whole
  words) from the end of the previous one in that section.
- Table cells lose docling's alignment padding. A table is never cut inside a
  row: one that fits becomes one chunk; a larger one is split between rows and
  every part repeats the header and separator rows. A single row longer than
  ``size`` stays whole. Tables get no overlap. docling does not say where on a
  page a table sits, so its heading line is the one in effect at the end of
  that page's text.
"""

from __future__ import annotations

import re

_SEPARATORS = ["\n\n", "\n", ". ", " "]
_TABLE_SEPARATOR = re.compile(r"^\|?(\s*:?-{3,}:?\s*\|)*\s*:?-{3,}:?\s*\|?$")  # only |, -, : and spaces
_SPACES = re.compile(r" {2,}")
_LEGAL = [  # outermost first; a heading clears the levels below it
    re.compile(r"(PHẦN|Phần)\s+(THỨ\s+\S+|Thứ\s+\S+|[IVXLC]+|\d+)\b"),
    re.compile(r"(CHƯƠNG|Chương)\s+[IVXLC\d]+\b"),
    re.compile(r"(MỤC|Mục)\s+\d+\b"),
    re.compile(r"Điều\s+\d+[a-zđ]?\s*[.:]"),
]
_APPENDIX = re.compile(r"(PHỤ LỤC|Phụ lục)\b")
_BOILERPLATE = re.compile(r"CỘNG H[ÒO]A XÃ HỘI|Độc lập\s*-\s*Tự do", re.IGNORECASE)
_PATH_SEPARATOR = " › "


def chunk_pages(pages: list[dict], size: int = 800, overlap: int = 100) -> list[dict]:
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError(f"need size > 0 and 0 <= overlap < size, got size={size}, overlap={overlap}")
    # An appendix heading alone does not make a fee schedule a legal text.
    lines = [line.strip().removeprefix("## ") for p in pages for line in p["text"].splitlines()]
    legal = any(pattern.match(line) for line in lines for pattern in _LEGAL)
    out: list[tuple[int, int, int, str]] = []  # (page, text 0 / table 1, order, text): sorted into reading order
    levels: dict[int, str] = {}  # heading level -> heading text of the open section
    section: list[tuple[int, str]] = []  # (page, line) of the open section

    def close() -> None:
        for page, text in _section_chunks(_header(levels, size), section, size, overlap):
            out.append((page, 0, len(out), text))
        section.clear()

    for page in pages:
        for line in (line.strip() for line in page["text"].splitlines()):
            level = _level(line, legal)
            if level is None:
                if line:
                    section.append((page["page"], _clean(line)))  # a non-heading "## " line keeps its words only
                continue
            close()
            for deeper in [k for k in levels if k >= level]:
                del levels[deeper]
            levels[level] = _clean(line)
        header = _header(levels, size)
        for table in page["tables"]:
            for text in _table_chunks(table, size - len(header) - 1 if header else size):
                out.append((page["page"], 1, len(out), f"{header}\n{text}" if header else text))
    close()
    out.sort()
    return [
        {"source": pages[0]["source"], "page": page, "chunk_index": i, "text": text}
        for i, (page, _, _, text) in enumerate(out)
    ]


def _level(line: str, legal: bool) -> int | None:
    """Heading level of a line, or None for body text."""
    text = line.removeprefix("## ").strip()
    if not text or len(text) > 300:
        return None
    if _APPENDIX.match(text):
        return 0
    for level, pattern in enumerate(_LEGAL):
        if pattern.match(text):
            return level
    if line.startswith("## ") and not legal and not _BOILERPLATE.search(text):
        return 0  # documents without legal structure (fee schedules, bank terms)
    return None


def _clean(line: str) -> str:
    return _SPACES.sub(" ", line.removeprefix("## ").strip())


def _header(levels: dict[int, str], size: int) -> str:
    """The heading path, dropping outer levels first and cutting the last one to fit a quarter of size."""
    limit = size // 4
    parts = [levels[k] for k in sorted(levels)]
    while len(parts) > 1 and len(_PATH_SEPARATOR.join(parts)) > limit:
        parts.pop(0)
    header = _PATH_SEPARATOR.join(parts)
    if len(header) <= limit:
        return header
    return header[: limit - 1].rstrip() + "…" if limit > 1 else ""


def _section_chunks(header: str, section: list[tuple[int, str]], size: int, overlap: int) -> list[tuple[int, str]]:
    budget = size - len(header) - 1 if header else size
    overlap = min(overlap, budget // 2)
    pieces = [
        (page, piece)
        for page, para in section
        for piece in _split(para, budget - overlap - 1 if overlap else budget, _SEPARATORS, budget)
    ]
    return [(page, f"{header}\n{text}" if header else text) for page, text in _pack(pieces, budget, overlap)]


def _pack(pieces: list[tuple[int, str]], size: int, overlap: int) -> list[tuple[int, str]]:
    """Greedy packing, one piece per line; a chunk's page is its first new piece's page."""
    chunks: list[tuple[int, str]] = []
    current, page = "", 0
    for piece_page, piece in pieces:
        joined = f"{current}\n{piece}" if current else piece
        if len(joined) <= size:
            page = page if current else piece_page
            current = joined
            continue
        if current:
            chunks.append((page, current))
        tail = _tail(current, overlap)
        current = f"{tail}\n{piece}" if tail and len(tail) + 1 + len(piece) <= size else piece
        page = piece_page
    if current:
        chunks.append((page, current))
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
    if not rows:
        # Docling exports a one-row table as header + separator. The header
        # can contain all the data; retain it like any other oversized row.
        return [table]
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
