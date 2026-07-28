"""Build resume_2col_interleaved.pdf: visually identical two-column layout to
resume_2col.pdf, but the content stream is written LINE-BY-LINE ACROSS COLUMNS
(line 1 left, line 1 right, line 2 left, line 2 right, ...).

This is what many Word / Canva / HTML-to-PDF exports emit, and it is the case that
defeats every extractor that trusts the content stream.
"""

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
PATH = OUT / "resume_2col_interleaved.pdf"

W, H = LETTER

LEFT = [
    "L1 Senior Engineer, Acme Corp",
    "L2 Built the payments platform",
    "L3 Led a team of six engineers",
    "L4 Staff Engineer, Globex",
    "L5 Owned the data pipeline",
]
RIGHT = [
    "R1 jane@example.com",
    "R2 SKILLS",
    "R3 Python, Go, Postgres",
    "R4 Kubernetes, Terraform",
    "R5 EDUCATION",
    "R6 BSc Computer Science",
]


def main() -> None:
    c = canvas.Canvas(str(PATH), pagesize=LETTER)
    c.setFont("Helvetica", 11)
    y = H - 100
    for i in range(max(len(LEFT), len(RIGHT))):
        if i < len(LEFT):
            c.drawString(60, y, LEFT[i])
        if i < len(RIGHT):
            c.drawString(330, y, RIGHT[i])
        y -= 20
    c.showPage()
    c.save()
    print(f"wrote {PATH}")


if __name__ == "__main__":
    main()
