"""Tiny PDF builders for parser tests, so no binary fixtures live in the repo."""

from __future__ import annotations

import io
from pathlib import Path

FEE_ROWS = [
    ("Dich vu", "Muc phi (VND)", "Ghi chu"),
    ("Rut tien ATM noi mang", "1.100", "Moi giao dich"),
    ("Rut tien ATM ngoai mang", "3.300", "Moi giao dich"),
    ("Phi thuong nien the ghi no", "66.000", "Moi nam"),
    ("Cap lai the", "55.000", "Moi lan"),
]

SCAN_LINES = [
    "BIỂU PHÍ DỊCH VỤ THẺ",
    "Phí rút tiền mặt tại ATM: 1.100 đồng",
    "Phí thường niên thẻ ghi nợ: 66.000 đồng",
]


def _pdf(page_ops: bytes, width: int = 595, height: int = 842) -> bytes:
    """One-page PDF with base-14 Helvetica; text must be ASCII."""
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>" % (width, height),
        b"<< /Length %d >>\nstream\n" % len(page_ops) + page_ops + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % i + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref))
    return out.getvalue()


def write_fee_table_pdf(path: Path) -> Path:
    """Digital PDF: a heading, a sentence and a ruled 3-column fee table."""
    x0, widths, row_h, top = 60, (220, 130, 120), 26, 700
    ops = [b"BT /F1 16 Tf 60 770 Td (BIEU PHI DICH VU THE) Tj ET"]
    ops.append(b"BT /F1 10 Tf 60 740 Td (Bieu phi ap dung tu ngay 01/01/2026 cho khach hang ca nhan.) Tj ET")
    right = x0 + sum(widths)
    bottom = top - row_h * len(FEE_ROWS)
    for r in range(len(FEE_ROWS) + 1):
        y = top - r * row_h
        ops.append(b"%d %d m %d %d l S" % (x0, y, right, y))
    x = x0
    for w in (0, *widths):
        x += w
        ops.append(b"%d %d m %d %d l S" % (x, top, x, bottom))
    for r, row in enumerate(FEE_ROWS):
        x = x0
        for w, cell in zip(widths, row, strict=True):
            ops.append(b"BT /F1 10 Tf %d %d Td (%s) Tj ET" % (x + 6, top - r * row_h - 17, cell.encode("ascii")))
            x += w
    path.write_bytes(_pdf(b"\n".join(ops)))
    return path


def write_scanned_pdf(path: Path) -> Path:
    """Image-only PDF (no text layer) with Vietnamese text, like a scanned page."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1240, 1754), "white")  # A4 at 150 dpi
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 36)
    except OSError:
        font = ImageFont.load_default(size=36)
    for i, line in enumerate(SCAN_LINES):
        draw.text((100, 150 + i * 80), line, fill="black", font=font)
    img.save(path, "PDF", resolution=150)
    return path
