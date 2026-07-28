# Document extraction probes

These scripts produce every measurement labelled **[measured here]** in
[`../../document-extraction-research.md`](../../document-extraction-research.md) —
the multi-column reading-order matrix in §1.4 and the DOCX capability matrix in §4.

They exist so those tables can be re-checked rather than trusted.

## Running

```bash
pip install pdfplumber pypdfium2 pypdf pdfminer.six reportlab \
            python-docx docx2python docx2txt mammoth

cd docs/research/document-extraction-probes
python3 make_pdf.py && python3 make_pdf2.py && python3 test_pdf.py
python3 make_docx.py && python3 test_docx.py
```

Generated fixtures land in `out/`, which is gitignored.

Apache Tika is opt-in, since it needs a JVM and a ~55 MB JAR:

```bash
curl -sLo /tmp/tika-app.jar \
  https://repo1.maven.org/maven2/org/apache/tika/tika-app/3.2.3/tika-app-3.2.3.jar
TIKA_JAR=/tmp/tika-app.jar python3 test_docx.py
```

Without `TIKA_JAR` the two Tika rows report `SKIPPED` and everything else still runs.

## What each script does

| Script | Purpose |
|---|---|
| `make_pdf.py` | `resume_2col.pdf` — 2-column resume, `L1…L5` left / `R1…R6` right, content stream **column-ordered**; two link annotations whose target URLs are absent from the visible text; page 2 is a bare image (synthetic scan) |
| `make_pdf2.py` | `resume_2col_interleaved.pdf` — same visual layout, content stream written **line-by-line across columns** |
| `test_pdf.py` | reading order (9 extraction modes × both streams), hyperlink recovery, char/font geometry, text-layer detection. Contains the reference `find_gutter()` implementation |
| `make_docx.py` | `resume_probe.docx` with 7 planted markers: body paragraph, 2-col table, header, footer, `w:hyperlink` whose anchor ≠ URL, floating text box (`mc:AlternateContent` → `wps:txbx` → `w:txbxContent`) |
| `test_docx.py` | runs 8 extractors (6 Python + Tika `--text`/`--html`) and prints the FOUND/MISS matrix |

## How the reading-order verdict is decided

Mechanically, not by eye. `test_pdf.py` pulls the ordered sequence of `L`/`R` markers
out of the extracted text and run-length encodes it. `Lx5Rx6` means the left column
came out as one block followed by the right column — correct. Anything with more than
two runs (`Lx1Rx1Lx1Rx1…`) means the columns were zipped together, which is what
destroys resume parsing.

## Caveat

**These PDFs are synthetic and deliberately clean.** They establish that the failure
mode exists and that the geometric fix works — not the rate at which it occurs in real
traffic. Before acting on the recommendations, re-run `test_pdf.py` against 50 real
resumes from your own funnel.
