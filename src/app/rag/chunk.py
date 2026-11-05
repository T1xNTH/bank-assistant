"""Chunk parsed pages by document structure (CR-009), keeping source/page metadata.

Owner: A — Epic E-003. See docs/00-project/product-plan.md.

Input is ``parse_docling.parse()`` output; each chunk is
``{"source", "page", "chunk_index", "text"}``. ``chunk_index`` counts from 0
across the whole document, so ``(doc_id, chunk_index)`` is unique. Sizes are in
characters.

- The text of all pages is read as one document and cut into sections at legal
  headings (Phần, Chương, Mục, Điều, Phụ lục; with or without docling's ``## ``).
  A heading must not continue in lower case ("Chương II của Nghị định này" is
  body text); OCR misreadings of Roman numerals (IH, VH, VỊ, H, EV) are accepted.
  A document without them is cut at docling's other ``## `` headings instead; a
  ``## `` heading straight after another with no text between is its child.
  Text before the first heading is a section of its own. A section runs across
  page breaks; a chunk's ``page`` is the page its first new line comes from.
- Every chunk of a section starts with one line naming its heading path, e.g.
  ``Chương II. ... › Điều 5. Mức tham chiếu``, capped at a quarter of ``size``
  (outer levels are dropped first). The line counts towards ``size``. A heading
  that does not survive whole in that line starts its section's text, and one
  with no text of its own that is not carried by the next section's path is a
  chunk of its own, so no heading's words are lost.
- Inside a section, paragraphs and list items (khoản, điểm) are packed greedily,
  one per line; longer ones are split recursively (lines, sentences, words), and
  each chunk after the first starts with up to ``overlap`` characters (whole
  words) from the end of the previous one in that section.
- Table cells lose docling's alignment padding. A table is never cut inside a
  row: one that fits becomes one chunk; a larger one is split between rows and
  every part repeats the header and separator rows. A single row longer than
  ``size`` stays whole. Tables get no overlap. docling does not say where on a
  page a table sits, so its heading line is the one in effect at the end of
  that page's text, unless that heading ends the page with no text after it.
- Row context (T-038): fee schedules nest rows by their STT number ("9" >
  "9.1" > "9.1.2") and put sub-items ("- Từ 15h trở đi") in unnumbered rows,
  and a row such as "| | THẺ CORPORATE | THẺ CORPORATE |" (one label across
  the columns) names a section. A part that starts below such rows repeats the
  section rows and the nearest numbered parent after the header (section rows
  dropped first when they do not fit), so a fee is never cut off from what it
  is the fee of. Outer levels are not repeated: "9 Chuyển tiền ngoại tệ khác
  hệ thống" on every part of section 9 outranked section 2 for "chuyển tiền
  trong nước khác hệ thống".
- A table continued on the next page: the first table of a page continues the
  previous page's last table when nothing on the page comes before it, its
  first row reads as data (a figure, a code or an empty cell) and does not
  repeat that table's column names (at least half its words). A heading or
  text before the table starts a new section, even with the same column
  count. Its first row is data. It gets the previous row context, and the
  previous header when the columns line up (docling drops empty columns page
  by page). Up to two rows without digits before a table's
  first numbered row are more header lines and are repeated with it.
- A merged cell: docling repeats its label in every column it spans. In a
  section row (one long label after empty cells or a short code) it is kept
  once; a row with its own label keeps every value, equal or not.
"""

from __future__ import annotations

import re

_SEPARATORS = ["\n\n", "\n", ". ", " "]
_TABLE_SEPARATOR = re.compile(r"^\|?(\s*:?-{3,}:?\s*\|)*\s*:?-{3,}:?\s*\|?$")  # only |, -, : and spaces
_SPACES = re.compile(r" {2,}")
_ROMAN = r"[IVXLCHỊE]+"  # OCR reads II as H, III as IH, VI as VỊ, IV as EV
_LEGAL = [  # outermost first; a heading clears the levels below it
    re.compile(rf"(PHẦN|Phần)\s+(THỨ\s+\S+|Thứ\s+\S+|{_ROMAN}|\d+)\b"),
    re.compile(rf"(CHƯƠNG|Chương)\s+({_ROMAN}|\d+)\b"),
    re.compile(r"(MỤC|Mục)\s+\d+\b(?![:.]\d|:)"),  # not form items such as "Mục 1:" or "Mục 1.1"
    re.compile(r"Điều\s+\d+[a-zđ]?\s*[.:]"),
]
_APPENDIX = re.compile(rf"(PHỤ LỤC|Phụ lục)(\s+({_ROMAN}|\d+)\b)?")
_BOILERPLATE = re.compile(r"CỘNG H[ÒO]A XÃ HỘI|Độc lập\s*-\s*Tự do", re.IGNORECASE)
_PATH_SEPARATOR = " › "
_STT = re.compile(r"\d+(\.\d+)*\.?")  # "9", "9.1.2", "3."
_NOISE = "-–•`' "  # OCR noise before a marked heading: "## - Chương X ..."


def chunk_pages(pages: list[dict], size: int = 800, overlap: int = 100) -> list[dict]:
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError(f"need size > 0 and 0 <= overlap < size, got size={size}, overlap={overlap}")
    # An appendix heading alone does not make a fee schedule a legal text.
    lines = [line.strip().removeprefix("## ") for p in pages for line in p["text"].splitlines()]
    legal = any(pattern.match(line) for line in lines for pattern in _LEGAL)
    # A fee schedule (tables, no legal headings) whose first line docling did not mark as a heading
    # is named by that line; it heads every chunk, above later headings, so that its tables are not
    # confused with another schedule's.
    raw = [line.strip() for p in pages for line in p["text"].splitlines() if line.strip()]
    title = (
        not legal
        and raw
        and _level(raw[0], legal) is None
        and any(p["tables"] for p in pages)
        and len(raw[0]) <= size // 4
    )
    out: list[tuple[int, int, int, str]] = []  # (page, text 0 / table 1, order, text): sorted into reading order
    levels: dict[int, str] = {}  # heading level -> heading text of the open section
    section: list[tuple[int, str]] = []  # (page, line) of the open section
    opened: tuple[int, str] | None = None  # (page, heading) that opened the section
    before = ""  # heading path in effect before ``opened``
    carry: _Carry | None = None  # the previous page's last table, for a continuation

    def close(following: str | None) -> None:
        """Emit the open section; ``following`` is the next section's heading path (None at the end)."""
        header = _header(levels, size)
        body = list(section)
        if opened and opened[1] not in header:
            body.insert(0, opened)  # the path was cut: the heading's own words go into the text
        if not body and opened and (following is None or opened[1] not in following):
            body = [opened]  # a heading with no text that the next path does not repeat
            header = _header({k: v for k, v in levels.items() if v != opened[1]}, size)
        for page, text in _section_chunks(header, body, size, overlap):
            if header and text.startswith(f"{header}\n{header}\n"):
                text = text[len(header) + 1 :]  # the title line heading its own section
            out.append((page, 0, len(out), text))
        section.clear()

    for page in pages:
        for line in (line.strip() for line in page["text"].splitlines()):
            level = _level(line, legal)
            if title and line:
                levels[-1], title = _clean(line), False  # also kept as text: it may be the only mention
            if level is None:
                if line:
                    section.append((page["page"], _clean(line)))  # a non-heading "## " line keeps its words only
                continue
            if not legal and opened and not section:
                level = max(levels) + 1  # a "## " heading right under another one is its subheading
            heading = _clean(line).lstrip(_NOISE) if line.startswith("## ") else _clean(line)
            following = {k: v for k, v in levels.items() if k < level} | {level: heading}
            close(_header(following, size))
            before, levels, opened = _header(levels, size), following, (page["page"], heading)
        # A heading closing the page with no text after it ("## Tệp đính kèm") comes after the page's tables.
        trailing = opened is not None and opened[0] == page["page"] and not section
        header = before if trailing else _header(levels, size)
        for i, table in enumerate(page["tables"]):
            budget = size - len(header) - 1 if header else size
            starts_page = i == 0 and not page["text"].strip()  # nothing on the page before this table
            texts, carry = _table_chunks(table, budget, carry if i == 0 else None, starts_page)
            for text in texts:
                out.append((page["page"], 1, len(out), f"{header}\n{text}" if header else text))
        if not page["tables"]:
            carry = None  # a page without tables ends any table
    close(None)
    out.sort()
    return [
        {"source": pages[0]["source"], "page": page, "chunk_index": i, "text": text}
        for i, (page, _, _, text) in enumerate(out)
    ]


def _level(line: str, legal: bool) -> int | None:
    """Heading level of a line, or None for body text."""
    text = line.removeprefix("## ").strip()
    if line.startswith("## "):
        text = text.lstrip(_NOISE)
    if not text or len(text) > 300:
        return None
    for level, pattern in [(0, _APPENDIX), *enumerate(_LEGAL)]:
        match = pattern.match(text)
        if match and not text[match.end() :].lstrip()[:1].islower():  # "Phụ lục II ban hành kèm theo ..." is text
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


class _Carry:
    """What a table continued on the next page needs from its previous part."""

    def __init__(self, head: list[str], columns: int, stack: list[tuple[int, str]]):
        self.head, self.columns, self.stack = head, columns, stack


def _cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _depth(row: str, sections: set[str] = frozenset()) -> int | None:
    """0 for a section row (one label across the columns), n for STT "a.b...", None for other rows."""
    if row in sections:
        return 0
    cells = _cells(row)
    if _STT.fullmatch(cells[0]):
        return cells[0].rstrip(".").count(".") + 1
    labels = [cell for cell in cells[1:] if cell]
    if not cells[0] and len(labels) >= 2 and len(set(labels)) == 1:
        return 0
    return None


def _context(stack: list[tuple[int, str]], depth: int | None) -> list[str]:
    """The rows a row sits under: outer numbered rows, or all of them for an unnumbered sub-item."""
    above = [(d, row) for d, row in stack if depth is None or d < depth]
    numbered = [row for d, row in above if d > 0]
    # Section rows and the nearest numbered parent only: repeating every level put the same outer row
    # ("9 Chuyển tiền ngoại tệ khác hệ thống") on many chunks, which then outranked their cousins.
    return [row for d, row in above if d == 0] + numbered[-1:]


def _push(stack: list[tuple[int, str]], depth: int | None, row: str) -> None:
    if depth is None:
        return
    while stack and stack[-1][0] >= depth and not (depth > 0 and stack[-1][0] == 0):
        stack.pop()
    stack.append((depth, row))


_WORD = re.compile(r"[^\W\d_]{2,}")


def _like_header(row: str, header: str) -> bool:
    """Whether ``row`` repeats ``header``: a page's own copy of the column names ("TT MÃ PHÍ | NỘI DUNG"
    where OCR merged two cells) is a header, not the first data row of a continued table (T-038 review)."""
    words, names = (set(_WORD.findall(text.lower())) for text in (row, header))
    return bool(words) and len(words & names) >= len(words) / 2


def _merge_spans(row: str) -> str:
    """docling repeats a merged cell's text in every column it spans; keep it once in a section row.

    A section row is nothing but one long label repeated across the columns, after empty cells or a
    short code ("| | THẺ CORPORATE | THẺ CORPORATE |", "| A | | DỊCH VỤ SMS BANKING | DỊCH VỤ SMS BANKING |").
    A row with its own label ("| Phát hành | Miễn phí | Miễn phí | Miễn phí |") holds one value per
    column, equal or not, and is kept as it is (PR #105 review).
    """
    cells = _cells(row)
    lead = 0
    while lead < len(cells) and (not cells[lead] or (len(cells[lead]) <= 2 and not cells[lead].isdigit())):
        lead += 1
    labels = [cell for cell in cells[lead:] if cell]
    if len(labels) < 2 or len(set(labels)) != 1 or sum(ch.isalpha() for ch in labels[0]) < 12:
        return row
    if cells[lead] != labels[0]:  # the label starts the rest of the row; no other value comes first
        return row
    out = [*cells[: lead + 1], *("" for _ in range(lead + 1, len(cells)))]
    return _SPACES.sub(" ", "| " + " | ".join(out) + " |")


def _looks_like_data(row: str) -> bool:
    """Whether a page's first table row reads as data: a figure, a code or an empty cell. docling makes
    the first row of a continued table its header; a table's own header ("| Hạng thẻ | Hạn mức |") names
    every column and has no figures (PR #105 review)."""
    return any(ch.isdigit() for ch in row) or "" in _cells(row)


def _table_chunks(
    table: str, size: int, carry: _Carry | None = None, starts_page: bool = False
) -> tuple[list[str], _Carry | None]:
    lines = table.strip().splitlines()
    sep_row = 1 if len(lines) > 1 and _TABLE_SEPARATOR.match(lines[1].strip()) else -1  # Markdown: 2nd line only
    lines = [_compact(line, i == sep_row) for i, line in enumerate(lines)]
    if not "\n".join(lines):
        return [], None
    sections = {_merge_spans(line) for line in lines if _depth(line) == 0}  # told apart before merging
    lines = [line if i == sep_row else _merge_spans(line) for i, line in enumerate(lines)]
    head_len = 2 if sep_row == 1 else 0
    head, rows = lines[:head_len], lines[head_len:]
    columns = len(_cells(lines[0]))
    stack: list[tuple[int, str]] = []
    same = carry is not None and columns == carry.columns
    if carry and head and starts_page and _looks_like_data(head[0]) and not _like_header(head[0], carry.head[0]):
        # Continued from the last page: the first row is data. Only a table with nothing before it on its
        # page continues one (a heading or text starts a new section, PR #105 review); docling drops
        # empty columns page by page, so the previous header is reused only when the columns still line up.
        rows, stack = [head[0], *rows], list(carry.stack)
        # A carried header longer than a quarter of the chunk is a data row docling read as the header
        # and would push parts past ``size`` (T-038 review F-03): repeat it only when it is short.
        head = carry.head if same and len("\n".join(carry.head)) <= size // 4 else []
    elif head:
        # More header lines ("| | MÃ PHÍ | NỘI DUNG |"): at most two rows before the first numbered row.
        # Section rows among them stay rows, so that they carry on as row context.
        first = next((i for i, row in enumerate(rows) if _depth(row, sections)), None)
        labels = rows[:first] if first is not None else []
        if first is not None and first <= 2 and not any(ch.isdigit() for row in labels for ch in row):
            lead = rows[:first]
            head = [*head, *(row for row in lead if _depth(row, sections) is None)]
            rows = [*(row for row in lead if _depth(row, sections) == 0), *rows[first:]]
    if not rows:
        # Docling exports a one-row table as header + separator. The header
        # can contain all the data; retain it like any other oversized row.
        return ["\n".join(lines)], None
    chunks: list[str] = []
    current: list[str] = []
    context: list[str] = []
    for row in rows:
        depth = _depth(row, sections)
        if current and len("\n".join([*head, *context, *current, row])) > size:
            chunks.append("\n".join([*head, *context, *current]))
            current = []
        if not current:
            context = _context(stack, depth)
            while context and len("\n".join([*head, *context, row])) > size:
                context = context[1:]  # outermost first
        current.append(row)
        _push(stack, depth, row)
    chunks.append("\n".join([*head, *context, *current]))
    if not head:  # a continuation under another column layout: later pages line up with the original
        return chunks, _Carry(carry.head, carry.columns, stack) if carry else None
    return chunks, _Carry(head, columns, stack)
