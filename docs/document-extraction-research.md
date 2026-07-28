# Document Extraction Stack for the Resume Parsing Engine — Research Report

**Date:** 2026-07-28
**Scope:** production document extraction for a commercial, closed-source SaaS resume parser. Python 3.11, FastAPI backend.
**Status of current code:** `backend/app/resume_parser/extractor.py` uses `pdfplumber.extract_text()` for PDF and `python-docx` `.paragraphs` for DOCX. **Both have demonstrable, measured failure modes on real resume layouts.** See [§0](#0-headline-findings) and [§9](#9-reproducing-the-experiments).

Every factual claim below carries a URL. Where a claim comes from vendor content-marketing rather than a neutral source, it is labelled **[vendor]**. Where a number is my own measurement, it is labelled **[measured here]** and the script is included in [§9](#9-reproducing-the-experiments).

---

## 0. Headline findings

1. **No PDF text-extraction library gets multi-column reading order right.** I built two visually identical two-column resume PDFs — one whose content stream is written column-by-column, one written line-by-line across both columns — and ran seven extraction modes across four libraries against both. On the second PDF, **all seven modes interleaved the columns**, producing garbage like `L2 Built the payments platform R3 Python, Go, Postgres`. A ~25-line geometric gutter detector layered on top of `pdfplumber`'s word boxes got **both** PDFs right. **[measured here]** This single result determines the whole architecture: the layout pass is your own code, not a library choice.

2. **The current `pdfplumber.extract_text()` call is the worst-case default for this exact requirement.** It interleaved columns on both test PDFs. `layout=True` did not help. `use_text_flow=True` fixed one of the two. **[measured here]**

3. **PyMuPDF is off the table.** It is AGPL-3.0 unless you buy a commercial licence from Artifex, whose commercial terms are per-copy with a quarterly minimum fee and are quoted per use case with no published price ([artifex.com/licensing](https://artifex.com/licensing)). For a closed-source SaaS the AGPL network-use clause reaches your entire application. Details and the full landmine list in [§7](#7-licensing-landmines-read-this-section).

4. **The current DOCX path silently drops most of a designed resume.** `python-docx` `.paragraphs` alone found only 2 of my 7 planted markers — it missed tables, headers, footers, hyperlink URLs and text boxes. `docx2python` found **all 7**; Apache Tika found all 7. **[measured here]** Full matrix in [§4](#4-docx-extraction-measured).

5. **The best open resume-NER model on Hugging Face scores 97.77% entity F1 on clean text and 69.24% on OCR/scraped text** ([oksomu/resume-ner](https://huggingface.co/oksomu/resume-ner)). That 28-point gap is the value of your extraction layer. It is where the engineering effort belongs.

6. **AWS Textract, by default, may ship your content to a different AWS region** for service improvement unless you file an org-wide opt-out ([Textract FAQs](https://aws.amazon.com/textract/faqs/)). For a product processing candidate PII under GDPR that is a blocking default, not a footnote.

---

## 1. Python PDF text extraction libraries

### 1.1 Licensing (verified against primary sources)

| Library | Licence | Verified at | Commercial-SaaS safe? |
|---|---|---|---|
| **PyMuPDF** (`fitz`) | **AGPL-3.0 OR Artifex commercial** | PyPI metadata reads literally `Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License` ([pypi](https://pypi.org/project/pymupdf/1.28.0/)); [`COPYING`](https://github.com/pymupdf/PyMuPDF/blob/main/COPYING) is the AGPL-3.0 text | **NO** without a paid licence |
| **pdfplumber** | MIT | [github.com/jsvine/pdfplumber](https://github.com/jsvine/pdfplumber) | Yes |
| **pdfminer.six** | MIT | [github.com/pdfminer/pdfminer.six](https://github.com/pdfminer/pdfminer.six) | Yes |
| **pypdfium2** | `Apache-2.0 OR BSD-3-Clause` (binding) over PDFium's BSD-style licence | [pypi](https://pypi.org/project/pypdfium2/); [README](https://github.com/pypdfium2-team/pypdfium2) | Yes, **with an attribution obligation** — see note below |
| **pypdf** (successor to PyPDF2) | BSD-3-Clause | [`pyproject.toml`](https://github.com/py-pdf/pypdf/blob/main/pyproject.toml) declares `license = "BSD-3-Clause"`; [`LICENSE`](https://github.com/py-pdf/pypdf/blob/main/LICENSE) is the 3-clause text | Yes |
| **Camelot** (`camelot-py` 2.0.0) | MIT | [`LICENSE`](https://github.com/camelot-dev/camelot/blob/master/LICENSE) | Yes |
| **tabula-py** | MIT (requires a Java runtime) | [analysis](https://www.quickbankconvert.com/blog/developer-tools/tabula-py-license-explained) **[vendor]**, corroborated by [py-pdf/benchmarks](https://github.com/py-pdf/benchmarks) listing Tika/Java tooling separately |
| **borb** | **AGPL-3.0-or-later** OR paid | [pypi](https://pypi.org/project/borb/) declares `AGPL-3.0-or-later`; [pricing](https://borbpdf.com/pricing.html) is €250–5,000/yr by document volume | **NO** without a paid licence |

**pypdfium2 attribution obligation.** The README states: *"PDFium's license as well as dependency licenses have to be shipped with binary distributions."* Its [`REUSE.toml`](https://github.com/pypdfium2-team/pypdfium2/blob/main/REUSE.toml) adds a notable caution — PDFium's own LICENSE file contains **both** BSD-3-Clause and Apache-2.0 texts, and the pypdfium2 maintainers say *"We're not sure if this meant as SPDX 'AND' or 'OR', so use the conservative (safe) assumption 'AND'."* Practically: bundle the `BUILD_LICENSES/` directory contents in your image and in any third-party notices file. This is cheap; just don't forget it.

**Camelot correction.** Common lore says Camelot drags in AGPL Ghostscript. As of `camelot-py` 2.0.0 that is **no longer true by default** — core dependencies are `pypdfium2`, `playa-pdf`, `opencv-python-headless`, `pandas`. Ghostscript is an opt-in extra (`extra == "ghostscript"`). **[measured here — read from the PyPI JSON metadata for 2.0.0]** Don't install that extra and you have no AGPL exposure from Camelot.

### 1.2 Published speed benchmarks

**The neutral one — [py-pdf/benchmarks](https://github.com/py-pdf/benchmarks)** (maintained by the pypdf org; 14 PDFs, 425 pages, mostly arXiv papers, Intel i7-6700HQ). Text-extraction wall time, average per document:

| Rank | Library | Average | Slowest single doc (117-page book) |
|---|---|---|---|
| 1 | PyMuPDF | 0.1 s | 0.3 s |
| 2 | pypdfium2 | 0.1 s | 0.3 s |
| 3 | Tika | 0.2 s | 0.5 s |
| 4 | pdftotext (poppler, GPL) | 0.3 s | 0.9 s |
| 5 | pypdf | 3.5 s | 6.4 s |
| 6 | pdfminer.six | 5.8 s | 16.6 s |
| 7 | **pdfplumber** | **9.5 s** | 16.6 s |

Same benchmark, text-extraction *quality* against ground truth:

| Rank | Library | Average |
|---|---|---|
| 1 | pypdfium2 | 97% |
| 2 | pypdf | 96% |
| 3 | PyMuPDF | 96% |
| 4 | Tika | 95% |
| 5 | pdftotext | 91% |
| 6 | pdfminer.six | 89% |
| 7 | **pdfplumber** | **75%** |

**Read that 75% with care.** In [pdfplumber discussion #955](https://github.com/jsvine/pdfplumber/discussions/955) the pdfminer.six maintainer raised these numbers, and pdfplumber's author replied that *"some seems to be more a matter of expectations rather than accuracy"*; a specific bug (`use_text_flow` not being respected by `extract_text`) was fixed in [#983](https://github.com/jsvine/pdfplumber/pull/983), with updated results at [dhdaines/benchmarks](https://github.com/dhdaines/benchmarks). The same discussion notes the ground-truth texts are *"of unknown origin"*. Treat the ordering as directionally right and the absolute gap as unsettled.

**Vendor benchmarks** (useful, but the authors sell competing products):

- [pdfmux](https://pdfmux.com/blog/pymupdf-vs-pdfplumber/) **[vendor]**, 1,422 real pages: PyMuPDF 180 pages/s vs pdfplumber 18 pages/s plain text (10×); text+bboxes 95 vs 22 pages/s; table extraction 45 vs 8 pages/s; memory per 100 pages 45 MB vs 180 MB. Table accuracy inverts: TEDS 0.692 (PyMuPDF) vs 0.847 (pdfplumber).
- [PDF Oxide](https://pdf.oxide.fyi/docs/performance) **[vendor]**, 3,830-PDF corpus, mean per PDF: PDF Oxide 0.8 ms, pypdfium2 4.1 ms, PyMuPDF 4.6 ms, pdftext 7.3 ms (GPL-3.0), pypdf 12.1 ms, pdfminer 16.8 ms, pdfplumber 23.2 ms, pymupdf4llm 55.5 ms.
- [PyMuPDF's own](https://pymupdf.readthedocs.io/en/latest/about.html) **[vendor]**, 7,031 pages: plain-text extraction 8.01 s (PyMuPDF) vs 227.27 s (PyPDF2).

**Why the speed gap matters much less than it looks for resumes.** These benchmarks measure throughput on 100+ page documents. A resume is 1–2 pages. Interpolating from the py-pdf benchmark's smallest inputs (7–9 pages: pdfplumber 2.3–2.5 s), a 2-page resume costs pdfplumber roughly 0.3–0.7 s. On an async upload endpoint that is invisible. **Do not trade licence safety or API richness for a speed difference you cannot perceive at your document size.**

### 1.3 Capability matrix — what you can actually get out

Verified by running each API. **[measured here]**

| Capability | pdfplumber | pdfminer.six | pypdfium2 | pypdf | PyMuPDF |
|---|---|---|---|---|---|
| **Character-level bbox** | ✅ `page.chars[i]` → `x0/x1/top/bottom` | ✅ `LTChar.bbox` | ✅ `PdfTextPage.get_charbox(i)` — verified returns `(60.19, 719.80, 64.71, 727.90)` | ⚠️ via `visitor_text` callbacks only | ✅ `get_text("rawdict")` |
| **Font name** | ✅ `char["fontname"]` → `'Helvetica'` | ✅ `LTChar.fontname` | ⚠️ **raw ctypes only** — `pypdfium2.raw.FPDFText_GetFontInfo` (verified → `'Helvetica'`); not in the high-level API | ❌ | ✅ |
| **Font size** | ✅ `char["size"]` → `11.0` | ✅ `LTChar.size` | ⚠️ raw only — `FPDFText_GetFontSize` (verified → `11.0`) | ❌ | ✅ |
| **Weight / style flags** | ⚠️ infer from `fontname` substring (`"-Bold"`) | ⚠️ same | ⚠️ `FPDFText_GetFontInfo` flags out-param (verified → `32`) | ❌ | ✅ `flags` bitfield in `get_text("dict")` |
| **Word positions** | ✅ `extract_words()` | ✅ `LTTextLine` children | ⚠️ derive from charboxes | ⚠️ | ✅ |
| **Rotation / CTM** | ✅ `char["matrix"]`, `char["upright"]`, plus a `pdfplumber.ctm.CTM` helper ([README](https://github.com/jsvine/pdfplumber/blob/stable/README.md)) | ✅ | ⚠️ | ❌ | ✅ |
| **Reading order** | ❌ see §1.4 | ❌ see §1.4 | ❌ see §1.4 | ❌ see §1.4 | ❌ see §1.4 |
| **Table structure** | ✅ best-in-class `extract_tables()`, TEDS 0.847 **[vendor]** | ❌ | ❌ | ❌ | ✅ (TEDS 0.692 **[vendor]**) |
| **Links / annotations** | ✅ **`page.hyperlinks`** and **`page.annots`** — verified recovered both hidden URLs | ❌ | ❌ no link API on `PdfTextPage`; verified public API is only `close, count_chars, count_rects, get_charbox, get_index, get_rect, get_text_bounded, get_text_range, get_textobj, parent, search`. Raw `FPDFLink_LoadWebLinks` / `FPDFLink_GetLinkAtPoint` exist | ✅ `/Annots → /A → /URI`, verified | ✅ `page.get_links()` |
| **Form-field text** | ⚠️ no API; the [README documents](https://github.com/jsvine/pdfplumber/blob/stable/README.md) a working AcroForm walk via pdfminer wrappers (`pdf.doc.catalog["AcroForm"]`) | ⚠️ raw | ⚠️ raw | ✅ `get_fields()` | ✅ |
| **Text-layer / scanned detection** | ✅ `len(page.chars) == 0` — verified 0 on an image-only page | ✅ | ✅ `count_chars() == 0` — verified 0 | ✅ `extract_text() == ""` — verified | ✅ |

**Hyperlink extraction is the single strongest argument for keeping pdfplumber.** LinkedIn and GitHub URLs on resumes are almost always hidden behind anchor text. I built a PDF whose visible text reads `LinkedIn Profile` and `GitHub` while the link destinations are `linkedin.com/in/janedoe-hidden` and `github.com/janedoe-hidden`. Neither URL appears in *any* library's extracted plain text. `page.hyperlinks` returned both. `pypdf`'s `/Annots` walk returned both. `pypdfium2`'s text page returned `None`. **[measured here]**

### 1.4 Reading order: the finding that decides the architecture

I generated two PDFs with identical visual output — a two-column resume with markers `L1…L5` in the left column and `R1…R6` in the right — differing only in **content-stream write order**:

- `resume_2col.pdf` — all of the left column written, then all of the right (what LaTeX and some template engines emit).
- `resume_2col_interleaved.pdf` — line 1 left, line 1 right, line 2 left, line 2 right… (what many Word/Canva/HTML-to-PDF exports emit).

"Column-blocked" = every `L` before every `R`. "Interleaved" = the columns got zipped together.

| Extraction mode | column-ordered stream | interleaved stream |
|---|---|---|
| `pdfplumber.extract_text()` **(current production code)** | ❌ interleaved | ❌ interleaved |
| `pdfplumber.extract_text(layout=True)` | ❌ interleaved | ❌ interleaved |
| `pdfplumber.extract_text(use_text_flow=True)` | ✅ correct | ❌ interleaved |
| `pdfminer.six extract_text()` (default LAParams) | ❌ interleaved | ❌ interleaved |
| `pdfminer.six boxes_flow=-1.0` (strict column mode) | ❌ interleaved | ❌ interleaved |
| `pypdfium2 get_text_bounded()` | ✅ correct | ❌ interleaved |
| `pypdf extract_text()` | ✅ correct | ❌ interleaved |
| `pypdf extract_text(extraction_mode="layout")` | ❌ interleaved | ❌ interleaved |
| **custom gutter detector over `pdfplumber.extract_words()`** | ✅ **correct** | ✅ **correct** |

**[measured here]** — all rows.

The gutter detector is about 25 lines: find the widest vertical band in the middle 50% of the page that no word box crosses, then `page.crop()` left and right of it and extract each side separately. That's it. A working reference implementation is checked in as `find_gutter()` in [`test_pdf.py`](research/document-extraction-probes/test_pdf.py).

This is not a surprising result once you see why. Every library either sorts by `(y, x)` — which walks across columns — or trusts the content stream, which is arbitrary. PyMuPDF's maintainer says it plainly in [discussion #1901](https://github.com/pymupdf/PyMuPDF/discussions/1901):

> *"There never is a guarantee that `sort=True` will deliver text in a sequence you like. The reason is how PDF works … Every single character can be stored internally in arbitrary sequence. … PyMuPDF is not aware of the 2-column page layout."*

The best library-side tooling for this is PyMuPDF's, and it is explicitly a **separate utility script, not a core feature**: [`multi_column.py`](https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/text-extraction/multi_column.py) returns column boundary boxes for you to clip and extract. [Artifex's own writeup](https://artifex.com/blog/extract-text-from-a-multi-column-document-using-pymupdf-inpython) lists its limitations: horizontal left-to-right text only, *"depends on some fairly properly designed page layouts"*, *"pages with overlaps between boundary boxes are likely to cause errors"*, and no image-caption handling. `pymupdf4llm`'s `get_text_lines` is the newer answer ([discussion #3552](https://github.com/pymupdf/PyMuPDF/discussions/3552)). Both are AGPL. **The point is that even the market leader solves this with a geometric heuristic on top of the parser — so you can too, in MIT-licensed code.**

Note also that **the neutral speed/quality benchmark corpus is mostly two-column arXiv papers**, which is part of why pdfplumber scores 75% on quality there. The metric is partly measuring the exact problem you have to solve yourself anyway.

---

## 2. Document AI and layout-aware toolkits

### 2.1 Licences and maturity (verified via the GitHub API on 2026-07-28)

| Tool | Code licence | Weights licence | Stars | Last push | Verdict |
|---|---|---|---|---|---|
| **Docling** (IBM) | **MIT** | per-model; README: *"For individual model usage, please refer to the model licenses found in the original packages"* | 63,888 | 2026-07-28 | ✅ best-governed option |
| **Unstructured** | Apache-2.0 | n/a | 15,209 | 2026-07-26 | ✅ safe, slower |
| **Marker** (Datalab) | **Apache-2.0** (changed from GPL-3.0) | **modified AI Pubs Open RAIL-M — free only for research, personal use, and startups under $5M funding/revenue** | 37,966 | 2026-07-20 | ⚠️ **weights landmine** |
| **Surya** (Datalab) | Apache-2.0 | **same $5M OpenRAIL-M ceiling** | 21,167 | 2026-07-23 | ⚠️ **weights landmine** |
| **MinerU** | **MinerU Open Source License** = Apache-2.0 + additional terms | included | 75,962 | 2026-07-28 | ⚠️ attribution duty; thresholds are generous |
| **Nougat** (Meta) | MIT | **CC-BY-NC-4.0 — non-commercial** | 10,052 | **2025-02-21** | ❌ unmaintained **and** non-commercial |
| **LayoutParser** | Apache-2.0 | varies | 5,767 | **2024-08-15** | ❌ effectively unmaintained |
| **Tesseract** | Apache-2.0 (+ Leptonica BSD-2) | n/a | 75,484 | 2026-07-21 | ✅ |
| **PaddleOCR** | Apache-2.0 | Apache-2.0 | 86,353 | active | ✅ |
| **RapidOCR** | Apache-2.0 | ONNX ports of PaddleOCR models; README notes *"the copyright of the OCR model is held by Baidu"* | 6,873 | 2026-06-17 | ✅ |
| **EasyOCR** | Apache-2.0 | Apache-2.0 | — | — | ✅ but slow, see §2.4 |
| **docTR** (Mindee) | Apache-2.0 | Apache-2.0 | 6,195 | 2026-07-28 | ✅ |
| **LlamaParse** | closed SaaS | n/a | n/a | n/a | commercial, see §3 |

**Marker's licence changed and most secondary sources are stale.** I fetched the raw files: [`datalab-to/marker/master/LICENSE`](https://raw.githubusercontent.com/datalab-to/marker/master/LICENSE) is now Apache-2.0, and the README's Commercial usage section reads *"Our code is licensed under **Apache 2.0** — free to use, including commercially. Our model weights use a modified AI Pubs Open Rail-M license (free for research, personal use, and startups under $5M funding/revenue)."* The old mirror [`vikparuchuri/marker`](https://github.com/vikparuchuri/marker) still shows GPL-3.0 and a **$2M** threshold, and several 2026 blog posts repeat the GPL figure. Surya is identical: Apache-2.0 code, OpenRAIL-M weights, $5M ceiling ([raw README](https://raw.githubusercontent.com/datalab-to/surya/master/README.md)).

**MinerU also changed, in the opposite direction — for the better.** It moved from AGPLv3 to a custom Apache-2.0-based licence in release 3.1.0 ([release notes](https://github.com/opendatalab/MinerU/releases/tag/mineru-3.1.0-released)). The [current LICENSE.md](https://github.com/opendatalab/MinerU/blob/mineru-3.1.7-released/LICENSE.md) requires a separate commercial licence only above **100M MAU or USD 20M monthly revenue**, and adds: *"If you provide online services to third parties based on MinerU, you must clearly and prominently indicate, in the relevant product or service interface or in publicly available documentation, that MinerU is used."* Non-compliance **terminates the licence automatically**. Old issues like [#4060](https://github.com/opendatalab/MinerU/issues/4060) describing AGPL + a CC-BY-NC-SA `layoutreader` are now obsolete; the release notes state the AGPL and CC-BY-NC-SA models were removed.

### 2.2 Docling in detail

- **Models.** Layout analysis (an object detector trained on DocLayNet) + **TableFormer** for table structure ([Docling technical report](https://arxiv.org/html/2408.09869v3), [AAAI version](https://arxiv.org/html/2501.17887)). The default layout model as of v2.50.0 is **`heron`**, RT-DETRv2-r50vd, **42.9M params**; alternatives are `heron-101` (76.7M), `egret-medium/large/xlarge` (19.5/31.2/62.7M) ([Advanced Layout Analysis Models for Docling](https://arxiv.org/html/2509.11720), [model catalog](https://docling-project.github.io/docling/usage/model_catalog/), [HF card](https://huggingface.co/docling-project/docling-layout-heron)).
- **PDF backend.** A custom parser, `docling-parse`, built on **qpdf** — not PyMuPDF, and not pypdfium2 by default. The paper is unusually blunt about why: *"we ran into various limitations, among which are restrictive licensing (e.g., pymupdf), poor speed, or unrecoverable quality issues, such as merged text cells across far-apart text tokens or table columns (pypdfium, PyPDF)."* **That sentence is a direct warning about using pypdfium2 as your only text source on multi-column resumes**, and it independently corroborates my measurement in §1.4.
- **CPU-only?** Yes. Supported devices for all layout models are CPU, CUDA, MPS, XPU; TableFormer supports CPU, CUDA, XPU (MPS disabled for performance) ([model catalog](https://docling-project.github.io/docling/usage/model_catalog/)).
- **Latency** ([technical report](https://www.arxiv.org/pdf/2408.09869v4), 8-thread budget via `OMP_NUM_THREADS`):

  | Configuration | 5th pct | median | 95th pct |
  |---|---|---|---|
  | x86 CPU | 0.6 s/page | **0.79 s/page** | 16.3 s/page |
  | M3 Max SoC | 0.26 s | 0.32 s | 6.48 s |
  | Nvidia L4 GPU | 57 ms | 114 ms | 2081 ms |

  Mean per-page cost with everything on: **3.1 s x86 CPU**, 1.26 s M3 Max, 481 ms L4. Component breakdown per page/table: OCR (EasyOCR) **13 s x86 CPU** / 5 s M3 / 1.6 s L4; layout model 633 ms / 271 ms / 44 ms; TableFormer-fast 1.74 s / 704 ms / 400 ms per *table*; `docling-parse` 81 ms / 44 ms (no GPU path). **Disabling OCR saves 60% of runtime on CPU; disabling OCR and table structure together saves ~75%.** For resumes with a text layer that means ~0.8 s/page on a server CPU.
  Layout-model-only amortized inference, AMD EPYC 7763 ([layout paper](https://arxiv.org/html/2509.11720) Table 5): egret-m 0.334 s/img, heron 0.643 s/img, heron-101 0.988 s/img. On A100: 0.024 / 0.030 / 0.174 s/img.
- **Reading order.** A dedicated stage — [`ReadingOrderModel`](https://github.com/docling-project/docling/blob/main/docling/models/stages/reading_order/readingorder_model.py) wrapping a `ReadingOrderPredictor`, which also predicts caption, footnote and merge relationships. **Caveat, from review comments on [PR #3233](https://github.com/docling-project/docling/pull/3233):** *"The 15% dilation threshold is fixed and **not user-configurable**, which can cause issues with complex multi-column layouts"* and *"Reading order quality depends heavily on the accuracy of upstream layout detection."* A `do_reading_order=False` escape hatch now exists. So Docling is much better than any text-extraction library here, but it is not a guarantee — validate it on your own resume corpus.
- **OCR engines available:** Tesseract (CLI or tesserocr), EasyOCR, RapidOCR, macOS Vision, SuryaOCR, and `Auto` ([model catalog](https://docling-project.github.io/docling/usage/model_catalog/)). Note that selecting SuryaOCR pulls Datalab's OpenRAIL-M weights into your stack — see §7.

### 2.3 Cross-tool speed comparison (Docling paper, same corpus and hardware)

| Tool | x86 CPU | M3 Max | L4 GPU |
|---|---|---|---|
| Docling | **3.1 s/page** | 1.27 s/page | 0.49 s/page |
| MinerU | 3.3 s/page | did not complete | **0.21 s/page** |
| Unstructured (`hi_res`) | 4.2 s/page | 2.7 s/page | no GPU benefit |
| Marker | **16+ s/page** | 4.2 s/page | 0.86 s/page |

Source: [Docling technical report](https://www.arxiv.org/pdf/2408.09869v4). Self-reported by the Docling team — a competitor of the other three. Directionally consistent with the fact that Marker runs a 650M-param VLM (Surya) per page.

### 2.4 Benchmarks: OmniDocBench, DocLayNet, PubLayNet

**[OmniDocBench](https://github.com/opendatalab/OmniDocBench)** is the relevant one: 1,651 PDF pages, 10 document types, 5 layout types, **with reading-order annotations**. `Overall = ((1 − TextEditDistance) × 100 + TableTEDS + FormulaCDM) / 3`. Selected v1.6_full rows, with the column that matters most for resumes:

| Method | Type | Size | Overall ↑ | Text Edit ↓ | Table TEDS ↑ | **Read Order Edit ↓** |
|---|---|---|---|---|---|---|
| MinerU2.5-Pro | Specialized VLM | 1.2B | **95.75** | 0.036 | 93.42 | **0.120** |
| GLM-OCR | Specialized VLM | 0.9B | 95.22 | 0.044 | 92.83 | — |
| PaddleOCR-VL | Specialized VLM | 0.9B | 94.18 | 0.040 | 90.65 | 0.135 |
| MinerU-2.5 | Specialized VLM | 1.2B | 93.04 | 0.045 | 87.88 | 0.130 |
| Gemini 3 Pro | General VLM | — | 92.91 | 0.064 | 89.15 | 0.165 |
| Gemini 3 Flash | General VLM | — | 92.62 | 0.066 | 89.29 | 0.172 |
| GPT-5.2 | General VLM | — | 86.59 | 0.114 | 82.95 | 0.193 |
| MinerU-Pipeline | Pipeline tool | — | 86.47 | 0.055 | 81.88 | 0.153 |
| Mistral OCR | Specialized VLM | — | 85.66 | 0.097 | 76.78 | 0.171 |
| **Marker** | Pipeline tool | — | **78.44** | 0.157 | 65.77 | **0.243** |

Also useful, an independent re-run on OmniDocBench v1.5 by Nanonets ([IDP Leaderboard](https://benchmarking.nanonets.com/benchmarks/omnidocbench)) which places Gemini-3-Flash first at 90.1 overall / 0.081 read order, and **Datalab Marker at 85.5 / 0.106** — materially better than the v1.6 figure above, illustrating how much these numbers move between dataset versions.

**Two caveats you should carry forward.** First, OmniDocBench is published by OpenDataLab, who also ship MinerU; olmOCR-Bench is published by AI2, who ship olmOCR. As one review puts it, *"the numbers aren't fabricated; the people producing them are also competitors"* ([analysis](https://dreaming.press/posts/2026-06-22-olmocr-vs-marker-vs-mineru-vs-mistral-ocr.html)). Second, and more important for you: these benchmarks lead with **text edit distance**, and *"it is nearly the least relevant one for retrieval, because all four tools are already good at transcribing clean text. The differences that survive are structural."* For resumes, weight **Read Order Edit** far above Overall.

**Docling is absent from the v1.6 leaderboard** (it was evaluated in v1.0/v1.5 per the [changelog](https://github.com/opendatalab/OmniDocBench)). Treat that as missing data, not a bad score. Its layout model quality is documented separately: `heron-101` reaches **78% mAP** on canonical DocLayNet, a 23.9% improvement over Docling's prior model ([layout paper](https://arxiv.org/html/2509.11720)). The same paper's honest conclusion — *"mAP may not always be a suitable metric to evaluate the layouts of documents"* — is worth remembering before you buy a decision on mAP.

---

## 3. Cloud document AI — 2026 published pricing

All figures are per 1,000 pages in USD from the vendors' own pricing pages unless marked otherwise.

### 3.1 Azure AI Document Intelligence (formerly Form Recognizer)

Source: [azure.microsoft.com/en-gb/pricing/details/ai-document-intelligence](https://azure.microsoft.com/en-gb/pricing/details/ai-document-intelligence/) (the `en-us` variant renders prices as `$-`; use the `en-gb` page).

| SKU | Price / 1,000 pages |
|---|---|
| Free tier (F0) | 0–500 pages/month free |
| **Read** (OCR only) | **$1.50** (0–1M), **$0.60** (1M+) |
| **All Prebuilt models** — Document, **Layout**, Receipt, Invoice, ID, W-2, 1098, Health card, Contract | **$10.00** |
| Custom classification | $3.00 |
| Custom extraction | $30.00 |
| Custom generative extraction | $30.00 |
| Add-on (high-res, font, formula, barcode) | $6.00 |
| Query Fields | $10.00 |
| Training | $3.00 / hour |

Commitment tiers: Read $375/500k (**$0.75**/1k), $1,200/2M ($0.60), $4,200/8M ($0.53). Prebuilt $190/20k (**$9.50**/1k), $900/100k ($9.00), $4,000/500k ($8.00). Batch SKUs are priced identically to synchronous.

**Is there a relevant prebuilt or custom model?** There is **no resume/CV prebuilt model.** The relevant SKU is **`prebuilt-layout` at $10/1k** — it is what gives you reading order, paragraph roles, tables and selection marks. `prebuilt-read` at $1.50/1k is OCR text only. Custom extraction ($30/1k + $3/hr training) would let you train on your own resume corpus, but at 20× the Layout price and with a training-data-labelling burden; not worth it as a fallback path.

One secondary caution: [parsli](https://parsli.co/compare/azure-document-intelligence) **[vendor]** reports the F0 free tier *"caps each request to the first 2 pages"*, which would make it useless for evaluation on multi-page resumes. Verify before you build a test harness on F0.

**Data residency / retention.** From [Microsoft's own responsible-AI documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/responsible-ai/document-intelligence/data-privacy-security): *"The incoming data is processed in the same region where the Document Intelligence resource was created."* Results are *"temporarily encrypted and stored in Azure Storage"* **in the same region**, shared temporary storage logically isolated per subscription. *"Analyze response is stored for 24 hours from when the operation completes"* and the **Delete Analyze Result API permanently purges** it. This is the clearest in-region commitment of the four hyperscalers — a Microsoft Q&A response describes it as *"a fully documented guarantee that all processing occurs in the same region"*, in contrast to Azure OpenAI ([Q&A](https://learn.microsoft.com/en-us/answers/questions/5679952/clarification-on-india-only-data-residency-for-azu)). For GDPR, deploy in West Europe / North Europe and call the delete API immediately after retrieving results.

### 3.2 AWS Textract

Source: [aws.amazon.com/textract/pricing](https://aws.amazon.com/textract/pricing/), US West (Oregon).

| API / feature | Price / 1,000 pages | Above 1M pages/month |
|---|---|---|
| **Detect Document Text** (OCR) | **$1.50** | $0.60 |
| Analyze Document — **Tables** | $15.00 | $10.00 |
| Analyze Document — **Forms** | $50.00 | $40.00 |
| Analyze Document — Queries | $15.00 | $10.00 |
| Analyze Document — Signatures | $3.50 | $1.40 |
| Analyze Expense | $10.00 | $8.00 |
| Analyze ID | $25.00 (first 100k) | $10.00 |
| Analyze Lending | $70.00 | $55.00 |
| **Layout** | **free when combined with Tables**; standalone reportedly $4.00 / $3.00 **[vendor — verify]** |

The Layout-with-Tables bundling is stated in the official pricing examples: *"Layout is available for free when used with the Tables feature."* The **standalone** Layout price of $4.00/1k (→$3.00 above 1M) comes from a [secondary source](https://updf.com/ocr/amazon-textract/) **[vendor]** because AWS's rate tables did not render in fetched HTML — **confirm in the AWS console before budgeting on it.** Free tier: 3 months, 1,000 pages/month for Detect Document Text; only 100 pages/month for Forms/Tables/Layout.

**Data residency / retention — this is the problem.** From the [Textract FAQs](https://aws.amazon.com/textract/faqs/):

> *"Unless you opt out as provided below, **some portion of content processed by Amazon Textract may be stored in another AWS region** solely in connection with the continuous improvement and development of your Amazon Textract customer experience and other Amazon machine-learning/artificial-intelligence technologies."*

Opting out requires an [AI services opt-out policy](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_ai-opt-out.html) attached at the AWS Organizations root. Separately, **async operations store results for 7 days in a Textract-owned S3 bucket by default**; synchronous operations are not stored ([AWS re:Post, answered by AWS](https://repost.aws/questions/QUC2dodjUnSuuRcSSTsmIfNw/how-long-are-textract-results-stored-for)). For candidate PII under GDPR: the org-wide opt-out is mandatory before first use, and prefer sync calls. This is more friction than Azure or Google impose.

### 3.3 Google Document AI

Source: [cloud.google.com/products/document-ai/pricing](https://cloud.google.com/products/document-ai/pricing).

| Processor | Price / 1,000 pages |
|---|---|
| **Enterprise Document OCR** | first 1,000/month free; **$1.50** (1k–5M); **$0.60** (5M+) |
| OCR add-ons (v2 only) | $6.00 |
| **Layout Parser** (includes initial chunking) | **$10.00** |
| **Form Parser** | **$30.00** (0–1M); $20.00 above |
| Custom extractor | $30.00 (0–1M); $20.00 above |
| Custom splitter / classifier | $5.00 → $3.00 |
| Re-chunking parsed documents | $0.02 |
| Summarizer | $0.025 per call |

Watch the page-counting rule: **for DOCX, "up to 3,000 characters = 1 page"** — a text-dense 2-page resume can bill as 2–3 pages. Images are 1 page each; PDF is per page.

**Data residency / retention.** From [Document AI security and compliance](https://docs.cloud.google.com/document-ai/docs/security): *"For online (immediate response) operations, the document data … is processed in memory, encrypted in flight, and **not persisted to disk**."* Batch requests store the document *"encrypted with an ephemeral key, meaning that no human has access to it"*, typically deleted immediately with *"a failsafe Time to live (TTL) of one day."* Supported controls include **data residency, CMEK, VPC Service Controls, and Access Transparency**. Google's online path is the strongest no-retention story of the three hyperscalers; use `processDocument` (sync), not `batchProcessDocuments`, and pin an EU location.

### 3.4 Mistral OCR 4

Source: [mistral.ai/news/ocr-4](https://mistral.ai/news/ocr-4/).

| Mode | Price / 1,000 pages |
|---|---|
| OCR API (`mistral-ocr-latest`) | **$4.00** |
| Batch API | **$2.00** (50% off) |
| Document AI layer (schema-driven extraction, same engine) | **$5.00** |

Every request returns *"extracted content, bounding boxes, block types, confidence scores, and markdown-structured text"* — bboxes and per-block confidence come free, which matters for auditability. 170 languages. Available via Mistral Studio, Amazon SageMaker, Microsoft Foundry, and **self-hosting for enterprise** (*"For organizations with stringent data-privacy requirements, OCR 4 also offers a self-hosting option so sensitive information stays within your own infrastructure"*). OmniDocBench v1.6: Overall 85.66, Read Order Edit 0.171 — mid-pack, weakest on tables (TEDS 76.78).

**GDPR angle.** Mistral AI SAS is a **French** legal entity, so unlike AWS/Azure/GCP EU subsidiaries it is not itself subject to the US CLOUD Act (18 U.S.C. §2713). Retention is reported as *"prompts are retained for 30 days for abuse detection purposes, then deleted. Enterprise customers can request zero retention,"* and data location is *"hosted in Europe (primarily France and Germany)"* — but the same analysis notes *"Mistral has not publicly committed to a data residency SLA at the level of Azure 'EU Data Boundary'"* ([analysis](https://sota.io/blog/mistral-ai-eu-native-llm-api-gdpr-no-cloud-act-2026)) **[vendor — get this in writing in a DPA]**.

### 3.5 LlamaParse

Source: [developers.llamaindex.ai/llamaparse/general/pricing](https://developers.llamaindex.ai/llamaparse/general/pricing/). Credits: **1,000 credits = $1.25**, in **both North America and Europe** — so EU residency costs the same.

| Parse tier | Credits/page | Effective / 1,000 pages |
|---|---|---|
| Fast | 1 | **$1.25** |
| Cost-effective | 3 | $3.75 |
| Agentic | 10 | $12.50 |
| Agentic Plus | 45 | $56.25 |
| Layout extraction add-on | +3 | +$3.75 |

Free tier 10k credits/month; Starter 40k; Pro 400k ([plans](https://www.llamaindex.ai/pricing)). Note LlamaIndex's own framing: *"LlamaParse is our commercial platform … it is **not open source**."*

### 3.6 Reducto

Sources: [reducto.ai/pricing](https://reducto.ai/pricing), [credit usage reference](https://reducto.mintlify.app/reference/credit-usage). **$0.015 per credit** after the first 15,000 free.

| Operation | Credits/page | Effective / 1,000 pages |
|---|---|---|
| Standard parse (text, layout, simple tables, OCR) | 1 | **$15.00** |
| Complex (VLM-enhanced pages) | 2 | $30.00 |
| Agentic — standard / complex | 2 / 4 | $30 / $60 |
| Extract (schema-based) | 2 | $30.00 |
| Deep Extract (beta) | 4 + 0.1/field, min 30 credits/doc | ≥$0.45/doc |
| Batch queue | −20% credits, 12-hour completion guarantee | |

The most expensive per page of everything surveyed. Reducto's value is agentic accuracy on genuinely hard financial documents, which is not the resume problem.

### 3.7 Frontier VLMs used directly as OCR

Official token rates: **Gemini 3 Flash — $0.50 per 1M input tokens (text/image/video), $3.00 per 1M output** ([Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing), corroborated by [GCP agent-platform pricing](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing)). The paid tier states **"Used to improve our products: No."**

**My own arithmetic** on those official rates, assuming ~900 input tokens (image + prompt) and ~600 output tokens of structured markdown/JSON per resume page:

- input: 0.9M tokens × $0.50/M = $0.45
- output: 0.6M tokens × $3.00/M = $1.80
- **≈ $2.25 per 1,000 pages**

**Output tokens dominate the cost by 4×.** If you ask for verbose markdown you pay for it; a tight JSON schema is materially cheaper. A third-party estimate using 858 in / 500 out lands at $1.93/1k for a Flash-class model ([analysis](https://the-rogue-marketing.github.io/google-gemini-api-ocr-guide-pydantic-ai/)) **[vendor]** — consistent with mine.

For GPT-class vision, a normalized per-A4-page comparison puts **GPT-5.2 at ~$0.015/page image cost alone (= $15/1k)**, rising to ~$0.05/page total on dense pages once input and output tokens are added; Gemini 3 Flash at $0.0004/page image cost; Claude Sonnet ~$0.003/page ([DocsRouter](https://docs.docsrouter.com/blog/the-complete-guide-to-vision-llm-pricing-for-ocr)) **[vendor]**.

### 3.8 Cost summary at 10,000 resumes/month (~15,000 pages)

| Option | Rate / 1,000 pp | Monthly |
|---|---|---|
| Local pypdfium2 + pdfplumber + own layout pass | $0 | **$0** (compute only) |
| Local Docling on CPU | $0 | $0 + ~0.8 s/page CPU |
| Gemini 3 Flash as OCR (my estimate on official rates) | ~$2.25 | ~$34 |
| Mistral OCR 4 batch | $2.00 | $30 |
| Mistral OCR 4 sync | $4.00 | $60 |
| Azure DI Read / AWS Detect Text / Google OCR | $1.50 | $22.50 |
| LlamaParse Fast | $1.25 | $19 |
| **Azure DI prebuilt-layout** | **$10.00** | **$150** |
| Google Layout Parser | $10.00 | $150 |
| AWS Textract Tables (+free Layout) | $15.00 | $225 |
| Reducto standard | $15.00 | $225 |
| Google Form Parser | $30.00 | $450 |
| AWS Textract Forms | $50.00 | $750 |
| LlamaParse Agentic Plus | $56.25 | $844 |

At this volume the absolute numbers are small — which is exactly the trap. The reason not to go cloud-first is **not** the bill; it is latency on the critical path, an external dependency, and the GDPR posture. See [§8](#8-alternative-stack-designs-and-why-they-are-worse).

---

## 4. DOCX extraction (measured)

I built a DOCX exercising everything a designed resume actually uses — a body paragraph, a 2-column table, a header, a footer, a real `w:hyperlink` with a relationship whose URL differs from its anchor text, and a **floating text box** (`mc:AlternateContent` → `wps:txbx` → `w:txbxContent`) — and ran every candidate extractor against it. Versions: python-docx 1.2.0, docx2python 3.6.2, docx2txt 0.9, mammoth 1.12.0, Apache Tika 3.2.3.

| Extractor | body | table | header | footer | link anchor text | **link URL** | **text box** |
|---|---|---|---|---|---|---|---|
| `python-docx` `.paragraphs` only **(current code)** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `python-docx` thorough (paras + tables + sections + `p.hyperlinks`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **`docx2python` 3.6.2** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `docx2txt` 0.9 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| `mammoth` `extract_raw_text` | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `mammoth` `convert_to_html` | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **Apache Tika 3.2.3** `--text` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ *(via `--html`)* | ✅ |

**[measured here]** — all rows.

**Reading this table.** `docx2python` and Tika are the only two that get everything. Between them, `docx2python` is a pure-Python library with no JVM; Tika is a 55 MB JAR plus a JVM plus an IPC boundary. For a Python service that only needs DOCX, `docx2python` wins on operational simplicity.

### 4.1 python-docx limitations, precisely

- **Text boxes: not extracted.** Confirmed by measurement above.
- **SmartArt: not supported.** The maintainer, on [issue #1486](https://github.com/python-openxml/python-docx/issues/1486): *"Not directly, no. Basically there wasn't enough call for it and there was no documentation on that aspect of the schema… you could get a reference to the XML element with `shp._graphicFrame` and then parse that directly using `lxml` methods."* The [inline-shapes reference](https://deepwiki.com/python-openxml/python-docx/7.3-inline-shapes-and-drawings) confirms Chart, SmartArt and Drawing Canvas are all "Not currently supported".
- **Headers/footers: supported**, via `Section.header` / `Section.footer` ([docs](https://python-docx.readthedocs.io/en/latest/user/hdrftr.html)) — but you must iterate `document.sections` yourself; they are not in `document.paragraphs`.
- **Tables: supported**, via `document.tables` — again not in `document.paragraphs`.
- **Hyperlinks: supported since 1.2.0**, via `Paragraph.hyperlinks` → `Hyperlink.address` ([API docs](https://python-docx.readthedocs.io/en/latest/api/text.html)). `paragraph.text` includes the *visible* anchor text but not the address. One documented quirk: for internal jumps the address is blank and the bookmark lives in `.fragment`.

### 4.2 Other DOCX traps worth guarding against

Beyond what my probe covers, [this write-up](https://dev.to/ivyjsu/getting-clean-text-out-of-pdf-docx-and-html-cmn) catalogues the rest: text lives in `w:t` runs that **split mid-word at formatting boundaries** (`hyper` + `link` must be joined before tokenizing — a real risk for skill names and company names), and **tracked changes leave deleted text in `w:del` elements you must exclude** or you will extract text the candidate removed. Both are worth explicit tests in your suite.

### 4.3 Apache Tika

Tika does get text boxes, and you can see exactly where: `OfficeParserConfig.getIncludeShapeBasedContent()` gates an XPath of `.//*/wps:txbx/w:txbxContent//w:p` — and the descendant-axis `//` was a deliberate fix ([TIKA-2807](https://apache.googlesource.com/tika/+/06cf66cef14863fee0111dddefaebaa051a40c72%5E%21/), commit comment: *"must look for all descendant paragraphs, not just the immediate children of txbxContent"*). Headers and footers are gated by `getIncludeHeadersAndFooters()` ([WordExtractor.java](https://github.com/apache/tika/blob/master/tika-parsers/src/main/java/org/apache/tika/parser/microsoft/WordExtractor.java)).

If you do run Tika, run it safely. Tika's own [robustness guide](https://tika.apache.org/docs/4.0.0-SNAPSHOT/advanced/robustness.html): *"Running parsers on untrusted data carries inherent risks… The primary defense against parser failures is process isolation."* In 4.x, **Tika Pipes** is the recommended mechanism and the `/tika`, `/rmeta` and `/unpack` endpoints parse in forked child processes; `/meta` still parses in-process and should be treated as best-effort ([server docs](https://tika.apache.org/docs/4.0.0-SNAPSHOT/using-tika/server/index.html)). Keep the `/config` endpoint family **disabled** (they are off by default; see CVE-2015-3271), and per Tika's own advice: *"Isolate Tika from critical systems — never run in the same JVM as your indexer."*

### 4.4 LibreOffice headless — and why I would not use it here

Two operational notes and one security finding.

- `soffice --headless --convert-to txt` **silently produces an OpenDocument ZIP with a `.txt` extension**. You must specify the filter: `--convert-to txt:Text` ([demonstrated](https://askubuntu.com/questions/668313/ubuntu-server-libreoffice-convert-to-txt-error), [filter table](https://help.libreoffice.org/latest/en-GB/text/shared/guide/convertfilters.html)). Output is UTF-8 with a BOM.
- For batch use, isolate the user profile per invocation (`-env:UserInstallation=...`) or concurrent conversions deadlock on the profile lock.
- **CVE-2026-6047** is a heap buffer overflow / type confusion (CWE-787, CWE-843) in LibreOffice's **OOXML text box import** path: *"a handler object was assumed to be of one type and written to at that type's field layout, but it could be a smaller object, so the write landed past the end of the allocation… can potentially lead to unauthorized code execution"* ([details](https://app.opencve.io/cve/CVE-2026-6047)). The vulnerability *"appears only when documents containing text boxes are processed"* — precisely the DOCX feature you need LibreOffice for.

Given that `docx2python` already extracts text boxes in-process with no C++ parser and no JVM, taking on a full office suite's attack surface to reach the same result is a bad trade. Keep LibreOffice only for legacy `.doc` / `.rtf` / `.odt`, in its own locked-down container, if you decide to support those at all.

---

## 5. Format sniffing and document safety

### 5.1 True MIME detection

| Library | Implementation | Notes |
|---|---|---|
| **python-magic** | ctypes wrapper over the **libmagic** C library | Requires libmagic installed in the image. Docs recommend at least **2048 bytes** for `from_buffer` since *"less can produce incorrect identification."* The `Magic` class is **not thread-safe**: *"it's not safe for sharing across multiple threads and will fail throw if this is attempted"* ([PyPI](https://pypi.org/project/python-magic/)) |
| **puremagic** | pure Python, zero runtime deps, with content-aware "deep scan" enabled by default | *"Faster, Lightweight, Cross platform compatible, No dependencies"* but *"Does not have as many file types … Duplications due to small or reused magic numbers."* **⚠️ puremagic 2.x requires Python 3.12+ — on your Python 3.11 you must pin the `1.x` chain** ([PyPI](https://pypi.org/project/puremagic/)) |
| **filetype** | pure Python, reads **only the first 261 bytes** | Simplest and fastest; smallest signature database ([GitHub](https://github.com/h2non/filetype.py/)) |

**Recommendation:** `python-magic` as primary. DOCX is a ZIP container, and distinguishing "an OOXML wordprocessing document" from "an arbitrary ZIP archive someone renamed" needs libmagic's deeper database, not a 261-byte header check. Keep `puremagic` (pinned `<2.0` for Python 3.11) as a pure-Python cross-check and as a fallback if libmagic is unavailable. Instantiate `magic.Magic` per-thread or use the module-level `magic.from_buffer` helper, given the thread-safety warning. **Never trust the browser-supplied `Content-Type` or the filename extension** — both are attacker-controlled in a file upload.

### 5.2 PDF threats and mitigations

**pikepdf ≥ 10.9 now ships a first-class sanitization API** (MPL-2.0, built on qpdf). From the [sanitize docs](https://pikepdf.readthedocs.io/en/latest/topics/sanitize.html):

| Helper | What it removes |
|---|---|
| `remove_javascript()` | the document-level JavaScript name tree **and every JavaScript action** reachable from the catalog, pages, annotations, form fields and outline items, including actions chained via `/Next` |
| `remove_attachments()` | embedded files, `/AF` references; defangs FileAttachment annotations while keeping page geometry |
| `remove_external_access()` | URI, **`Launch`**, `GoToR`, `GoToE`, `SubmitForm`, `ImportData` actions |
| `remove_multimedia()` | Screen/Movie/Sound/RichMedia/3D annotations and Rendition/RichMediaExecute actions |
| `remove_thumbnails()`, `remove_search_index()`, `remove_private_app_data()`, `remove_web_capture()`, `remove_collection()` | stale/leaky metadata surfaces |
| `Sanitizer()` | fluent chaining; coalesces the action-based removals into a single document pass and is reusable across files |

**Critical interaction with your product requirement.** `remove_external_access()` *"removes all of these actions… Link annotations are kept — so any visible underline or box is preserved — but their triggering action is removed, rendering them inert."* **That destroys the LinkedIn/GitHub URL extraction that §1.3 identifies as important.** So: **extract hyperlinks first, sanitize second**, or use only `remove_javascript()` + `remove_attachments()` + `remove_multimedia()` on the copy you keep. Do not blanket-apply a "sanitize everything" recipe.

**What pikepdf deliberately refuses to do, and you should too.** The docs carry an explicit warning list:

> - **XFA forms.** *"Removing XFA typically reduces the document to a single blank page with an error message — destroying everything the document was for."*
> - **All annotations / the whole AcroForm.** *"Wholesale removal discards links, comments, and every form field, not just the risky parts."*
> - **The document `/ID`.** *"Erasing the trailer `/ID` does not improve security; pikepdf will simply generate a new one when saving."*

And, pointedly: *"The ChatGPT-style 'sanitizers' circulating online often go much further, and in doing so destroy legitimate content."* If you were planning to strip XFA — which is a real legacy attack surface — the trade is that XFA-form resumes become blank pages. Prefer *detecting* XFA and routing to a rasterize-and-OCR path over stripping it.

**Two more options.** [`pdf-defang`](https://kovetz-pdf.github.io/pdf-defang/) (MIT, on pikepdf) offers `strict` and `balanced` levels, stripping document JavaScript, `OpenAction`, document and page `/AA`, `Launch`/`GoToR`/`GoToE`/`ImportData`/`Rendition`/`Movie`/`Sound`, **XFA**, and dangerous URI schemes (`javascript:`, `file:`, `data:`, UNC paths) while keeping `http`/`https`/`mailto`/`tel`/`ftp` links. Note it *does* strip XFA, against pikepdf's advice — use `balanced` and know the trade. The nuclear option, recommended by pikepdf itself:

```bash
ocrmypdf --force-ocr input.pdf output.pdf
```

which *"rasterizes all pages to images and then re-OCRs them. In the process it discards JavaScript, embedded files, form fields, annotations, the original (possibly inaccurate or maliciously crafted) text layer, and any hidden or off-page content — because none of it survives the trip through a bitmap."* OCRmyPDF is MPL-2.0. This is the right handling for anything your scanner flags as suspicious, and it doubles as your OCR path.

**Structural guards you must add yourself:**

- **Encrypted PDFs.** `pypdf.PdfReader(...).is_encrypted` — verified working **[measured here]**. pikepdf/qpdf can open password-protected files. Decide policy: reject, or attempt an empty-password open (very common for "protected" resumes) and reject otherwise.
- **Huge page counts.** Check `len(reader.pages)` **before** any per-page loop. A resume is 1–4 pages; a 10,000-page PDF is either an attack or a mistake. Cap it.
- **Malformed structure.** `pikepdf.open()` *"silently fixes many types of PDF damage on open"* ([README](https://github.com/pikepdf/pikepdf)) — using it as your front door normalizes input before your parsers see it.

### 5.3 OOXML / DOCX threats — and a correction to the standard advice

**The billion-laughs advice you will find everywhere is wrong for your stack.** Both `python-docx` and `docx2python` parse with **lxml**, and per [defusedxml's own README](https://github.com/tiran/defusedxml/blob/main/README.md):

> *"lxml is safe against most attack scenarios. lxml uses `libxml2` for parsing XML. The library has **builtin mitigations against billion laughs and quadratic blowup attacks**. The parser allows a limited amount of entity expansions, then fails. lxml also disables network access by default."*

`defusedxml`'s own `defusedxml.lxml` module is marked **DEPRECATED** for this reason. So:

- **If you parse OOXML via python-docx / docx2python / lxml:** you are already covered against billion laughs. For belt-and-braces, construct the parser explicitly: `etree.XMLParser(resolve_entities=False)`.
- **`defusedxml` is the right answer only if you parse the OOXML parts yourself** with `xml.etree`, `minidom`, `sax` or `pulldom` — [all of which are Vulnerable to billion laughs and quadratic blowup](https://docs.python.org/2/library/xml.html) — or if you accept raw XML uploads.
- **`defusedxml` does not protect DOCX ZIP extraction.** Its decompression-bomb guard is a monkey-patch on `xmlrpc` with a 30 MB `MAX_DATA` default. It has nothing to say about `zipfile`.

**Zip bombs — you must implement this yourself.** DOCX is a ZIP and Python's `zipfile` enforces no decompression-ratio limit. Guards to add, all cheap:

1. Cap the number of entries (`len(zf.infolist())`) — a legitimate DOCX has tens, not thousands. My probe DOCX had 19 entries **[measured here]**.
2. Cap the **sum** of `ZipInfo.file_size` across all entries (total uncompressed size).
3. Cap the per-entry **compression ratio** `file_size / compress_size` — `gzip` compresses 1 GiB of zeros to roughly 1 MB, and lzma to 148 KB ([defusedxml docs](https://pypi.org/project/defusedxml/)), so a ratio above ~200:1 on a text part is anomalous.
4. Read each part with a **bounded read loop** rather than trusting the declared `file_size`, since the declared value is attacker-controlled.
5. Reject nested archives and reject entries with absolute or `..` paths.

**ClamAV** ([clamd protocol docs](https://docs.clamav.net/manual/Usage/ClamdProtocol.html)):

- Use **`INSTREAM`** over a TCP or Unix socket to scan bytes in memory with no temp file.
- **`StreamMaxLength`, `MaxFileSize` and `MaxScanSize` must all exceed your upload cap**, or you get `INSTREAM size limit exceeded` — a very common misconfiguration ([clamav#1319](https://github.com/Cisco-Talos/clamav/issues/1319)), and one where the error message is misleading (`max: 0`).
- Relevant `clamd.conf` knobs for documents: `ScanPDF`, `ScanOLE2`, `ScanXMLDOCS`, `ScanArchive`, `ArchiveBlockEncrypted`, `MaxRecursion`, `MaxFiles`, `MaxScanTime`.
- **`pyclamd` is synchronous.** In FastAPI, wrap it: `await asyncio.to_thread(scan_bytes_sync, data)` — otherwise you block the event loop for the duration of the scan ([reference implementation](https://github.com/glowingkitty/OpenMates/blob/main/backend/upload/services/malware_scanner.py)).
- Run `clamd` in its own container with a `freshclam` sidecar.

### 5.4 Sandboxing and resource limits

**Resource limits.** `resource.setrlimit` with `RLIMIT_AS` (virtual memory), `RLIMIT_CPU` (CPU seconds) and `RLIMIT_FSIZE` (output size), plus `os.setsid()` in the child so you can kill the whole process group ([pattern](https://healeycodes.com/running-untrusted-python-code), [production example](https://github.com/paulholland511/eidetic-os/blob/main/eidetic_os/sandbox.py)). **`RLIMIT_CPU` alone is insufficient** — it does not fire on a process that is blocked or sleeping, so you also need a wall-clock `proc.communicate(timeout=N)`. Set the CPU limit slightly above the wall-clock timeout so the wall clock normally fires first for honest documents.

**The FastAPI-specific caveat.** The usual recipe is `subprocess.Popen(..., preexec_fn=set_limits)`, but `preexec_fn` is documented as unsafe in the presence of threads — and FastAPI runs sync endpoints and `asyncio.to_thread` calls on a thread pool. Prefer one of:

1. A **dedicated extraction worker** (Celery / RQ / arq / a separate FastAPI service) whose *whole process* runs under the limits, set once at startup. Cleanest, and it also gets extraction off your request path.
2. **Container-level cgroup limits** (`--memory`, `--cpus`, `pids-limit`) on an extraction sidecar. This is what actually enforces limits under Kubernetes anyway.
3. A pre-forked pool created before any threads exist.

**gVisor.** Useful as a syscall-level boundary for genuinely untrusted parsing, but be clear about what it does not do: *"gVisor doesn't by itself do memory limiting; instead, it relies on the host Linux kernel to do this"* via cgroups ([gvisor#10264](https://github.com/google/gvisor/issues/10264)). To get enforcement you need: the host OOM killer enabled, `cgroupfs` mounted, `runsc --ignore-cgroups` **not** set, and if you use `--systemd-cgroup`, systemd ≥ v244. For a resume parser, gVisor is a reasonable step-3 hardening; steps 1 and 2 (allowlist + subprocess with limits) buy you most of the risk reduction.

### 5.5 The gate, in order

```
1. size cap at the ASGI/ingress layer (reject before reading the body)
2. python-magic on the first ≥2048 bytes → strict allowlist {application/pdf,
   application/vnd.openxmlformats-officedocument.wordprocessingml.document}
   — ignore the client Content-Type and the extension entirely
3. ClamAV INSTREAM (asyncio.to_thread) → reject on FOUND
4. format-specific structural guards:
     PDF   → pikepdf.open() (repairs) → is_encrypted? page count cap?
             /XFA present? → route to rasterize+OCR
     DOCX  → zip entry count, total uncompressed size, per-entry ratio,
             no nested archives, no traversal paths
5. EXTRACT HYPERLINKS AND ANNOTATIONS  ← before any sanitization
6. pikepdf Sanitizer().remove_javascript().remove_attachments()
   .remove_multimedia()  — deliberately NOT remove_external_access()
7. run the actual text extraction in the worker process, under RLIMIT_AS /
   RLIMIT_CPU / RLIMIT_FSIZE + wall-clock timeout, in its own container
   with cgroup limits
```

---

## 6. Scanned-resume detection heuristics

**The authoritative practitioner recipe** is on PyMuPDF's own blog, [Using PyMuPDF to triage your documents](https://pymupdf.io/blog/using-pymupdf-to-triage-your-documents) — usable as a *design*, with any library:

| Bucket | Rule |
|---|---|
| `SKIP` | < 20 chars on page **and** < 2% image coverage |
| `OCR_NEEDED` | image covers **> 25%** of page **and** < 30 native chars |
| `LLM_NEEDED` | scores ≥ 2 on a complexity checklist |
| `TEXT_ONLY` | everything else |

Their thresholds are keyword-only arguments on purpose: *"Every document set has its own quirks, and the example above is a starting point rather than a prescription."*

**A three-signal / two-of-N classifier** is the other widely-cited pattern ([pdfmux](https://pdfmux.com/blog/detect-scanned-pdf-python/), [routing follow-up](https://pdfmux.com/blog/pdf-extraction-routing-python/)) **[vendor]**, claiming 98% F1 and < 5 ms/page:

| Signal | Scanned indicator | Cost |
|---|---|---|
| Text density | < 50 chars on a full page | < 0.1 ms |
| Image coverage | > 50–80% of page area | < 0.5 ms |
| **Text-block area ratio** | **< 5%** (digital pages are typically 20–60%) | — |
| Font embedding | zero embedded fonts in page resources | < 0.1 ms |
| Encoding sanity | garbled text / U+FFFD replacement chars | < 0.2 ms |
| Character distribution | unrealistic letter frequencies | < 0.3 ms |

*"A page that fails two or more signals is routed to OCR. One failing signal is ambiguous (a cover page is legitimately image-heavy but not scanned), so the two-of-five rule keeps false positives low."* They call **text-block area ratio** *"the most reliable single signal"*, and note it is what catches the nasty **hybrid case**: a scanned page carrying a thin, bad, invisible OCR layer, where text length looks fine but the visible content is still a raster.

A simpler starting threshold of **100 characters per page** is also recommended ([Tensoria](https://tensoria.fr/en/blog/pdf-data-extraction-ai-architecture)) **[vendor]**.

**Do not just use OCRmyPDF's built-in decision.** `--mode skip` (formerly `--skip-text`) *"skips pages with existing text"* — **any** text objects at all, with no minimum count ([advanced docs](https://ocrmypdf.readthedocs.io/en/latest/advanced.html)). [Issue #258](https://github.com/ocrmypdf/OCRmyPDF/issues/258) is people hitting exactly this: a page with a watermarked page number gets skipped and stays un-OCRed, and the workaround is patching `_page_has_text` with `len(text) >= 10`. OCRmyPDF's maintainer: *"There is no standard algorithm to estimate searchability."* Note `--mode redo` does perform a real visible/invisible text analysis and re-OCRs raster content without disturbing genuine text — that is the right mode for hybrid pages.

**The failure mode nobody's char count catches.** From [OCRmyPDF issue #604](https://github.com/ocrmypdf/OCRmyPDF/issues/604), the maintainer:

> *"Internally PDF identifies text characters by a glyph number… It needs a Unicode mapping table to tell what character number is associated with what glyph, and sometimes those tables are missing, wrong or corrupt — in which case you have a legible document whose text extracts as gibberish. Forcing OCR will fix that."*

A resume exported by a design tool with a broken or absent `ToUnicode` CMap will extract thousands of characters of mojibake and sail through every char-count check. **Your gate needs an encoding-sanity signal, not just a density signal.**

**Concrete recommendation for resumes.** Resumes are 1–4 pages, so evaluate per page and route per page, and keep the probe on `pypdfium2` where `count_chars()` is essentially free (verified 0 on an image-only page, 327 on a text page **[measured here]**):

```
for each page:
  chars      = textpage.count_chars()
  img_cov    = sum(image areas) / page area
  txt_cov    = union(word bboxes) area / page area
  printable  = fraction of extracted chars that are not U+FFFD / control / PUA
  ascii_ok   = extracted text contains plausible dictionary words

  needs_ocr = (chars < 100)
           or (img_cov > 0.50 and txt_cov < 0.05)
           or (printable < 0.85)          # broken ToUnicode CMap
           or (not ascii_ok and chars > 200)  # dense but meaningless
```

Then: `needs_ocr` → rasterize via `pypdfium2` and run RapidOCR/Tesseract (which also sanitizes, per §5.2). Track the OCR rate as a product metric; a spike means an upstream template changed.

---

## 7. Licensing landmines — read this section

Ranked by how likely each is to bite a commercial, closed-source, EU-serving SaaS.

### 🚨 1. PyMuPDF / `fitz` / `pymupdf4llm` — AGPL-3.0

The PyPI licence field reads literally **`Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License`** ([pypi](https://pypi.org/project/pymupdf/1.28.0/)). The AGPL's §13 network-use clause means offering the software as a network service obliges you to make **your application's** corresponding source available to your users. Artifex's own [licensing page](https://artifex.com/licensing) spells out the AGPL column: *"Full source code disclosure (including your app code)"*, *"No support available"*.

The commercial alternative is **not a published price**. Artifex: *"Each Artifex commercial license is crafted based on your individual use case"*, with **OEM Distribution** and **Subscription** models both described as *"Per-copy cost with a quarterly minimum fee"* plus *"Annual reporting on volume of distribution"*. For a startup that means an unbudgeted negotiation, a recurring minimum, and an ongoing reporting obligation on your core extraction path.

This is not a theoretical concern. **IBM's Docling team specifically wrote a new PDF parser to avoid it**: *"we ran into various limitations, among which are restrictive licensing (e.g., pymupdf)"* ([technical report](https://www.arxiv.org/pdf/2408.09869v4)).

**Transitive exposure to check:** anything depending on PyMuPDF inherits the AGPL. `pdf2docx`-family packages are a known example — one derivative documents it explicitly: *"If you ship pdf2docx-plus inside a closed-source product, you need a commercial PyMuPDF license from Artifex. If you offer pdf2docx-plus as a SaaS/network service to third parties, the AGPL requires you to make the corresponding source (including your app) available to those users"* ([LICENSING.md](https://github.com/mithunvoe/pdf2docx-plus/blob/main/LICENSING.md)). **Add a CI licence gate** (`pip-licenses` / `reuse` / an SBOM policy check) that fails the build on AGPL and GPL in the runtime dependency tree.

### 🚨 2. Nougat weights — CC-BY-NC-4.0 (non-commercial)

Code is MIT, **weights are non-commercial**. This is a flat prohibition, not a threshold. It is also unmaintained (last push 2025-02-21) and built for LaTeX academic papers, so it is the wrong tool for resumes on every axis.

### ⚠️ 3. Marker and Surya weights — AI Pubs Open RAIL-M, $5M funding/revenue ceiling

Code is Apache-2.0 (I verified the raw LICENSE files), but *"model weights use a modified AI Pubs Open Rail-M license (free for research, personal use, and startups under **$5M funding/revenue**)"* ([Marker README](https://raw.githubusercontent.com/datalab-to/marker/master/README.md), [Surya README](https://raw.githubusercontent.com/datalab-to/surya/master/README.md)).

**This is the worst kind of landmine because it detonates on success.** Cross $5M in funding *or* revenue and you must either buy a Datalab licence at whatever the then-current price is or re-architect your core extraction path — at the exact moment you have the least engineering slack. Note also that **selecting `SuryaOCR` as Docling's OCR engine pulls these weights into an otherwise-clean MIT stack.** If you use Docling, pin the OCR engine to Tesseract or RapidOCR explicitly.

### ⚠️ 4. borb — AGPL-3.0-or-later

`AGPL-3.0-or-later` on [PyPI](https://pypi.org/project/borb/), commercial tiers €250–5,000/yr by annual document volume ([pricing](https://borbpdf.com/pricing.html)). Also the wrong tool — borb's strength is PDF *generation*.

### ⚠️ 5. pyresparser (GPL-3.0) and OpenResume (AGPL-3.0)

Both are the first hits when you search for open resume parsers. **Do not vendor either.** `pyresparser` is GPL-3.0 with its last PyPI release uploaded **2019-12-15** and last commit 2023-09 (verified via GitHub and PyPI APIs **[measured here]**). `OpenResume` is AGPL-3.0. Read their algorithms — see §10 — and write your own.

### ⚠️ 6. MinerU — attribution obligation with automatic termination

Now Apache-2.0-based with generous thresholds (100M MAU / $20M monthly revenue), but: *"If you provide online services to third parties based on MinerU, you must clearly and prominently indicate, in the relevant product or service interface or in publicly available documentation, that MinerU is used"*, and failure to comply means *"this License and all rights granted under this License will terminate automatically"* ([LICENSE.md](https://github.com/opendatalab/MinerU/blob/mineru-3.1.7-released/LICENSE.md)). A footer credit is a small price, but it is a **product** requirement, not just a legal file — it needs a design decision, and it must not get lost in a redesign.

### ℹ️ 7. Minor obligations, cheap to satisfy

- **pypdfium2**: ship PDFium's LICENSE plus its dependency licences with your binary distribution; the maintainers advise treating PDFium's dual text as `BSD-3-Clause AND Apache-2.0` (the conservative reading).
- **pdftext**: GPL-3.0 ([per the PDF Oxide comparison table](https://pdf.oxide.fyi/docs/performance)) **[vendor]** — avoid, and note it appears in some Marker-adjacent stacks.
- **poppler / `pdftotext`**: GPL. Fine as a subprocess CLI tool under most readings, but not worth the argument when pypdfium2 is equally fast and permissive.
- **Camelot**: MIT and, as of 2.0.0, **no Ghostscript by default** — just don't install the `ghostscript` extra.
- **tabula-py**: MIT, but drags in a JVM.
- **Docling code is MIT; model weights are per-model.** Its README: *"For individual model usage, please refer to the model licenses found in the original packages."* Audit whichever layout/table/OCR models you actually enable, not just the framework.

---

## 8. Comparison matrix

Legend: ✅ good / ⚠️ partial or caveated / ❌ no. "Speed" is text extraction at resume scale (1–2 pages). Cost is per 1,000 pages.

| Library / service | Licence | Speed | Layout / bbox | Multi-column reading order | Tables | OCR | Maturity | CPU-only | Cost |
|---|---|---|---|---|---|---|---|---|---|
| **pdfplumber** | **MIT** | ⚠️ slow in bulk (9.5 s avg on 30-page docs); ~0.3–0.7 s for a 2-page resume | ✅ **best API**: char bbox + `fontname` + `size` + `matrix` + `upright`; **`.hyperlinks` + `.annots`** | ❌ default and `layout=True` both interleave; `use_text_flow=True` fixes only column-ordered streams **[measured]** | ✅ **best OSS** (TEDS 0.847 **[vendor]**) | ❌ | ✅ 10.6k★, active | ✅ | $0 |
| **pypdfium2** | Apache-2.0 / BSD-3 (+PDFium notices) | ✅ **fastest permissive** (0.1 s avg; 4.1 ms/PDF **[vendor]**) | ⚠️ `get_charbox` ✅; font name/size **raw ctypes only**; **no link API** **[measured]** | ❌ trusts content stream **[measured]**; Docling's paper cites *"merged text cells across far-apart… table columns"* | ❌ | ❌ (renderer for OCR) | ✅ active, small team (801★) | ✅ | $0 |
| **pdfminer.six** | MIT | ⚠️ 5.8 s avg | ✅ `LTChar.fontname/.size/.bbox` | ❌ all `boxes_flow` values interleave **[measured]** | ❌ | ❌ | ✅ 7.0k★ | ✅ | $0 |
| **pypdf** | BSD-3-Clause | ⚠️ 3.5 s avg | ⚠️ bbox via visitor callbacks; ✅ `/Annots` URIs, ✅ `get_fields()`, ✅ `is_encrypted` | ❌ **[measured]** | ❌ | ❌ | ✅ 10.1k★ | ✅ | $0 |
| **PyMuPDF** | 🚨 **AGPL-3.0 / paid** | ✅ fastest overall (180 pp/s **[vendor]**) | ✅ richest (flags bitfield, rawdict) | ⚠️ best tooling but **out-of-core**: `multi_column.py` utility / `pymupdf4llm` | ✅ (TEDS 0.692 **[vendor]**) | ⚠️ Tesseract, manual | ✅ | ✅ | 🚨 unpublished per-copy + quarterly minimum |
| **Camelot 2.0** | MIT (Ghostscript optional) | ⚠️ | n/a | n/a | ✅ tables only | ⚠️ `ocr` extra → RapidOCR | ✅ 3.7k★ | ✅ | $0 |
| **tabula-py** | MIT (+JVM) | ⚠️ | n/a | n/a | ✅ tables only | ❌ | ✅ | ✅ | $0 |
| **borb** | 🚨 **AGPL-3.0 / paid** | — | ⚠️ | ❌ | ⚠️ | ❌ | ⚠️ | ✅ | €250–5,000/yr |
| **Docling** | **MIT** (weights per-model) | ⚠️ 0.79 s/page median CPU, ~0.8 s with OCR off; 3.1 s/page mean all-on | ✅ layout model + bboxes + DoclingDocument | ✅ **best permissive option** — dedicated `ReadingOrderModel`; ⚠️ fixed 15% dilation threshold hurts complex multi-column | ✅ TableFormer | ✅ Tesseract/EasyOCR/RapidOCR/Surya/Auto | ✅ 63.9k★, pushed today | ✅ **yes** | $0 |
| **Unstructured** | Apache-2.0 | ⚠️ 4.2 s/page CPU, no GPU benefit | ✅ | ⚠️ | ✅ | ✅ | ✅ 15.2k★ | ✅ | $0 |
| **Marker** | Apache-2.0 code / ⚠️ **OpenRAIL-M weights, $5M cap** | ❌ 16+ s/page x86 CPU; 0.86 s L4 | ✅ | ⚠️ **worst read-order in OmniDocBench v1.6 (0.243)** | ✅ | ✅ via Surya | ✅ 38.0k★ | ⚠️ impractical | $0 under $5M |
| **Surya** | Apache-2.0 code / ⚠️ **OpenRAIL-M weights, $5M cap** | ⚠️ 650M params | ✅ | ✅ dedicated reading-order model | ✅ | ✅ 90+ langs | ✅ 21.2k★ | ⚠️ GPU strongly preferred | $0 under $5M |
| **MinerU** | ⚠️ Apache-2.0 + thresholds + **attribution** | ⚠️ 3.3 s/page CPU; **0.21 s L4** | ✅ | ✅ **SOTA — 0.120 read-order edit** | ✅ TEDS 93.4 | ✅ | ✅ 76.0k★ | ⚠️ VLM wants GPU | $0 under 100M MAU |
| **Nougat** | 🚨 MIT code / **CC-BY-NC-4.0 weights** | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | ❌ dead (2025-02) | ❌ | 🚨 non-commercial |
| **LayoutParser** | Apache-2.0 | ⚠️ | ✅ | ⚠️ | ⚠️ | via backends | ❌ dead (2024-08) | ✅ | $0 |
| **Tesseract** | Apache-2.0 | ⚠️ | ✅ hOCR bboxes | ❌ | ⚠️ | ✅ 100+ langs | ✅ 75.5k★ | ✅ | $0 |
| **RapidOCR** | Apache-2.0 (Baidu models) | ✅ fast ONNX | ✅ | ❌ | ⚠️ | ✅ | ✅ 6.9k★ | ✅ **best CPU OCR** | $0 |
| **PaddleOCR** | Apache-2.0 | ✅ | ✅ PP-Structure | ✅ PP-StructureV3 | ✅ | ✅ | ✅ 86.4k★ | ✅ | $0 |
| **EasyOCR** | Apache-2.0 | ❌ **13 s/page x86 CPU** (Docling's measurement) | ✅ | ❌ | ❌ | ✅ 80+ | ✅ | ⚠️ too slow on CPU | $0 |
| **docTR** | Apache-2.0 | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 6.2k★, pushed today | ✅ | $0 |
| **Azure DI — Read** | commercial | ✅ | ⚠️ OCR only | ❌ | ❌ | ✅ | ✅ | n/a | **$1.50** |
| **Azure DI — prebuilt-layout** | commercial | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | n/a | **$10.00** |
| **AWS Textract — Detect Text** | commercial | ✅ | ⚠️ | ❌ | ❌ | ✅ | ✅ | n/a | **$1.50** |
| **AWS Textract — Tables (+free Layout)** | commercial | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | n/a | **$15.00** |
| **Google Document OCR** | commercial | ✅ | ⚠️ | ❌ | ❌ | ✅ | ✅ | n/a | **$1.50** |
| **Google Layout Parser** | commercial | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | n/a | **$10.00** |
| **Mistral OCR 4** | commercial (self-host for enterprise) | ✅ | ✅ bboxes + block types + confidence | ⚠️ 0.171 read-order edit | ⚠️ TEDS 76.8 | ✅ 170 langs | ✅ | n/a | **$4.00** / $2.00 batch |
| **Gemini 3 Flash as OCR** | commercial | ✅ | ❌ no reliable bboxes | ⚠️ 0.172 read-order edit | ⚠️ | ✅ | ✅ | n/a | **≈$2.25** (my calc on official rates) |
| **LlamaParse Fast → Agentic Plus** | commercial, closed | ✅ | ✅ | ✅ at higher tiers | ✅ | ✅ | ✅ | n/a | **$1.25 → $56.25** |
| **Reducto** | commercial | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | n/a | **$15.00** – $60.00 |

**DOCX** (measured, §4):

| Tool | Licence | Text box | Header/footer | Hyperlink URL | Tables | Notes |
|---|---|---|---|---|---|---|
| **docx2python 3.6.2** | MIT | ✅ | ✅ | ✅ | ✅ | **only pure-Python tool that gets all of it** |
| Apache Tika 3.2.3 | Apache-2.0 | ✅ | ✅ | ✅ (`--html`) | ✅ | needs JVM; use Tika Pipes |
| python-docx 1.2.0 (thorough) | MIT | ❌ | ✅ | ✅ | ✅ | best *structural* object model |
| docx2txt 0.9 | MIT | ✅ | ✅ | ❌ | ✅ | flat text only, unmaintained |
| mammoth 1.12.0 | BSD-2 | ❌ | ❌ | ✅ (HTML) | ✅ | semantic HTML, wrong tool here |
| LibreOffice headless | MPL-2.0 | ✅ | ✅ | ⚠️ | ✅ | 🚨 **CVE-2026-6047 in OOXML text-box import** |

---

## 9. Reproducing the experiments

All measurements labelled **[measured here]** come from five scripts, run on Python 3.12.3 with python-docx 1.2.0, docx2python 3.6.2, docx2txt 0.9, mammoth 1.12.0, Tika 3.2.3, pdfplumber 0.11.10, pypdfium2 5.12.1, pypdf 6.14.2, pdfminer.six 20260107, reportlab 5.0.0. They are checked in, with run instructions, under [`docs/research/document-extraction-probes/`](research/document-extraction-probes/):

| Script | What it does |
|---|---|
| `make_docx.py` | builds `resume_probe.docx` with 7 planted markers: body paragraph, 2-col table, header, footer, `w:hyperlink` with anchor ≠ URL, and a floating text box (`mc:AlternateContent` → `wps:txbx` → `w:txbxContent`) |
| `test_docx.py` | runs 8 extractors against it (6 Python, plus Tika `--text` and `--html`) and prints the FOUND/MISS matrix of §4. Tika is opt-in via a `TIKA_JAR` environment variable, since it needs a JVM |
| `make_pdf.py` | builds `resume_2col.pdf`: 2-column resume, `L1…L5` left / `R1…R6` right, content stream **column-ordered**; two `linkURL` annotations whose targets are absent from the visible text; page 2 is a bare image (synthetic scan) |
| `make_pdf2.py` | builds `resume_2col_interleaved.pdf`: same visual layout, content stream written **line-by-line across columns** |
| `test_pdf.py` | runs all 9 extraction modes of §1.4 against **both** PDFs and classifies each output as correct vs interleaved by run-length-encoding the `L`/`R` marker sequence; also probes hyperlink recovery, char/font APIs and text-layer detection. Contains the reference `find_gutter()` implementation |

The reading-order verdict is mechanical, not eyeballed: extract the ordered sequence of `L`/`R` markers, run-length encode it, and if there are more than 2 runs the columns were interleaved.

**Before adopting any recommendation here, re-run `test_pdf.py` against 50 real resumes from your own funnel.** My PDFs are synthetic and deliberately clean; they establish that the failure mode exists and that the fix works, not the exact rate at which it occurs in your traffic.

---

## 10. Open-source resume parsers worth studying

| Project | Licence | Stars | Last activity | Approach | Verdict |
|---|---|---|---|---|---|
| [**OpenResume**](https://www.open-resume.com/resume-parser) | 🚨 **AGPL-3.0** | 8,779 | 2024-10 | TypeScript + `pdf.js`; **feature-scoring** extraction | **Study the algorithm. Do not vendor the code.** |
| [**pyresparser**](https://github.com/omkarpathak/pyresparser/) | 🚨 **GPL-3.0** | 957 | 2023-09; **last PyPI release 2019-12-15** | spaCy NER + nltk + a skills CSV, over `pdfminer.six`/`docx2txt` | **Dead and copyleft. Skip.** |
| [oksomu/resume-ner](https://huggingface.co/oksomu/resume-ner) | — | — | active | DistilBERT token classification, 13 labels, ONNX artifacts | Best documented; **read its limitations** |
| [Anjali-2026/resume-ner-bert-v2](https://huggingface.co/Anjali-2026/resume-ner-bert-v2) | Apache-2.0 | — | 2025-08 | BERT, 25 entity types, 431 MB | 90.87% F1, but see caveat |
| Affinda | commercial | — | — | closed API | no meaningful open tooling |

**OpenResume's algorithm is genuinely worth an hour of reading.** Its [parser deep-dive](https://www.open-resume.com/resume-parser) documents a **feature-scoring system**: each resume attribute has a set of feature-matching functions, each with a positive or negative score; every text item in a section is scored against all of them, and the highest scorer wins the attribute. It's a clean, debuggable, per-field-explainable design — much easier to reason about in production than an opaque NER model, and it composes well with the geometric layout pass in §1.4 because both operate on positioned text items.

Its **subsection detection heuristic** is directly reusable: *"check if the vertical line gap between 2 lines is larger than the typical line gap * 1.4, since a well formatted resume usually creates a new empty line break before adding the next subsection. There is also a fallback heuristic … to check if the text item is bolded."* You have `char["size"]` and `char["fontname"]` from pdfplumber, so both signals are available to you.

And note its own stated scope: **"the algorithm is designed to parse single column resume in English language."** Even the best-documented open parser punts on the multi-column case. That is the gap your product has to fill.

**The number that should shape your priorities.** `oksomu/resume-ner` reports **entity F1 97.77%** overall, **99.18% on clean resumes**, and **69.24% on noisy (OCR/scraped) text**. Its documented limitations name the culprit explicitly: *"image-based/scanned PDFs require OCR before text extraction"* and **"two-column PDF layouts may flatten during text extraction."**

So the field-extraction model is not your bottleneck — a 30-point accuracy cliff sits entirely in the extraction layer, and it is caused by exactly the two problems in §1.4 and §6. Fix extraction and almost any decent NER model or LLM will do well. Ship a strong model on flattened two-column text and it will confidently return wrong employers and wrong dates.

One caveat on the second model: `Anjali-2026/resume-ner-bert-v2` reports 90.87% F1 on 22,542 samples, but its own card says **21,773 of those are "rule-based extraction from conversation data"** — i.e. mostly synthetic silver labels. Treat the headline number as optimistic and validate on your own hand-labelled set.

---

## 11. Recommended stack

Design principles, in priority order: **(1)** no copyleft and no revenue-threshold licences anywhere on the critical path; **(2)** own the layout pass, because no library does it; **(3)** keep candidate PII local by default and treat the cloud as a fallback, not a dependency; **(4)** hyperlink extraction is a first-class output, not an afterthought.

### Tier 0 — Ingest gate (always, every file)

| Component | Choice | Licence |
|---|---|---|
| MIME sniffing | **python-magic** (libmagic) on ≥2048 bytes, strict allowlist; **puremagic `<2.0`** as pure-Python fallback (2.x needs Python 3.12+) | MIT / MIT |
| Malware scan | **ClamAV** `clamd` INSTREAM over socket, `asyncio.to_thread`-wrapped, own container + freshclam sidecar | GPL-2.0 *service*, not linked |
| PDF normalize + guards | **pikepdf** `open()` (auto-repairs) → `is_encrypted`, page-count cap, `/XFA` detection | MPL-2.0 |
| DOCX guards | own zip-bomb checks: entry count, total uncompressed size, per-entry ratio, no nesting, no traversal | — |
| Sanitize (**after** link extraction) | `pikepdf.sanitize.Sanitizer().remove_javascript().remove_attachments().remove_multimedia()` — **deliberately not `remove_external_access()`** | MPL-2.0 |
| Isolation | dedicated extraction worker process, `RLIMIT_AS`/`RLIMIT_CPU`/`RLIMIT_FSIZE` set at startup + wall-clock timeout, own container with cgroup limits | — |

**Why not `preexec_fn`:** it is unsafe with threads, and FastAPI is threaded. Set the limits once in a worker process instead. **Why not `remove_external_access()`:** it strips the link actions that carry the candidate's LinkedIn and GitHub URLs.

### Tier 1 — Fast path: the 90–95% case (born-digital PDF with a good text layer)

| Step | Choice | Licence |
|---|---|---|
| Triage probe | **pypdfium2** `count_chars()` + image coverage + text-block area ratio + **encoding sanity** (§6) | Apache-2.0 / BSD-3 |
| Geometry source | **pdfplumber** `extract_words()` / `chars` — bbox, `fontname`, `size`, `upright`, `matrix` | MIT |
| **Reading order** | **your own gutter detector** (§1.4) — widest word-free vertical band in the middle 50%, then `page.crop()` per column; recurse once for 3-column layouts | your code |
| Section/heading detection | line-gap × 1.4 + bold/size, per OpenResume's heuristic — reimplemented from the published algorithm, not copied | your code |
| **Hyperlinks** | **pdfplumber `.hyperlinks` + `.annots`**, cross-checked with **pypdf** `/Annots → /A → /URI` | MIT / BSD-3 |
| Form fields | **pypdf** `get_fields()`, or the AcroForm walk from pdfplumber's README | BSD-3 |
| Tables | **pdfplumber** `extract_tables()` — best OSS table accuracy, and many resumes are silently table-based | MIT |

Latency budget: ~0.3–0.8 s for a 2-page resume. Everything is MIT/BSD/Apache. Zero marginal cost.

**Emit a confidence signal from this tier.** Concretely: did the gutter detector find a gutter ≥ 20 pt? Do the two column crops each contain a plausible amount of text? Does the output contain expected resume-ish anchors (an email, a date range, a section heading)? Low confidence escalates to Tier 2. Making escalation data-driven is what keeps the expensive tiers rare.

### Tier 2 — Layout path: the hard 5–8% (designer templates, sidebars, 3-column, tables-as-layout)

| Step | Choice | Licence |
|---|---|---|
| Layout + reading order + tables | **Docling**, CPU-only, `do_ocr=False` (you already know there's a text layer), `docling-parse` backend, layout model `heron` (default) or `egret-medium` if you need ~2× less CPU | **MIT** (audit enabled model weights) |
| OCR engine setting | **pin to `tesseract` or `rapidocr`** — do **not** leave it on `Auto`, and do not select `SuryaOCR` | Apache-2.0 |

~0.8 s/page on a server CPU with OCR disabled. Docling is the only permissively licensed toolkit with a purpose-built reading-order stage, it is the most actively maintained (63.9k★, pushed today), and IBM's stewardship plus the MIT licence is the most durable governance story in this space. Validate its multi-column behaviour on your own corpus given the fixed-15%-dilation caveat.

### Tier 3 — OCR path: scanned and image-only resumes (2–5%)

| Step | Choice | Licence |
|---|---|---|
| Rasterize | **pypdfium2** at 300 DPI | Apache-2.0 / BSD-3 |
| OCR | **RapidOCR** (ONNX, CPU-optimised) primary; **Tesseract 5.5.x** fallback for unusual scripts | Apache-2.0 / Apache-2.0 |
| Alternative one-shot | **`ocrmypdf --force-ocr`** → clean searchable PDF, then re-enter Tier 1 | MPL-2.0 |

**Explicitly avoid EasyOCR on CPU:** Docling measured **13 s/page on x86 CPU** vs 1.6 s on an L4 GPU. That is a 13-second synchronous stall per page in a CPU-only deployment.

The `ocrmypdf --force-ocr` route is doubly attractive because it is also pikepdf's recommended sanitization sledgehammer — for a resume your scanner flagged as suspicious, one command both de-fangs and OCRs it.

### Tier 4 — Cloud fallback (< 1%: Tier 2 and 3 both low-confidence, or a hard timeout)

| Rank | Choice | Cost / 1,000 pp | Why |
|---|---|---|---|
| **1** | **Azure AI Document Intelligence `prebuilt-layout`**, West/North Europe | **$10.00** | Clearest documented in-region processing of the hyperscalers; 24 h retention with an explicit **Delete Analyze Result** API; reading order + tables + selection marks in one call |
| 2 | **Mistral OCR 4** (batch where latency allows) | $4.00 / $2.00 | French entity → no US CLOUD Act collision; returns bboxes + block types + **per-block confidence**; enterprise self-hosting is a credible exit if you later want everything on-prem |
| 3 | **Google Layout Parser** (sync `processDocument`, EU location) | $10.00 | Online path is *"processed in memory… not persisted to disk"*; CMEK + VPC-SC + Access Transparency available |
| — | **AWS Textract** | $1.50–$15.00 | Cheap and capable, but **only after** filing the org-wide AI services opt-out; the default cross-region storage for service improvement is unacceptable for candidate PII |
| — | **Gemini 3 Flash as OCR** | ≈$2.25 (my calc) | Cheapest and surprisingly strong (OmniDocBench 92.62), but no reliable bboxes → no provenance for an audit trail. Fine as a *disagreement tie-breaker*, not as the extraction of record |

Wire it as a circuit breaker with a hard timeout and a per-day spend cap, and log every escalation as a product metric. Any sustained rise in Tier 4 volume means an upstream template changed and Tier 1's heuristics need tuning — that alarm is worth more than the fallback itself.

### DOCX path (all tiers)

| Step | Choice | Licence |
|---|---|---|
| Primary | **docx2python 3.6.2** — the only pure-Python extractor that got text boxes **and** headers/footers **and** hyperlink URLs **[measured]** | MIT |
| Structural companion | **python-docx 1.2.0** for tables-as-objects, styles, `Paragraph.hyperlinks`, section iteration | MIT |
| Must-have guards | join `w:t` runs split mid-word before tokenizing; **exclude `w:del` tracked-changes text** | — |
| Legacy `.doc`/`.rtf`/`.odt` | **only if the product requires it**: Apache Tika via **Tika Pipes** in its own container, `/config` endpoints disabled | Apache-2.0 |
| Not recommended | LibreOffice headless — CVE-2026-6047 is in the exact OOXML text-box import path you'd be using it for | — |

### Cross-cutting

- **CI licence gate.** Fail the build on AGPL/GPL/non-commercial licences in the runtime dependency tree, and on new model weights whose licence isn't on an allowlist. This is the control that would have caught PyMuPDF, borb, pdftext, pyresparser, Nougat and the Surya-via-Docling path — all of which are one careless `pip install` away.
- **Extraction provenance.** Carry `(page, bbox, font_size, source_tier)` alongside every extracted field. It is nearly free at Tier 1 and Tier 2, it is what lets you debug a bad parse against the original pixels, it is what lets you show a recruiter *why* a field says what it says, and under the EU AI Act, hiring is a high-risk domain where that traceability is likely to be asked for.
- **Golden corpus.** 50–100 hand-labelled real resumes covering single-column, two-column, sidebar, table-based, scanned, non-Latin, and broken-`ToUnicode` cases. Run it on every extraction change. This is the highest-leverage artefact in the whole project — it is what turns all of the above from opinion into measurement.

---

## 12. Alternative stack designs, and why they are worse

### Alternative A — "Just use PyMuPDF for everything" (+ `pymupdf4llm`)

Fastest option on every benchmark (180 pages/s **[vendor]**; 0.1 s avg on the neutral one), the richest single API (char bbox, font flags bitfield, links, form fields, tables, rendering), and the **best available multi-column tooling** in `multi_column.py` and `pymupdf4llm.get_text_lines`. One dependency instead of four. On pure engineering merit this is the strongest stack in this document.

**Why it's worse anyway:**

1. **It is AGPL-3.0.** You are a commercial closed-source SaaS. §13's network-use clause means your users can demand your application's source. Artifex states the AGPL option plainly: *"Full source code disclosure (including your app code)."*
2. **The commercial escape hatch has no public price and is not a one-off.** *"Each Artifex commercial license is crafted based on your individual use case"*; both commercial models are *"Per-copy cost with a quarterly minimum fee"* with *"Annual reporting on volume of distribution."* You'd be committing your core extraction path to an unbudgeted negotiation, a recurring floor, and an ongoing reporting duty — before you know your volumes.
3. **You'd still be writing the layout pass.** `multi_column.py` is a utility script whose own documentation admits it *"depends on some fairly properly designed page layouts"* and that overlapping boxes *"are likely to cause errors."* So you pay the licensing cost and still own the hard part.
4. **The best-funded team in this space made the opposite call.** IBM Research wrote `docling-parse` from scratch partly to avoid *"restrictive licensing (e.g., pymupdf)."*

The speed advantage is the weakest part of the case: at 1–2 pages per document, pdfplumber's extra ~0.4 s is invisible inside an async upload. You would be buying a legal liability to win a race nobody is timing.

### Alternative B — "Cloud-first": every resume through Azure DI / Textract / Google Layout

Zero extraction code, vendor-maintained quality, scales instantly, no models to ship. At 15,000 pages/month, $150 on Azure Layout is trivially affordable.

**Why it's worse:**

1. **You pay a per-page fee for the 90–95% of resumes a $0 local parser handles perfectly**, and the marginal quality on those pages is roughly nil — cloud Layout and a local gutter detector both get a clean two-column resume right.
2. **You put a third-party network hop on your critical path.** 1–3 s added latency plus tail risk, on the interaction where a candidate is watching a spinner. Their outage becomes your outage.
3. **You need the local path anyway** — for the fallback, for offline development, for the enterprise customer who requires on-prem. Cloud-first means building both and maintaining both, with the cheap one relegated to the badly-tested path.
4. **GDPR gets harder, not easier.** Every resume becomes a cross-border transfer to assess, a DPA to negotiate, a sub-processor to disclose, a retention window to document. Textract's default cross-region storage for service improvement is a live problem until you file the org-wide opt-out. Local-first means the *default* is that candidate PII never leaves your infrastructure, and the cloud is a documented exception on <1% of volume.
5. **Cost stops being trivial exactly when it hurts.** At 1M pages/month, Azure Layout is $10,000/month for work you could do on a couple of CPU cores.

Keep it as **Tier 4**. That gets you the quality insurance without the latency, the dependency, or the default-transfer posture.

### Alternative C — "Best benchmark scores": Marker/Surya, or MinerU, as the primary engine

MinerU2.5-Pro is genuinely state of the art — **95.75 OmniDocBench Overall and the best reading-order edit distance at 0.120**, which is the metric that matters most here. Marker/Surya ship reading-order and layout models purpose-built for exactly this problem.

**Why it's worse:**

1. **Marker and Surya weights are a licence time bomb.** Free only *"for research, personal use, and startups under $5M funding/revenue."* Cross $5M in funding or revenue and you must buy a Datalab licence at an unknown price or rip out your core extraction path — precisely when you have the least slack. Note this also reaches you sideways: choosing `SuryaOCR` inside Docling imports the same terms into an otherwise MIT stack.
2. **Marker is the wrong pick even ignoring licences.** It has the **worst reading order in the OmniDocBench v1.6 excerpt (0.243)** — worse than MinerU-Pipeline, Mistral OCR and every VLM listed — and needs **16+ s/page on x86 CPU**.
3. **MinerU's licence is now genuinely reasonable** (100M MAU / $20M monthly revenue) but carries a **product-surface attribution requirement** with automatic termination for non-compliance. A footer credit is cheap; a footer credit that must survive every future redesign, in a licence that self-terminates, is a small permanent liability.
4. **The benchmark advantage doesn't transfer.** MinerU's SOTA numbers come from a **1.2B-parameter VLM** that wants a GPU: 0.21 s/page on an L4 versus 3.3 s/page on CPU. You'd be adding GPU infrastructure to your upload path to win an edit-distance metric on 1,651 pages of academic papers, magazines and newspapers — a corpus that contains no resumes.
5. **The benchmarks are published by competitors.** OmniDocBench is OpenDataLab's, and OpenDataLab ships MinerU. As one review puts it: *"the numbers aren't fabricated; the people producing them are also competitors."*

### Alternative D — "LLM-vision only": render each page and ask a VLM

Cheap (≈$2.25/1k pages on Gemini 3 Flash), almost no code, and layout is handled implicitly — the model sees the page as a human does, so two columns are a non-issue. OmniDocBench 92.62 for Flash beats every pipeline tool.

**Why it's worse:**

1. **You lose the hyperlink layer completely.** URLs behind anchor text are *not visible in a raster*. A VLM looking at a screenshot sees "LinkedIn Profile" and has no way to recover `linkedin.com/in/janedoe`. My measurement confirms the URLs appear in no library's extracted text either — they exist only in the annotation dictionary, which a rendered image discards. Given that LinkedIn/GitHub enrichment is an explicit requirement, this alone disqualifies vision-only.
2. **No bbox provenance.** You cannot point at the pixels a claim came from. For a hiring product with EU AI Act high-risk exposure, "the model said so" is a weak position when a candidate disputes an extracted employer or date.
3. **Non-determinism on the critical path.** The same resume can yield different output across calls. Regression-testing an extraction pipeline whose output isn't stable is genuinely hard, and silent drift when the provider updates the model is worse.
4. **Confident hallucination is the characteristic failure.** A parser that fails returns empty. A VLM that fails returns a plausible-looking wrong employer, and nothing in the output flags it. As one practitioner puts it: *"a model handed interleaved two-column text produces plausible-sounding wrong content — and nothing in the output reveals extraction as the culprit."*
5. **Output tokens dominate cost and scale with verbosity**, so the cost is much less predictable per document than a flat per-page rate.

A VLM is an excellent **adjudicator** — give it the Tier 1 text *plus* the page image and ask it to reconcile ambiguous sections — and an excellent **field extractor** downstream of good text. It is a poor extractor of record.

### Alternative E — "One framework": Unstructured for everything

Apache-2.0, one API across PDF/DOCX/HTML/email/images, huge integration ecosystem, 15.2k★ and actively maintained. Genuinely convenient.

**Why it's worse:** it is **4.2 s/page on x86 CPU** with **no GPU benefit at all** (Docling's measurement) — five times slower than the Tier 1 path and slower than Docling on the same hardware for a comparable job. And it is a wrapper: you inherit its backend choices rather than controlling them, which matters a great deal when the thing you most need to control is the reading-order pass, and when a backend swap upstream could quietly import a licence you've excluded. Unstructured is a good choice for an ingestion pipeline over heterogeneous enterprise documents. For one narrow document type where you need to own the layout logic and audit every licence, the abstraction costs more than it saves.

---

## 13. Summary of concrete changes to the current codebase

| Current | Change to | Why |
|---|---|---|
| `pdfplumber.extract_text()` | `extract_words()` + own gutter detector + per-column crop | interleaves columns on both test PDFs **[measured]** |
| no hyperlink extraction | `page.hyperlinks` + `page.annots`, cross-checked with `pypdf` `/Annots` | LinkedIn/GitHub URLs are invisible in extracted text **[measured]** |
| no scanned detection | pypdfium2 `count_chars()` + image coverage + text-block ratio + **encoding sanity** | image-only pages currently yield empty strings with no signal |
| `docx.Document(...).paragraphs` | `docx2python` primary, `python-docx` for structure | `.paragraphs` alone missed 5 of 7 planted markers **[measured]** |
| `re.sub(r"\s+", " ", text)` in `clean_extracted_text` | preserve line and block structure | collapsing all whitespace to single spaces destroys the line-gap and section-boundary signals that both the layout pass and the OpenResume-style heading heuristic depend on |
| no ingest gate | §5.5 pipeline | no MIME validation, no malware scan, no zip-bomb guard, no resource limits today |
| no licence gate | CI check failing on AGPL/GPL/non-commercial | PyMuPDF, borb, pdftext, pyresparser and Nougat are each one `pip install` away |

That `clean_extracted_text` row is worth emphasising: `re.sub(r"\s+", " ", ...)` flattens the entire document to one line. Even if you fix the column problem, collapsing whitespace immediately afterwards throws away the vertical-gap information that section detection needs.
