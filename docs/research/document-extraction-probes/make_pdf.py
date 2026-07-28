"""Build resume_2col.pdf: a two-column resume whose content stream is COLUMN-ORDERED.

All of the left column is written first, then all of the right column. This is what
LaTeX and some template engines emit. Markers L1..L5 (left) and R1..R6 (right) let a
checker recover the extracted reading order mechanically.

Also plants:
  - two link annotations whose target URLs do NOT appear in the visible text
    (the LinkedIn/GitHub-behind-anchor-text case)
  - a second page that is a bare image with no text layer (a synthetic scan)
"""

import io
import struct
import zlib
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
PATH = OUT / "resume_2col.pdf"

W, H = LETTER

LEFT = [
    "JANE DOE",
    "EXPERIENCE",
    "L1 Senior Engineer, Acme Corp",
    "L2 Built the payments platform",
    "L3 Led a team of six engineers",
    "L4 Staff Engineer, Globex",
    "L5 Owned the data pipeline",
]
RIGHT = [
    "CONTACT",
    "R1 jane@example.com",
    "R2 SKILLS",
    "R3 Python, Go, Postgres",
    "R4 Kubernetes, Terraform",
    "R5 EDUCATION",
    "R6 BSc Computer Science",
]

# The URLs are deliberately absent from the drawn text.
LINKS = [
    ("LinkedIn Profile", "https://www.linkedin.com/in/janedoe-hidden", 250),
    ("GitHub", "https://github.com/janedoe-hidden", 225),
]


def make_png(w: int, h: int) -> bytes:
    """Minimal flat-grey RGB PNG, so the scan page needs no image dependencies."""
    raw = b"".join(b"\x00" + bytes([200, 200, 200] * w) for _ in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def main() -> None:
    c = canvas.Canvas(str(PATH), pagesize=LETTER)
    c.setFont("Helvetica", 11)

    y = H - 72
    for line in LEFT:
        c.drawString(60, y, line)
        y -= 20

    y = H - 72
    for line in RIGHT:
        c.drawString(330, y, line)
        y -= 20

    for anchor, url, y_pos in LINKS:
        c.drawString(60, y_pos, anchor)
        c.linkURL(url, (60, y_pos - 5, 260, y_pos + 15), relative=0)

    c.showPage()

    c.drawImage(
        ImageReader(io.BytesIO(make_png(200, 260))),
        40, 40, width=W - 80, height=H - 80,
    )
    c.showPage()
    c.save()
    print(f"wrote {PATH}")


if __name__ == "__main__":
    main()
