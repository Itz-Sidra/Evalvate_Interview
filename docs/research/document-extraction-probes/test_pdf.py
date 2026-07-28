"""Probe PDF extractors for the properties that matter to a resume parser:

  A. multi-column reading order, on both a column-ordered and an interleaved stream
  B. hyperlink URL recovery when the URL is not in the visible text
  C. character/font geometry APIs
  D. text-layer (scanned page) detection

The reading-order verdict is mechanical, not eyeballed: pull the ordered sequence of
L/R markers out of the extracted text, run-length encode it, and if there are more
than 2 runs then the columns were interleaved.

Run make_pdf.py and make_pdf2.py first.
"""

import re
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from pdfminer.high_level import extract_text as pm_extract
from pdfminer.layout import LAParams
from pypdf import PdfReader

OUT = Path(__file__).parent / "out"
COL_ORDERED = OUT / "resume_2col.pdf"
INTERLEAVED = OUT / "resume_2col_interleaved.pdf"

# URLs that exist only in link annotations, never in the drawn text.
TARGETS = ["linkedin.com/in/janedoe-hidden", "github.com/janedoe-hidden"]

GOOD = "correct"
BAD = "interleaved"


def order_verdict(text: str) -> tuple[str, str]:
    """Return (verdict, run-length shape) for the L/R marker sequence."""
    seq = re.findall(r"\b([LR])\d\b", text or "")
    if not seq:
        return "no markers", ""
    runs: list[list] = []
    for s in seq:
        if not runs or runs[-1][0] != s:
            runs.append([s, 1])
        else:
            runs[-1][1] += 1
    shape = "".join(f"{k}x{n}" for k, n in runs)
    return (GOOD if len(runs) <= 2 else BAD), shape


# ---------------------------------------------------------------- gutter detector


def find_gutter(page, min_width=10.0, mid_frac=0.5):
    """Widest vertical band in the middle `mid_frac` of the page crossed by no word.

    Returns the band's centre x, or None if there is no plausible gutter.
    """
    words = page.extract_words()
    if not words:
        return None

    spans = sorted((float(w["x0"]), float(w["x1"])) for w in words)
    merged: list[list[float]] = []
    for x0, x1 in spans:
        if merged and x0 <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], x1)
        else:
            merged.append([x0, x1])

    lo = page.width * (0.5 - mid_frac / 2)
    hi = page.width * (0.5 + mid_frac / 2)

    best = None
    for (_, end), (start, _) in zip(merged, merged[1:]):
        width = start - end
        centre = (end + start) / 2
        if width >= min_width and lo <= centre <= hi:
            if best is None or width > best[0]:
                best = (width, centre)
    return best[1] if best else None


def extract_columns(page) -> str:
    """Extract text column-by-column if a gutter is found, else fall back."""
    gutter = find_gutter(page)
    if gutter is None:
        return page.extract_text() or ""
    left = page.crop((0, 0, gutter, page.height)).extract_text() or ""
    right = page.crop((gutter, 0, page.width, page.height)).extract_text() or ""
    return f"{left}\n{right}"


# ---------------------------------------------------------------- extractors

def modes(path: Path) -> dict[str, str]:
    """Run every extraction mode against `path`, returning {label: text}."""
    out: dict[str, str] = {}
    p = str(path)

    with pdfplumber.open(p) as pdf:
        page = pdf.pages[0]
        out["pdfplumber.extract_text()"] = page.extract_text() or ""
        out["pdfplumber layout=True"] = page.extract_text(layout=True) or ""
        out["pdfplumber use_text_flow=True"] = page.extract_text(use_text_flow=True) or ""
        out["custom gutter detector"] = extract_columns(page)

    out["pdfminer.six default LAParams"] = pm_extract(p, page_numbers=[0])
    out["pdfminer.six boxes_flow=-1.0"] = pm_extract(
        p, page_numbers=[0], laparams=LAParams(boxes_flow=-1.0)
    )

    doc = pdfium.PdfDocument(p)
    out["pypdfium2 get_text_bounded()"] = doc[0].get_textpage().get_text_bounded()

    r = PdfReader(p)
    out["pypdf extract_text()"] = r.pages[0].extract_text()
    out["pypdf extraction_mode=layout"] = r.pages[0].extract_text(extraction_mode="layout")
    return out


ROW_ORDER = [
    "pdfplumber.extract_text()",
    "pdfplumber layout=True",
    "pdfplumber use_text_flow=True",
    "pdfminer.six default LAParams",
    "pdfminer.six boxes_flow=-1.0",
    "pypdfium2 get_text_bounded()",
    "pypdf extract_text()",
    "pypdf extraction_mode=layout",
    "custom gutter detector",
]


def section_a() -> None:
    print("=" * 92)
    print("A. MULTI-COLUMN READING ORDER")
    print("=" * 92)
    col = modes(COL_ORDERED)
    inter = modes(INTERLEAVED)

    print(f"{'extraction mode':34} {'column-ordered':>26} {'interleaved':>26}")
    print("-" * 92)
    for label in ROW_ORDER:
        cv, cs = order_verdict(col[label])
        iv, ivs = order_verdict(inter[label])
        print(f"{label:34} {cv + ' ' + cs:>26} {iv + ' ' + ivs:>26}")

    print()
    print("--- custom gutter detector, interleaved stream, raw output ---")
    print(inter["custom gutter detector"])


def section_b() -> None:
    print()
    print("=" * 92)
    print("B. HYPERLINK URL RECOVERY (URLs absent from visible text)")
    print("=" * 92)

    def hit(s: str) -> bool:
        return all(t in str(s) for t in TARGETS)

    p = str(COL_ORDERED)
    with pdfplumber.open(p) as pdf:
        page = pdf.pages[0]
        plain = page.extract_text() or ""
        links = page.hyperlinks
        annots = page.annots
    print(f"{'plain extracted text (pdfplumber)':44} {hit(plain)}")
    print(f"{'pdfplumber page.hyperlinks':44} {hit(links)} -> {[h.get('uri') for h in links]}")
    print(f"{'pdfplumber page.annots':44} {hit(annots)}")

    doc = pdfium.PdfDocument(p)
    print(f"{'plain extracted text (pypdfium2)':44} "
          f"{hit(doc[0].get_textpage().get_text_bounded())}")

    r = PdfReader(p)
    urls = []
    for pg in r.pages:
        for a in pg.get("/Annots", []) or []:
            action = a.get_object().get("/A") or {}
            if action.get("/URI"):
                urls.append(str(action["/URI"]))
    print(f"{'pypdf /Annots -> /A -> /URI':44} {hit(urls)} -> {urls}")

    tp = doc[0].get_textpage()
    print(f"{'pypdfium2 textpage.get_links()':44} "
          f"{tp.get_links() if hasattr(tp, 'get_links') else 'no such method'}")
    import pypdfium2.raw as pdfium_c
    print(f"{'pypdfium2 raw FPDFLink_LoadWebLinks':44} "
          f"{hasattr(pdfium_c, 'FPDFLink_LoadWebLinks')}")


def section_c() -> None:
    print()
    print("=" * 92)
    print("C. CHARACTER / FONT GEOMETRY")
    print("=" * 92)
    with pdfplumber.open(str(COL_ORDERED)) as pdf:
        ch = pdf.pages[0].chars[0]
        print("pdfplumber char keys:", sorted(k for k in ch if k in
              {"x0", "x1", "top", "bottom", "fontname", "size", "matrix", "upright", "text"}))
        print(f"  sample: text={ch['text']!r} font={ch['fontname']!r} size={ch['size']:.1f}")

    doc = pdfium.PdfDocument(str(COL_ORDERED))
    tp = doc[0].get_textpage()
    print(f"pypdfium2 get_charbox(0): {tp.get_charbox(0)}")
    print("pypdfium2 font name/size: raw ctypes only "
          "(FPDFText_GetFontInfo / FPDFText_GetFontSize)")

    fields = PdfReader(str(COL_ORDERED)).get_fields()
    print(f"pypdf get_fields(): {fields}")


def section_d() -> None:
    print()
    print("=" * 92)
    print("D. TEXT-LAYER / SCANNED-PAGE DETECTION (page 2 is a bare image)")
    print("=" * 92)
    with pdfplumber.open(str(COL_ORDERED)) as pdf:
        p0, p1 = pdf.pages[0], pdf.pages[1]
        print(f"pdfplumber page1: chars={len(p0.chars)}, images={len(p0.images)}")
        print(f"pdfplumber page2: chars={len(p1.chars)}, images={len(p1.images)}")

    doc = pdfium.PdfDocument(str(COL_ORDERED))
    print(f"pypdfium2 count_chars page1: {doc[0].get_textpage().count_chars()}")
    print(f"pypdfium2 count_chars page2: {doc[1].get_textpage().count_chars()}")

    r = PdfReader(str(COL_ORDERED))
    print(f"pypdf page2 stripped text length: {len(r.pages[1].extract_text().strip())}")
    print(f"pypdf is_encrypted: {r.is_encrypted}")


if __name__ == "__main__":
    for f in (COL_ORDERED, INTERLEAVED):
        if not f.exists():
            raise SystemExit(f"missing {f} - run make_pdf.py and make_pdf2.py first")
    section_a()
    section_b()
    section_c()
    section_d()
