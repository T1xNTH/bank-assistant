"""Tiny PDF builders for parser tests, so no binary fixtures live in the repo."""

from __future__ import annotations

from pathlib import Path

import pytest

FEE_ROWS = [
    ("Dịch vụ", "Mức phí (VND)", "Ghi chú"),
    ("Rút tiền ATM nội mạng", "1.100", "Mỗi giao dịch"),
    ("Rút tiền ATM ngoại mạng", "3.300", "Mỗi giao dịch"),
    ("Phí thường niên thẻ ghi nợ", "66.000", "Mỗi năm"),
    ("Cấp lại thẻ", "55.000", "Mỗi lần"),
]

# Fonts with Vietnamese glyphs (Linux, Windows, macOS). Fonts without them render
# boxes, which would make the parser tests fail for the wrong reason.
VI_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]

SCAN_LINES = [
    "BIỂU PHÍ DỊCH VỤ THẺ",
    "Phí rút tiền mặt tại ATM: 1.100 đồng",
    "Phí thường niên thẻ ghi nợ: 66.000 đồng",
]


def _vi_font_path() -> str:
    for path in VI_FONTS:
        if Path(path).is_file():
            return path
    pytest.skip(f"no font with Vietnamese glyphs found (tried {', '.join(VI_FONTS)})")


def write_fee_table_pdf(path: Path) -> Path:
    """Digital PDF with a Vietnamese text layer: a heading, a sentence and a ruled fee table."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    pdfmetrics.registerFont(TTFont("Vi", _vi_font_path()))
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Vi", 16)
    c.drawString(60, 770, "BIỂU PHÍ DỊCH VỤ THẺ")
    c.setFont("Vi", 10)
    c.drawString(60, 740, "Biểu phí áp dụng từ ngày 01/01/2026 cho khách hàng cá nhân.")
    x0, widths, row_h, top = 60, (220, 130, 120), 26, 700
    right, bottom = x0 + sum(widths), top - row_h * len(FEE_ROWS)
    for r in range(len(FEE_ROWS) + 1):
        c.line(x0, top - r * row_h, right, top - r * row_h)
    x = x0
    for w in (0, *widths):
        x += w
        c.line(x, top, x, bottom)
    for r, row in enumerate(FEE_ROWS):
        x = x0
        for w, cell in zip(widths, row, strict=True):
            c.drawString(x + 6, top - r * row_h - 17, cell)
            x += w
    c.save()
    return path


def write_scanned_pdf(path: Path) -> Path:
    """Image-only PDF (no text layer) with Vietnamese text, like a scanned page."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1240, 1754), "white")  # A4 at 150 dpi
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(_vi_font_path(), 36)
    for i, line in enumerate(SCAN_LINES):
        draw.text((100, 150 + i * 80), line, fill="black", font=font)
    img.save(path, "PDF", resolution=150)
    return path
