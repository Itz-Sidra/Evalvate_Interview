# How Applicant Tracking Systems Actually Ingest, Parse, Index, and Rank Resumes

**Research input for the ATS Simulation engine.**
Compiled 2026-07-28. Every non-obvious claim carries a URL.

---

## How to read this document

Claims are tagged:

- **[FACT]** — **WELL-SOURCED FACT.** Stated in vendor product documentation, a peer-reviewed paper, a court filing, a company press release, or reproduced by direct measurement in this document. Safe to build on.
- **[WEAK]** — **PLAUSIBLE BUT WEAKLY SOURCED.** Small-n surveys, single-vendor marketing claims, third-party compilations, or reasonable inference. Directionally useful; do not present as established.
- **[MYTH]** — **MYTH / DEBUNKED.** Traceably false, or true-in-2012-and-false-now. Never assert.

### A note on source hygiene

Search results for every query in this space are dominated by SEO content farms and AI-generated "ATS resume checker" blogs (`resumeoptimizerpro.com`, `juicedresume.com`, `atsgrader.com`, `talenttuner.app`, `jobcannon.io`, `resumevera.com`, `haired.app`, `applyarc.com`, `hireflow.net`, `atsverification.com`, and dozens more). These sites **confidently invent specifics**: named scoring weights ("Formatting 10%, Keyword Match 30%"), fabricated parser identities, and invented test corpora ("our analysis of 50,000+ submissions"). Several contradict the vendor documentation they claim to summarize.

I have **excluded all of them as sources of fact**. Where a claim below is attributed, it is attributed to a vendor doc, a primary research paper, a court record, or a measurement I ran. This is the single most important methodological point in this report, because an ATS simulator built on that content-farm layer will confidently encode fiction.

---

## Section 0: The most important structural finding

Before the details, the finding that should shape the product:

> **An ATS is primarily a database and workflow tool with a retrieval layer on top. The dominant failure mode for a qualified candidate is not rejection — it is non-retrieval.** Content-based automatic rejection is rare and, where it exists, is bounded and documented. Automatic *ranking* is now near-universal in enterprise ATSs and is a genuinely new development in 2024–2026.

Both halves matter. The "robot rejected you" story is false. But the reflexive 2020-era correction — "ATSs are just databases, scoring is a myth" — has itself gone stale. Every major enterprise ATS shipped a resume-vs-job match score between 2024 and 2026, several with documented mechanics. A simulator must model the ranking layer honestly without inventing the rejection layer.

---

## Section 1: Resume parsing vendors

### 1.1 Who owns what (the consolidation matters)

| Engine | Owner | Verification |
|---|---|---|
| Textkernel (+ Sovren) | **Bullhorn**, acquired 18 Jun 2024 | [bullhorn.com](https://www.bullhorn.com/blog/bullhorn-acquires-textkernel-to-accelerate-its-ai-strategy/) |
| Sovren | Merged into Textkernel, Nov 2021 | [textkernel.com](https://www.textkernel.com/learn-support/blog/textkernel-acquires-us-based-software-company-sovren-to-become-the-global-leader-in-ai-powered-recruitment-technology-2/) |
| ALEX | HireAbility (independent) | [hireability.com](https://www.hireability.com/products/) |
| DaXtra | DaXtra Technologies | [daxtra.com](https://www.daxtra.com/) |
| RChilli | RChilli | [rchilli.com](https://www.rchilli.com/solutions/resumeparser) |
| Affinda | Affinda | [affinda.com](https://docs.affinda.com/configuration/ocr) |
| SmartRecruiters | **SAP**, acquired 11 Sep 2025 | [news.sap.com](https://news.sap.com/2025/09/sap-completes-smartrecruiters-acquisition/) |

**[FACT]** Textkernel is owned by Bullhorn (June 2024, reported at ~€300M). Textkernel's own developer docs now route support to `TXsupport@bullhorn.com`, confirming the integration ([Textkernel getting-started docs](https://developer.textkernel.com/tx-platform/v10/resume-parser/overview/getting-started/)). Textkernel had previously been owned by CareerBuilder (2019) and Main Capital Partners (2021) ([Techzine](https://www.techzine.eu/news/analytics/121381/dutch-ai-recruiter-textkernel-acquired-by-us-based-bullhorn-for-300-million-euros/)).

**[FACT]** SAP completed its SmartRecruiters acquisition on 11 September 2025, and SmartRecruiters will **entirely replace** the SuccessFactors Recruiting module, with customers given 3–5 years to migrate ([SAP](https://news.sap.com/2025/09/sap-completes-smartrecruiters-acquisition/); [CIO, quoting SuccessFactors president Daniel Beck](https://www.cio.com/article/4068172/sap-sets-timeline-to-replace-successfactors-recruiting-module-with-smartrecruiters.html)). **This means "SuccessFactors Recruiting" is a deprecating target.** Any simulator modelling SuccessFactors should treat it as legacy.

### 1.2 CORRECTION: iCIMS did not acquire HireAbility

**[MYTH]** A widely-copied claim — originating in a GitHub research compilation ([`sunnypatell/ats-screener`](https://github.com/sunnypatell/ats-screener/blob/main/research/ats-platform-research.md)) and propagated through `ats-screener.vercel.app` and several content farms — states that **iCIMS acquired HireAbility and that ALEX powers iCIMS**. I could find **no primary source for this**: no iCIMS press release, no HireAbility announcement, and HireAbility's own site still describes itself as an independent company founded 1999 in Londonderry NH with no mention of iCIMS ([hireability.com](https://www.hireability.com/hireability-resume-job-parsers/)).

What *is* verifiable is that iCIMS acquired **Opening.io** (an AI matching firm) in 2020, which underpins its Role Fit AI ([Integral Recruiting analysis](https://integralrecruiting.com/ai-candidate-screening-how-does-icims-compare/)).

**Do not encode parser-to-ATS mappings from third-party compilations.** Most ATS vendors do not publicly disclose their parsing engine. Treat the mapping as unknown unless the vendor says so.

### 1.3 Textkernel: the best-documented parser in the industry

Textkernel's public developer docs are the single richest primary source available, because they document *failure* candidly.

**Supported formats [FACT]** ([Supported File Formats](https://developer.textkernel.com/TKPlatform/master/file-formats/)):
- 70+ document formats: PDF, DOC/DOCX, HTML, RTF, TXT, ODT, Apple Pages
- Archives (CVs only): ZIP, EML — max 10 files, one auto-identified as the resume
- Images via optional OCR add-on: PDF(image), BMP, JPG, GIF, PNG, TIFF
- Compression formats not supported as general input ([FAQ](https://developer.textkernel.com/tx-platform/v10/faq/))

**Published accuracy [FACT]**: "Our standard parser… achiev[es] **over 95% accuracy for the most critical data points**. Textkernel's LLM Parser elevates accuracy even further, **reducing the remaining errors by up to 30%**" — but the LLM parser "requires more time for parsing and comes at a higher cost" ([FAQ](https://developer.textkernel.com/tx-platform/v10/faq/)). Note the careful hedge: *critical data points* on *typical* resumes, not all fields.

**OCR incidence [FACT]**: "On average, approximately **5% of documents require OCR**." OCR is capped at **10 pages** and **120 seconds** ([Getting Started](https://developer.textkernel.com/tx-platform/v10/resume-parser/overview/getting-started/)).

**The parsing pipeline is two-stage, and stage 1 is where things break [FACT]**:

> "First, we convert the source document to plain text, analyze it, and decide if the text is usable… **The vast majority of problems in parsing are not from processing the plain text, but from conversion to plain text.** … when you find a mistake in the output, don't assume it's a parsing mistake. Look at the converted text and see if the converted text is as expected (reads logically). If the converted text is malformed, we cannot fix it."
> — [Getting Started](https://developer.textkernel.com/tx-platform/v10/resume-parser/overview/getting-started/)

**This is the most important architectural fact in the whole report.** Text extraction, not NLP, is the dominant error source. A simulator should model extraction as its own explicit stage.

**On PDF specifically [FACT]** — and note this is a parsing vendor, not a resume-services company, so there's no incentive to scaremonger:

> "If you want to minimize conversion problems, **don't use PDF documents**. Many PDFs convert/parse fine; however, the reason for most of our 'this document did not parse correctly' bug reports is that the document is a **corrupt PDF file**. PDF is a broken standard that often hides issues with the underlying text."

**Documents Textkernel predicts will fail [FACT]** (same page):
- **Artists & graphic designers** — "candidates will use images instead of text, have text run diagonally across the resume, use vertical text"
- **Long academic/medical CVs** — "tens of pages… flooded with patents, publications, and speaking events… often at a school or university [so] it is easily confused with education"

**Fields Textkernel tells integrators NOT to trust [FACT]** ([Parser Output](https://developer.textkernel.com/tx-platform/v9/resume-parser/overview/parser-output/), [Integration Steps](https://developer.textkernel.com/tx-platform/v10/resume-parser/overview/integration-steps/)):

> "These sections are impossible to parse at a granular level with any meaningful accuracy. Do not use this data except perhaps as an indicator that the document contains such sections."

This applies to **patents, publications, speaking engagements, and training**. Explicitly: "it is a mistake to use speaking engagements/patents/publications data in any other capacity than simply a blob of text."

**Document Last Modified Date [FACT]** — an under-appreciated mechanic:

> "To parse a resume accurately, you must tell us when that resume was written… **it is 100x more important than any other setting**… If you leave this date off and parse a batch of 1 million resumes, your oldest and least employable candidates will be distorted as the most experienced, most employable, ready-to-go-to-work candidates."

Because it governs how "Present" / "current" resolve into date ranges. A resume saying "2015 – Present" yields wildly different tenure depending on this parameter.

**Anti-gaming guidance [FACT]** — Textkernel advises its integrators: "we do not recommend letting candidates review the skills/taxonomies. Letting a candidate edit this data would make it easy for someone to 'game the system'" ([Integration Steps](https://developer.textkernel.com/tx-platform/v10/resume-parser/overview/integration-steps/)).

### 1.4 Textkernel's ResumeQuality codes — a ready-made rule set

**[FACT]** Textkernel returns machine-readable resume-quality findings in four severity bands. This is the closest thing in the industry to a published, testable spec of "what makes a resume parse badly," and it is directly implementable. Full table: [Parser Output](https://developer.textkernel.com/tx-platform/v9/resume-parser/overview/parser-output/).

**Fatal (400–499):**

| Code | Meaning |
|---|---|
| 408 | Document too long, truncated before parsing |
| 411 | Time limit exceeded; some data not processed |
| 412 | No sections found |
| 413 / 414 | No WORK HISTORY / no EDUCATION section found |
| 415 / 416 | Work history / education found but had to be *inferred* as a section |
| 417 | Likely a CV; "prone to errors due to the use of nonstandard headers"; **only the first work-history section was parsed** |
| 418 | Date ranges written vertically across multiple lines |
| 419 | Employment section gave no dates for jobs |
| 433 | **Columnar data detected and rearranged** (see below) |
| 441 | Neither email nor phone found |

**Major (300–399):**

| Code | Meaning |
|---|---|
| **300** | **"Indicates that the document was PDF."** |
| 301 | Document was Apple Pages |
| 302 | First and last name not found |
| 303 | Sections found longer than work history + education combined — "usually indicates an issue identifying the sections correctly" |
| 311 | Contact info found somewhere other than the top of the resume |
| 312 | Publications section with significant content |
| 323 | Multiple sections of the same type |
| 324 | Sections with no text other than the header |
| 325 | Sections with no header |
| 331 | More than 30 jobs found |

**Data issues (200–299):** no email (211), no phone (212), no street address (213), jobs without titles (221), jobs without company names (222), jobs without start dates (224) or end dates (225), degrees without degree names (231) or school names (232), no jobs within a year of the document date (226).

**Suggestions (100–199):** references section present (111), separate skills section present (112), driving licence number (121), passport number (122), marital status (123), date of birth (124), multiple emails (132) or phones (133), **section header not on a separate line above its content (151)**.

Two of these deserve emphasis:

**Code 433 refutes the strong form of the column myth [FACT]:**

> "We detected that this document contained data in columnar format. **We rearranged this data to be machine readable with greater accuracy.** It is a HUGE MISTAKE for candidates to represent data in columns rather than in a simple top-to-bottom, all-across-the-page format."

So a leading parser **detects and repairs** columns — it does not choke on them. Textkernel also markets "Column layout auto-detection" and "efficiently handling both single and multi-column resumes" ([product page](https://www.textkernel.com/products-solutions/parser/)). Columns are a *degradation and warning*, not a fatal error, in this engine. That distinction matters enormously for honest simulation.

**Code 300 is the strongest vendor-neutral evidence that PDF is worse than DOCX [FACT]:** the mere fact that a document is a PDF is classified as a *Major Issue* in resume quality. Not fatal. Not "unreadable." But materially worse than DOCX, per the parser vendor itself.

**Critical caveat the docs shout about [FACT]** — do not misuse these codes:

> "The ResumeQuality section output should **NEVER IN ANY SENSE WHATSOEVER** be [interpreted] as an indication [that the] Parser has failed… The sole [purpose is for] you, the [integrator], to understand substandard aspects of the candidate's resume… **Great resumes will parse great. Horrible resumes will parse poorly. That is a limitation of the quality of the resume. The Parser [cannot] fix candidate mistakes.**"

Textkernel also notes most resumes are mid-distribution: "candidates' resumes fall within a bell curve… Most fall into the Good to Pretty Good range."

### 1.5 Affinda: concrete, thresholded OCR behaviour

**[FACT]** Affinda documents an exact, implementable OCR decision rule ([docs.affinda.com/configuration/ocr](https://docs.affinda.com/configuration/ocr)) with four modes:

| Mode | Behaviour |
|---|---|
| Never | OCR never applied even with no text layer. "Not recommended for most use cases." |
| **Default** | **OCR applied when fewer than 25 words are in the text layer**; extracted text overwrites the existing layer. With >25 words, OCR is not applied. |
| Partial | OCR applied only to elements lacking a text layer; preserves machine-readable text |
| Always | OCR replaces any existing text layer. "Only recommended when the text layer in a document is frequently incorrect." |

**The 25-word threshold is the single most concretely modellable number I found in this research.** It also names the exact pathology behind "my resume parsed as garbage":

> "If extraction is producing duplicated text, garbled output, or wildly incorrect values despite the document looking fine visually, the PDF may have a **corrupted or duplicated text layer**."

And critically — a PDF with a *bad but present* text layer is worse than one with *no* text layer, because it silently defeats the OCR fallback:

> "a document may be submitted that has a text layer that does not perfectly match the data in the document itself. Whilst this is uncommon, it means that Affinda has not applied OCR technology and thus **we will not be able to accurately extract the data**."

**[WEAK]** Affinda's marketing claims "accuracy rates above 99%, even on resumes with complex layouts, multiple columns or mixed languages" and image-based object detection for reading order ([blog](https://www.affinda.com/blog/ai-resume-parser/)). Unaudited vendor marketing; the 99% figure has no published methodology or test set. Treat as aspiration, not measurement.

### 1.6 Other engines

**[FACT]** **HireAbility ALEX** ("Automated Linguistic EXpert") is described as "a **grammar-based parser** using proprietary semantic parsing algorithms… As a grammar-based resume parser ALEX assigns meaning to terms (words and sentences) based upon the context in which they appear," which it contrasts with "conventional 'key-word'-based and statistical parsers." Outputs XML or JSON; supports Word, PDF, Open Office, Excel, HTML, RTF, plain text; generates candidate summaries including "3 most relevant competencies (most used over the years)," years in management, and security clearance ([hireability.com/products](https://www.hireability.com/products/)).

**[FACT]** **RChilli** parses DOC, DOCX, PDF, RTF, TXT, ODT, HTM/HTML, DOCM, DOTM, DOT, DOTX in 40+ languages, and states it processes "over 4.1 billion documents every year" across "1,600+ top global recruiting platforms" ([rchilli.com](https://www.rchilli.com/solutions/resumeparser)). It ships native no-code SAP SuccessFactors connectors ([RChilli for SuccessFactors](https://www.rchilli.com/sap-successfactors/ai-agents)).

**[FACT]** **Textkernel** also integrates into SAP SuccessFactors ([integration page](https://www.textkernel.com/integrations/sap-successfactors/)) — so *multiple* parsers serve the same ATS depending on customer configuration. **There is no single "the SuccessFactors parser."** This generalizes: parser identity is a per-tenant configuration choice, not a per-ATS constant.

**[WEAK]** DaXtra advertises "up to 95% accuracy across 150+ data fields and 40+ languages" with industry-specific taxonomies and cloud/on-prem deployment. This figure appears in aggregator write-ups rather than DaXtra's own published documentation; I could not locate a DaXtra-published methodology.

**[FACT]** Textkernel claims it "parses a staggering 2 billion resumes and job postings yearly" and is "Trusted by more than 60% of the global HR Tech industry" ([product page](https://www.textkernel.com/products-solutions/parser/)) — vendor self-report, but from the vendor itself and consistent with its market position.

### 1.7 Standards: HR-Open and JSON Resume

**[FACT]** The **HR Open Standards Consortium** (non-profit, founded 1999; formerly HR-XML) publishes both XML (XSD) and JSON schemas. Release 4.1.1 includes Recruiting, Screening, Assessments, Interviewing, Compensation, Benefits, Timecard and Wellness schemas in both serializations ([hropenstandards.org/standards](https://www.hropenstandards.org/standards)).

**[FACT]** Its resume-specific work is the **Resumé/CV Project**, supporting JSON Schema and XSD with JSON-LD for discoverability ([Learn & Work Ecosystem Library](https://learnworkecosystemlibrary.com/initiatives/the-hr-open-standards-resume-cv-project/)).

**[FACT]** The lineage has moved: **LER-RS** (Learning and Employment Record Resume Standard, developed with the U.S. Chamber of Commerce Foundation's T3 Innovation Network) was **superseded by the Trusted Career Profile (TCP) in January 2026**, released as part of HR Open Standards 4.5. TCP combines LERs, Open Badges 3.0 and Comprehensive Learner Records into a verifiable profile ([LER schema crosswalk](https://ler.me/embeds/ler-schema-crosswalk.html)).

**[WEAK]** One practitioner who obtained release 4.4 reports the schema has "roughly 350 high-level elements, and nests down 28 levels," with resume-like content in the `Person Profile` type, and characterizes it as SOAP-oriented and enterprise-integration-focused ([Virag Consulting](https://viragconsulting.blog/2025/04/02/my-json-resume/)). Single-practitioner observation; the spec requires a free account to download, so I could not verify the element count directly.

**[FACT]** **JSON Resume** is a community open-source project. As of 2026 it consolidated into a Turborepo monorepo containing `@jsonresume/schema` (schema + validator), `resume-cli`, Rust serde bindings, ~46 official themes, and notably an **`@resume/ats-validator`** package for "ATS validation for resume HTML" ([github.com/jsonresume/jsonresume.org](https://github.com/jsonresume/jsonresume.org/)).

**Practical read:** HR-Open is the interchange standard real ATSs care about but is heavyweight and enterprise-facing; JSON Resume is the pragmatic developer-facing schema. For a simulator's internal canonical representation, JSON Resume is the sane choice, with HR-Open as an export target if enterprise interop is ever needed.

---

## Section 2: Per-ATS specifics

### 2.1 Market share (needed for honest weighting)

**[FACT]** Jobscan's 2025 ATS Usage Report (5th edition), methodology: they "reverse-engineered the career pages for each company" on the Fortune 500 list; separately analyzed detected ATS across 12,820 companies from 1M+ scanner uses ([Jobscan 2025 report](https://www.jobscan.co/blog/fortune-500-use-applicant-tracking-systems/)).

- **97.8% of Fortune 500 had a *detectable* ATS** in 2025 (489/500). Trend: 98.4% (2024), 97.4% (2023), 98.8% (2019), 98.2% (2018).
- Fortune 500 distribution: **Workday >39%**, **SuccessFactors 13.2%** — combined 52.4%. Taleo declining; iCIMS enduring.
- Broader market (12,820 companies): **Greenhouse 19.3%, Lever 16.6%, Workday 15.9%, iCIMS 15.3%**.

**Two honesty caveats.** First, "detectable ATS" ≠ "uses an ATS to screen"; 11 undetected companies may simply run in-house systems. Second, Jobscan sells resume-optimization software, so it has a commercial interest in ATS ubiquity — but the methodology here is disclosed and the measurement (detecting ATS on career pages) is mechanical and plausible. Note the general-market figures are drawn from *Jobscan users' scans*, which skews toward job-seeker-facing tech and startup employers.

**Important:** the enterprise and SMB distributions are almost disjoint. A simulator claiming to model "the ATS" is really modelling either Workday/SuccessFactors/iCIMS (enterprise) or Greenhouse/Lever/Ashby (startup). Their mechanics differ substantially.

### 2.2 Workday

**Parsed fields [FACT]** — Workday's own training documentation is explicit and the list is *short*:

> "Workday presents applicants with the option to attach a resume. **The parsed data includes: Personal and contact information; Work experience; Education; Languages.**"
> — [Workday: Prospects and Candidates](https://doc.workday.com/workday-education/en-us/course-manuals/recruiting-for-administrators/prospects-and-candidates.html)

**Skills are NOT directly parsed into the profile [FACT]** — they are *suggested* and candidate-confirmed:

> "Once a candidate applies to a job, Workday assesses the content of the application and resume, and from that content, **Workday suggests skills. Candidates can decide to keep or remove these prepopulated skills.** Additionally, Workday has the **Candidate Skills Cloud** feature. If configured, this feature **enables Workday to score candidate applications.**"

This confirms the user's premise about "Candidate Skills Match" and adds a mechanic worth modelling: **the candidate has an editorial step between parsing and scoring.**

**[FACT] Workday Skills Cloud** is "a universal skills ontology" using "machine learning and… graph technology" that can "understand the relevant skills to any structured or unstructured document, for example, a resume… and extract those pertinent skills and simultaneously represent such a document 'spatially'" ([Workday blog](https://blog.workday.com/en-us/foundation-workday-skills-cloud.html)).

**[WEAK]** The frequently-cited "200,000+ canonical skills" figure for Skills Cloud appears only in content-farm write-ups. Workday's own blog describes the ontology qualitatively without publishing a count. Do not cite the number.

**HiredScore [FACT]** — Workday announced intent to acquire HiredScore on **26 February 2024** ([Workday investor relations](https://investor.workday.com/news-and-events/press-releases/news-details/2024/Workday-Announces-Intent-to-Acquire-HiredScore-02-26-2024/default.aspx)); HiredScore AI for Recruiting became purchasable through Workday on **1 August 2024** ([Workday newsroom](https://newsroom.workday.com/2024-08-01-Workday-Transforms-How-Companies-Hire-and-Manage-Talent-with-New-AI-Powered-HR-Solutions?asPDF=1)).

**HiredScore grading [FACT]** ([doc.workday.com: Concept: HiredScore Grades](https://doc.workday.com/hiredscore/en-us/workday-hiredscore/recruiter-productivity-/concept--hiredscore-grades.html)):

Grades **A–D**, assigned "based on how well their resumes match the skills and qualifications specified in the job description":

| Grade | Definition |
|---|---|
| A | Candidate meets or exceeds the basic requirements |
| B | Candidate meets the basic requirements |
| C | Candidate meets some but not all of the basic requirements |
| D | Candidate doesn't meet the basic requirements |

**No grade is assigned when:** the candidate submits no resume; the resume is in an unsupported format; **there is no job description on the requisition**; or it's a campus/graduate requisition.

**Supported resume formats: DOC, DOCX, PDF, RTF, TXT** ([HiredScore reference PDF](https://doc.workday.com/content/dam/fmdita-outputs/pdfs/hiredscore/en-us/Workday-HiredScore.pdf), FAQ section). Note: **no ODT, no Pages, no images** — HiredScore is *narrower* than Textkernel. A `.pages` or `.odt` resume simply does not get graded.

**Recruiters can override [FACT]:** a `Change Grade` action exists — "When you change a candidate grade and provide a reason, these details display in a tooltip."

**Workday's own framing is anti-determinism [FACT]:** "candidates with grades C or D might still be a great fit for the role," with a worked example of a grade-C candidate being better-suited than A/B candidates.

**LLM-based grading, July 2026 [FACT]** — from the same release-notes PDF:

> "we enhance Workday HiredScore Spotlight basic qualifications matching and final grade assignment with the addition of a **Large Language Model (LLM)-driven approach that evaluates each screenable qualification individually against the candidate's parsed resume**… a new **Fit & Gap** view."

And the requisition parser now enriches each extracted qualification with metadata: **qualification type (required vs preferred)**, **section (experience / skills / education)**, and — notably — **"whether or not it's possible to screen the qualification, and if it can be evaluated with the information on a typical resume."**

That last field is a genuinely interesting, modellable concept: **not all job requirements are resume-screenable**, and the system explicitly classifies which ones are.

**Workday's guidance to its own customers [FACT]:** "We recommend that you use objective rather than subjective requirements on job requisitions," e.g. "2 years of experience in machine learning," "Certified in Python," "Degree in computer science."

**Other HiredScore mechanics [FACT]:**
- **Fetch** — automatic sourcing surfacing "up to 8 relevant leads per requisition… from your company database of applicants from up to the past **3 years**" ([Using Fetch](https://doc.workday.com/hiredscore/en-us/workday-hiredscore/hiredscore-fetch-/steps--using-hiredscore-fetch.html)). Configurable exclusions include prior rejection statuses, last-application age (1–4 years), and candidates active on other requisitions.
- **Global Talent Search** — filter previous applicants by name, location, years of experience, skills, education level, language, major, prior employer.
- **Smart resumes** — HiredScore "calculates employment gaps and time in position" and normalizes all resumes to one format for review.
- Latency: "approximately 5 to 15 minutes for new applicants to display in HiredScore. However, in some cases, it can take up to 24 hours."

**Bias-testing posture [FACT]:** Workday states "The Spotlight functionality was not designed as nor intended to be an AEDT as defined under the NYC Law," that its output "is not intended to be the sole criterion, weighted more heavily than any other criterion, or overrule conclusions from human decision-making," and that Workday engaged an external consultant for impact-ratio bias testing ([Workday responsible-AI page, archived](https://web.archive.org/web/20250810074028/https:/www.workday.com/en-us/legal/responsible-ai-and-bias-mitigation.html)).

#### Mobley v. Workday — the litigation record

This is the most legally significant fact in the space, and it is a court record rather than marketing.

**[FACT]** *Mobley v. Workday, Inc.*, No. 3:23-cv-00770-RFL (N.D. Cal.). On **16 May 2025**, Judge Rita Lin **granted preliminary certification of a nationwide ADEA collective** ([order, Dkt. 128](https://www.courthousenews.com/wp-content/uploads/2025/05/ai-applicant-recommendation-system-class-certification.pdf)). The court's own words:

> "Mobley is joined by four other plaintiffs over the age of forty, who allege that they too have applied for hundreds of jobs via Workday and have been rejected almost every time without an interview, allegedly because of age discrimination in Workday's AI recommendation system."

> "The critical issue at the heart of Mobley's claim is whether that system has a disparate impact on applicants over forty. That issue is susceptible to common proof… the proposed collective need not be identical in all ways, because its members are alike in the central way that matters: **they were allegedly required to compete on unequal footing due to Workday's discriminatory AI recommendations.**"

Collective definition: "All individuals aged 40 and over who, from September 24, 2020, through the present, applied for job opportunities using Workday, Inc.'s job application platform and were denied employment recommendations" ([Holland & Knight](https://www.hklaw.com/en/insights/publications/2025/05/federal-court-allows-collective-action-lawsuit-over-alleged); [Lexology](https://www.lexology.com/library/detail.aspx?g=b913169b-7c7a-4c17-9d71-e33ec05dfc05)).

**[FACT]** The court later **expanded the collective to cover HiredScore**, rejecting Workday's argument that HiredScore is "a separate product, built on a wholly separate technology platform." The order states: "The scope of the collective, at the preliminary certification stage, includes individuals whose applications were scored, sorted, ranked, or screened using HiredScore AI features," and ordered Workday to produce a customer list of those who enabled the features ([court order](https://s3.documentcloud.org/documents/26037637/mobley-v-workday-inc.pdf)).

**Two crucial caveats a simulator must not elide.** First, certification is **preliminary** and Workday may move to decertify; the court explicitly noted Workday "would then have an opportunity to present evidence that the collective is not, in fact, similarly situated." Second — and this is the part everyone gets wrong — **the court has made no finding that Workday's AI actually discriminates.** It found the *question* is common enough to litigate collectively. Workday has stated the suit lacks merit. Citing this case as proof that ATS AI rejects older candidates would be a serious misrepresentation of a procedural ruling.

**[WEAK]** Post-February-2026 developments (a March 2026 ruling on ADEA applicant coverage, a March 2026 amended complaint) are reported by a specialist newsletter ([aigovernanceforhr.com](https://www.aigovernanceforhr.com/p/the-mobley-v-workday-case-didnt-end)) that I could not corroborate against primary filings. Verify before citing.

### 2.3 Greenhouse

**This is where conventional wisdom is now outdated.** The old claim "Greenhouse doesn't score resumes" was true and is no longer.

**Parsing failures [FACT]** — Greenhouse publishes an unusually candid list ([Unsuccessful resume parse](https://support.greenhouse.io/hc/en-us/articles/200989175-Unsuccessful-resume-parse)):

Three causes: file too large, "fake resumes," and formatting issues.

- **Hard file-size limit: "Greenhouse Recruiting can't parse resumes larger than 2.5MB."**
- **"Fake resumes"** — a genuinely surprising mechanic: the parser rejects data it recognizes as placeholder. "the name First Last or the Town name won't be recognized as real data and will be automatically skipped by the parser." Fake company names ("Company 1", "Client 1", "Any Company"), job titles ("employee 1"), and school names are also skipped. Greenhouse even advises that anonymizing candidates should use "more creative test data (such as Mycomp, Inc.)."
- **Formatting issues**, verbatim:
  - Resumes with incomplete job titles (e.g. "Sr. Account Exec" instead of "Senior Account Executive")
  - "A resume with **spaces between the letters**. While it may appear cohesive to the naked eye, the parser won't recognize the separate letters as a single word"
  - Resumes including **graphics, photos, or word art**
  - Resumes **uploaded as an image** rather than a document
  - "Complex resumes with **tables, headers, and footers**"
  - "Resumes with the **name and contact information in the header, footer, or text box**"
  - "Resumes that have a **columned layout**"
  - "Resumes **without clear sections** and differing formats throughout each section"
  - "**Company names that don't include identifying words** such as Inc., Co., LTD, or LLC"

Greenhouse is careful about consequence: "these formatting issues may result in a **partial** resume parse that will need to be manually corrected and verified" — degradation, not rejection. And when a parse fails entirely, "the resume has only been attached to the candidate" and staff "manually input the candidate's details." **The document still reaches a human.**

**Talent Matching — Greenhouse now computes match scores [FACT]** ([Talent Matching](https://support.greenhouse.io/hc/en-us/articles/41396009937307-Talent-Matching)):

Available on new tiers (Core/Plus/Pro) with the "Real Talent" add-on. Mechanics:

- Recruiters build a **calibration**: a weighted list of skills/requirements. Greenhouse can generate a suggested calibration from a job description and scorecard attributes.
- **"Since the match score is spread across the selected skills, for clearer matches, we recommend focusing on 4–6 key skills."**
- Five categories: **Strong match / Good match / Partial match / Limited match / Needs manual review**
- Candidates are "grouped by match score and ordered by application date within each group"
- **Only applies to candidates in the first Application Review stage**
- The UI shows "the candidate's resume, with matched and similar keywords highlighted," plus counts like "Calibrated skills matched: 2 of 4" and "Matched terms on this resume: 4" — i.e. both **exact** and **similar** keyword matching
- **Both Talent Matching and resume parsing must be enabled** for full functionality
- Editing a calibration **re-scores all current Application Review candidates**; calibration history is versioned
- Recruiters can **override** a score "if you've manually reviewed the candidate's resume and decided that the information wasn't accurately represented"

**The unparseable-resume path is explicitly benign [FACT]:**

> "If a candidate cannot be assigned a match score (for example, **if their resume cannot be read by the system** or they have opted out of AI-assisted review) they are flagged as **'Needs manual review'** and highlighted in the user interface to be fully reviewed by a human."
> — [Operational readiness guide: Talent Matching policy](https://support.greenhouse.io/hc/en-us/articles/44682413339675-Operational-readiness-guide-Talent-Matching-policy)

**This is the most important single sentence in this report for simulator honesty.** In Greenhouse, a catastrophic parse failure routes you to *guaranteed human review* — arguably a better outcome than a mediocre machine score. The intuitive model "bad parse → invisible → rejected" is **wrong** here.

**No auto-rejection [FACT]**, stated three times across two documents:
- "Talent Matching is **assistive AI, not automated-decision-making**. It does not automatically advance or reject candidates. Recruiters and hiring managers remain responsible for all hiring decisions."
- "It does not automatically reject or advance candidates."
- Customer-facing disclosure language: "**Talent Matching does not automatically disposition any candidate or make hiring decisions.**"

Greenhouse also supports candidate **AI opt-out** requesting manual review, and configurable jurisdiction-specific disclaimers (citing California ADMT regulations and NYC-style requirements).

### 2.4 Lever

**Also outdated conventional wisdom.** Lever shipped Talent Fit.

**Search [FACT]** ([Searching the Database for Candidates](https://help.lever.co/s/article/Searching-the-Database-for-Candidates)):

> "The search algorithm will look for candidate names and any parseable content attached to candidate profiles, including **resumes, notes, and feedback forms**."

Operators **AND / OR / NOT**, parenthesized grouping, and field-specific filter chips:
- `Resume:` restricts to resume-parsed content only, "exclud[ing] any matching search terms that appear elsewhere on the candidate's profile, such as in notes and feedback forms"
- `titles:` matches "titles in candidate work histories (**parsed from their resumes**)"
- `card:` / `cards:` search interviewer ratings
- Negation example given: `Resume: (NOT "Java")`

**Note the leakage risk:** unfiltered Lever search matches recruiter notes and interview feedback, not just the resume. A candidate can surface in a search because of what a *recruiter* wrote about them.

**Talent Fit [FACT]** ([Talent Fit in Lever](https://help.lever.co/s/article/Talent-Fit-in-Lever), last published 29 Jun 2026):

- Enabled at `Settings > AI Features > Screening Companion`; per-job toggle; **no additional cost**
- "Talent Fit automatically identifies top-matched candidates based on job requirements, providing clear justification for each match"
- Uses **the job description and candidate resumes**
- Matched candidates are **labelled** "Talent Fit" next to their name — **a binary label, not a numeric score**
- Output structure: "**positives, areas for clarification, and concerns**"
- **Auto-reprocesses** "if there are any changes to the job description or their resumes"
- **Go-forward only:** "as new candidates apply, they will be evaluated by Talent Fit" — does not retroactively review existing applicants (Spring 2026 release allows manual re-runs on old jobs)
- **Not a filter:** "Talent Fit is **not intended to filter out candidates**, but to provide additional context on their background and highlight areas that require clarification"
- Non-matching ≠ unqualified: "If a candidate who's not a Talent Fit doesn't mean they don't have some of the skills, just that they aren't the top fit"
- **Deliberately not trained on hiring outcomes:** "We don't directly train our models on customer hiring outcomes, as this could result in biased recommendations." Asked about a thumbs-up/down feedback loop: "We want to be careful because we don't want to train our AI… we don't want to train on someone else's bias."
- All Lever AI features auto-enable an **AI Disclaimer Statement**
- Candid operational note: jobs can show "Talent Fit has been temporarily disabled for this job while we complete additional validation"

**[FACT]** Jobscan's Lever guide lists parsed fields as name, work history, job title, address, email, phone, LinkedIn profile, previous employers, education, skills ([Jobscan: Lever ATS](https://www.jobscan.co/blog/lever-ats/)). Third-party but from a firm that reverse-engineers ATSs; consistent with Lever's own `titles:` and `Resume:` search behaviour. Jobscan's accompanying claim that "Lever doesn't score your resume" is **now outdated** given Talent Fit.

### 2.5 Ashby

**Search [FACT]** ([Candidate Search](https://docs.ashbyhq.com/candidate-search)) — the most precisely documented boolean surface of any ATS I reviewed. `Full Text Resume Search` supports four match modes:

| Mode | Semantics |
|---|---|
| **Matches** | Case-insensitive exact match of all individual words, order-independent |
| **Contains** | Exact phrase in exact order, case-insensitive |
| **Equals** | Exact phrase **with exact capitalization** |
| **Similar** | Word variations — "searching `localization` may bring resumes containing `localized` or `localize`" (stemming) |

Operators: `OR` (`|`, `,`), `AND` (`&`, `+`), `NOT` (`!`) — note "using the text not/NOT will not work for this operation". Quoted phrases. **Prefix wildcard** (`*`): "`*script` — matches javascript, typescript"; "`*end` — matches frontend, backend". Grouping via `()` or `[]`.

Documented example: `"senior software engineer" and (python or java) and (remote or hybrid) and !(junior or intern or contractor)`

**Notable limitation [FACT]:** "can I search for terms or keywords used in notes added to the candidate profile? **No**, it is not currently possible" — the opposite of Lever.

**AI-Assisted Application Review [FACT]** ([product update](https://www.ashbyhq.com/product-updates/ai-assisted-application-review)):

- Recruiters define criteria in job settings; Ashby describes them as **must-haves, should-haves, nice-to-haves**
- "the AI is parsing through each resume, trying to find evidence as to whether the candidate '**Meets**' or '**Does not Meet**' the criteria you've defined. Once complete, the AI returns the best determination, along with rationale"
- Two failure states, usefully distinguished: "If the AI can't make a determination, the criteria evaluation will be marked as **unknown**. If the **resume is unreadable**, the criteria will be marked as **skipped**."
- Citations for every output: "Ashby gives you citations for all AI outputs, so you can verify, flag and override analyses" ([ashbyhq.com/ai](https://www.ashbyhq.com/ai))
- Bias guardrails: "in-app warnings for criteria that can lead to biases," "more direct warnings about potential Equal Employment Opportunity (EEO) violations," third-party auditing by **FairNow**
- Configurable **automated-processing legal notice** with a `hide scores` option that suppresses AI-informed scores from users if the candidate hasn't seen the notice ([AI-Assisted Application Review docs](https://docs.ashbyhq.com/ai-assisted-application-review))

**A genuine tension worth recording honestly.** Ashby's marketing states: "The AI **never 'ranks' or gives numerical ratings** to applicants, a human must always be involved in decision-making" ([ashbyhq.com/ai](https://www.ashbyhq.com/ai)), and its own blog quotes a talent leader: "No decisions are made for me. **No scoring or ranking is involved.**" ([Ashby blog](https://www.ashbyhq.com/blog/recruiting/ai-assisted-application-review-in-practice)).

But Ashby's **product documentation** describes an **`AI job criteria met percentage`** column: "sort by this column to move the best fit candidates (highest percentage) to the top of your review queue and identify the lowest fit candidates (lowest percentage) at a glance" ([AI-Assisted Application Review docs](https://docs.ashbyhq.com/ai-assisted-application-review)). The candidate-search FAQ confirms it: "If you are looking for a measure of AI criteria fit, refer to the **AI job criteria met percentage** column."

A sortable per-candidate percentage that orders a review queue **is a numeric rank**, whatever the marketing says. The defensible narrow reading is that the AI emits per-criterion verdicts and the percentage is a derived aggregate rather than a model-produced score. A simulator should model Ashby as per-criterion boolean verdicts *plus* a derived sortable percentage, and should not repeat "Ashby never ranks" as fact.

Ashby's search FAQ also draws a distinction worth preserving: `application review average score` and `average overall recommendation` "reflect **human reviewer input only** and are independent from AI-assisted application review criteria evaluations."

### 2.6 iCIMS

The most mechanically detailed public documentation of relative ranking I found.

**[FACT]** ([Understanding iCIMS AI Talent Explorer](https://community.icims.com/s/article/Understanding-iCIMS-Talent-Cloud-AI)) — formerly Talent Cloud AI; three features: **Candidate Ranking using Role Fit**, **Talent Discovery**, **Talent Match**.

**Role Fit is relative, tiered, and deliberately not absolute:**

| Scored candidates on the job | Tiers |
|---|---|
| ≤ 10 | 1 tier |
| 11–100 | 3 tiers |
| 101+ | 5 tiers |

> "The tier assigned is based on the candidate's relative scores relative to other applicants for the job, and **do not represent specific numerical ranges**… There are no specific score criteria per tier, and the tiers do not have to have an even distribution of candidates. **AI Talent Explorer does not provide specific (i.e., absolute) candidate scores (i.e., candidate scored a 90/100).**"

> "Candidates' rank and tier vary as new profiles are added to the job, or new candidates apply for the job."

**This is a fundamentally different model from Workday's absolute A–D grades, and it has a real consequence: in iCIMS your position depends on who else applied.** Applying early to a thin pool, or late to a strong one, materially changes your tier without your resume changing at all.

**Two scoring paths with different inputs [FACT]:**
- **Candidate Ranking** uses "specific text that is parsed from the candidate's **most recent resume** relating to relevant skills, experiences, and roles; candidate personal information is not included." Crucially: "**Scores do not reference candidate information from other sources (e.g., candidate profile fields).**"
- **Talent Discovery** is the inverse — "based on skills from **candidate profile fields**, including any skills extracted from the resume during profile creation. It does not include data that is only part of a candidate's resume."

**Sub-scores [FACT]:** hovering the Role Fit indicator reveals **skills match score** ("how well the candidate's identified skills fit the requirements of the job") and **experience match score** ("how well the candidate's previously held job titles and other work history details (e.g., length of employment) match the description of the job"). The visual is a dual ring: outer = score, inner = tier.

**Job-side inputs [FACT]:** the ranking engine uses standard Job Profile fields including **Qualifications**.

**An asymmetric re-scoring rule with real candidate consequences [FACT]:**

> "If any of the above Job profile fields are updated for a specific job, candidates for that job are automatically rescored… However, **if a candidate's information is updated at any time (e.g., if the candidate uploads a new resume), that candidate will not receive an updated Role Fit score for any jobs they have already applied to or been submitted for.**"

Employers can re-score; candidates cannot. This is directly relevant to advice a simulator might give: in iCIMS, fixing your resume after applying does not help that application.

**Opt-out and AEDT [FACT]:** a `Show Only Unranked` toggle and `Role Fit Status – Unranked` filter exist "for customers who configure a candidate consent or opt out option to AI ranking on a career site/portal," with iCIMS documentation on supporting NYC AEDT legislation.

**[WEAK]** iCIMS reportedly identified Candidate Ranking as an AEDT under NYC Local Law 144 and commissioned independent bias audits in 2022 and 2023, and acquired Opening.io in 2020 ([Integral Recruiting Design](https://integralrecruiting.com/ai-candidate-screening-how-does-icims-compare/)). Third-party analysis citing an iCIMS bias-audit PDF I did not retrieve directly.

**[FACT]** iCIMS search supports boolean within `Search by Keyword` ([iCIMS community](https://community.icims.com/articles/Knowledge/Searching-for-and-Adding-Candidates-in-iCIMS-Nurture)).

### 2.7 Oracle Taleo

Taleo's mechanism is **not resume-text scoring** — it is questionnaire-based prescreening. This is widely misreported.

**[FACT]** ([Oracle: Candidate Prescreening](https://docs.oracle.com/en/cloud/saas/taleo-enterprise/20d/otrec/candidate-prescreening.html); [Requisitions](https://docs.oracle.com/en/cloud/saas/talent-acquisition/19c/otfru/requisitions.html))

**ACE Prescreening** combines three elements: **disqualification questions, prescreening questions, and competencies**.

**Disqualification questions are the real auto-reject [FACT]:**

> "A disqualification question is a single-answer question that contains the minimum requirements for a candidate to be eligible for a job. For example 'Are you entitled to work in the United States?' When candidates apply for a job, it's mandatory to respond to the disqualification questions. **Answers to the disqualification questions decide if candidates move forward in the selection process or are automatically disqualified.**"

**Required vs Asset vs Weight [FACT]:**
- **Required** — "All hires have all Required qualifications"
- **Asset** — "does not have to be selected for the candidate to be considered… but would distinguish this candidate compared to others. Think 'Strongly Preferred' and 'Nice-to-Have'"
- **Weight** — added to questions/competencies "to give them more consideration"

**ACE alert thresholds [FACT]** — configurable and explicitly recruiter-tunable:

| Option | Definition |
|---|---|
| Result | "A submission meeting all the prescreening required criteria and obtaining a result of at least *n*%" |
| Asset | "meeting all the prescreening required criteria and obtaining *n* of 3 assets" |
| Both | Result AND assets |
| Either | Result OR assets |

Recruiters "have the option to reset the Required, Asset and Weight indicators as well as the ACE alert to modify the threshold if necessary to obtain a viable pool of top candidates."

**The scored inputs are candidate *answers*, not resume prose [FACT]:** "Competencies and questions are **answered by candidates**. The candidates' responses… are filtered by the system and presented on the candidates list." An `Ace Candidate` icon marks top candidates.

**Automatic progression exists [FACT]** ([Candidate Selection Workflow](https://docs.oracle.com/en/cloud/saas/taleo-enterprise/20a/otrcg/candidate-selection-workflow.html)) — conditions can auto-advance candidates, with a documented caveat that if prescreening questions are not mandatory, "the candidate will be [considered as not meeting] required criteria."

**Autopooling [FACT]** surfaces matching candidates from other requisitions, capped at 300 displayed ([Recruiting Fundamentals](https://docs.oracle.com/en/cloud/saas/taleo-enterprise/21b/otrcg/recruiting-fundamentals.html)).

**Simulator implication:** modelling Taleo as "keyword-scores your resume" is wrong. Model it as a **weighted questionnaire with a hard disqualification gate and a tunable ACE threshold.** Resume text feeds recruiter boolean search, not the ACE score.

### 2.8 SmartRecruiters (now SAP)

Publishes the most transparent scoring architecture of any vendor here, in a public AI whitepaper.

**[FACT]** ([SmartRecruiters AI Whitepaper](https://ta.smartrecruiters.com/rs/664-NIC-529/images/SmartRecruiters-AI-Whitepaper.pdf?version=1); [Volume 3](https://ta.smartrecruiters.com/rs/664-NIC-529/images/SmartRecruiters%20-%20AI%20Whitepaper_Volume%203_july%2015.pdf?version=0))

**SmartAssistant Match Score — full documented pipeline:**

1. Extract from **job title, job description, and qualifications sections** of the Job Ad; infer required skills
2. Same process on the candidate's CV/application, extracting skills from **employment history, education, and resume text content**
3. **Normalize skills to the European Commission's ESCO taxonomy — "nearly 14,000 skills and over 3,000 occupations"**
4. Compare skill sets "using a Deep Learning AI algorithm trained on historical SmartAssistant customer data"
5. Output: **5-star scale.** "scores of 4 and 5 stars considered high confidence in a good match, and 1-2 stars is considered low confidence"

**The prediction target is unusually well-specified [FACT]:** the model predicts "the likelihood of a candidate **advancing in the hiring process past the CV screening phase**." And explicitly *not* hiring:

> "The model does not factor in the likelihood of being hired because **interviews are often subject to human bias**, and we do not have visibility to ensure this would not impact the model results."

**Timing and recalculation [FACT]:** "The score is calculated when the candidate's application is added… each candidate is assigned an **independent Match Score for each job funnel** they are a part of. Match Scores are **recalculated if there are any changes to the critical sections of the Job Ad**. **Candidates do not see their Match Score**; this information is generally only shared with applicants as required by data transparency requirements."

**Explicit no-decision statement [FACT]:** "It does not make any hiring decisions; candidates are moved forward or rejected by recruiters." And: "**AI-generated scores cannot be used as a criterion for automating hiring processes such as making offers, rejecting candidates, or moving candidates to a new stage.**" With an honest addendum: "users should still be trained in AI literacy so they don't overweigh said recommendations."

**Bias mitigation with specifics [FACT]:** no collection of age, sex, sexual orientation, ethnicity, political affiliation or religion; no photo/video processing; training data anonymized; and notably "**we remove the names of universities** from training data and ranking generation to ensure hidden human bias does not lead to biased model results." Annual third-party bias audit "As required by New York City Law 144."

**Winston Match (July 2025, next-gen) [FACT]** ([product page](https://www.smartrecruiters.com/recruiting-software/talent-matching/); [July 2025 release](https://assets.smartrecruiters.com/resources/article/july-2025-product-release-highlights-talent-matching-powered-by-gen-ai/)):

Dimensions scored separately then ensembled:
- Skills match (resumes vs job descriptions)
- Work experience (title, seniority, trajectory)
- Education and certifications
- Job title relevance

> "Each dimension is scored using separate models and then **ensembled into a single weighted score. The weights reflect the relevance of each dimension for that specific job**, based on real-world hiring outcomes."

**⚠️ SmartRecruiters ships a real auto-reject [FACT]** — the clearest counterexample to a blanket "no ATS auto-rejects" claim:

> "**Auto Reject in Workflows** — With Auto-Rejection Rules, admins can now create workflows to reject unsuitable applicants based on **up to 10 custom conditions per hiring step**."
> — [July 2025 Product Release Highlights](https://assets.smartrecruiters.com/resources/article/july-2025-product-release-highlights-talent-matching-powered-by-gen-ai/)

Note the architecture: auto-rejection is a **separate workflow-rule feature**, distinct from the AI match score (which the whitepaper forbids using for automated dispositioning). The honest framing is: **rule-based auto-rejection exists and is expanding; score-based auto-rejection is contractually/architecturally prohibited.**

### 2.9 SAP SuccessFactors

**[FACT]** SuccessFactors Recruiting is being **replaced by SmartRecruiters** over 3–5 years ([CIO](https://www.cio.com/article/4068172/sap-sets-timeline-to-replace-successfactors-recruiting-module-with-smartrecruiters.html)). SAP describes SmartRecruiters for SAP SuccessFactors as "the next-generation recruiting solution that **builds on and replaces the legacy SAP SuccessFactors Recruiting module**" ([sap.com](https://www.sap.com/products/hcm/recruiting-software.html)).

**[FACT]** SuccessFactors' parsing is supplied by **third-party partners**, not one native engine — both **Textkernel** ([integration page](https://www.textkernel.com/integrations/sap-successfactors/)) and **RChilli** ([RChilli for SuccessFactors](https://www.rchilli.com/sap-successfactors/ai-agents)) offer native integrations. RChilli "maps this data using standardized taxonomies (Picklists) for consistent candidate records."

**Simulator implication:** SuccessFactors parsing behaviour is **tenant-dependent**. There is no single correct model. Given ~13% of the Fortune 500 and a migration path to SmartRecruiters, model it as "configurable third-party parser + deprecating."

### 2.10 BambooHR

**[FACT]** BambooHR candidate keyword search covers "**resumes, cover letters, locations, and answers to application questions**" ([BambooHR product update](https://www.bamboohr.com/product-updates/candidate-keyword-search-enhancements)).

**[FACT]** BambooHR's public API shows the application form is a **fixed set of standard question toggles** (`applicationQuestionResume`, `Address`, `LinkedinUrl`, `DateAvailable`, `DesiredSalary`, `CoverLetter`, `ReferredBy`, `WebsiteUrl`, `HighestEducation`, `College`, `References`), each settable to `true` / `false` / `Required` ([BambooHR API: Create Job Opening](https://documentation.bamboohr.com/reference/create-job-opening)). This is a **structured-form-first** design — far less resume-parsing-dependent than enterprise ATSs.

**[WEAK]** The claim that BambooHR ships **no native resume parsing**, relying on manual review or third-party bolt-ons (CandidateZip, Parseur), comes from a content-farm source I've otherwise excluded. It is *consistent* with the API evidence above (fixed form fields, no parsed-entity endpoints) and with BambooHR's marketplace listing parsing integrations, but I found **no BambooHR statement either way**. Flag as unverified; if BambooHR matters to the product, test it directly.

### 2.11 Jobvite

**[FACT]** Full boolean search ([Candidates Tab](https://help.jobvite.com/s/article/Candidates-Tab)): `AND` (implied by default — "you will get the same results if you type Java AND Perl as if you type Java Perl"), `OR`, quoted phrases for adjacency. Search composes with filters. Multiple custom-field filters use AND logic. Jobvite recommends uploading the resume first "so that it can parse the information into the correct fields for you."

**Knockout mechanics [FACT]** ([Pre-screening Forms](https://help.jobvite.com/s/article/Pre-screening-Forms)) — several details are unusual and highly modellable:

- **Only the first knockout question is evaluated if the workflow changes:** "By default, the most important question is at the top. Evolve ATS won't look at the knock-out questions after the first one if their workflow changes. If the workflow doesn't change, the next knock-out question will apply."
- **No retroactivity:** "knockout questions and pre-screening forms only apply to candidates who apply **after** the questions are added. Existing applicants will not be re-screened."
- **Knocked-out candidates get no automatic rejection email:** "Their status has just changed to Rejected." Jobvite recommends a `Reject Later` status "to help track knocked-out candidates for later rejection" — explicitly "This would be a poor [candidate] experience" otherwise.
- Prescreen answers become searchable only if mapped to a standard/custom field **and** added to `Admin > ATS > Candidate Search`.
- Knock-**in** questions also exist; a candidate can be auto-moved to `Submit to Hiring Manager`.

**Simulator implication:** "auto-rejected in 5 minutes with an email at 2am" is *not* the Jobvite behaviour. Silent status change, delayed or absent email. This matters for candidate-experience modelling.

### 2.12 Per-ATS summary

| ATS | Parses resume → fields | Search | Automatic score / rank | Documented auto-reject |
|---|---|---|---|---|
| **Workday** | Yes: contact, work experience, education, languages. Skills *suggested*, candidate-confirmed | Boolean/keyword over parsed text | **Yes** — HiredScore grades **A–D** (absolute); Candidate Skills Cloud scoring; LLM per-qualification Fit & Gap (2026) | Not by score. Workday states Spotlight isn't intended as an AEDT |
| **Greenhouse** | Yes; documented failure list; 2.5MB cap | Recruiters search parsed text; original file shown | **Yes** — Talent Matching: Strong/Good/Partial/Limited/Needs manual review, from weighted calibration (4–6 skills recommended) | **No.** Stated 3× in docs. Unparseable → *guaranteed human review* |
| **Lever** | Yes | Boolean `AND/OR/NOT`, chips `Resume:` `titles:` `card:`; also searches notes & feedback | **Yes** — Talent Fit binary label + positives/clarifications/concerns; go-forward only | **No.** "not intended to filter out candidates" |
| **Ashby** | Yes; 16MB limit | Richest boolean: matches/contains/equals/similar, prefix `*`, grouping. **Cannot** search notes | Per-criterion Meets/Does not Meet/unknown/skipped **+ sortable "AI job criteria met percentage"** (see §2.5 tension) | **No.** Reviewer advances/rejects |
| **iCIMS** | Yes | Boolean keyword | **Yes** — Role Fit, **relative tiers** (1/3/5 by pool size), no absolute score; skills + experience sub-scores | Advisory. Opt-out supported; treated as AEDT under NYC LL144 [WEAK] |
| **Taleo** | Yes (for search) | Boolean | **ACE score from questionnaire answers**, not resume prose; Required/Asset/Weight; tunable % threshold | **Yes** — disqualification questions auto-disqualify |
| **SuccessFactors** | Via 3rd-party (Textkernel/RChilli), tenant-dependent | — | Varies by configuration | — (being replaced by SmartRecruiters) |
| **BambooHR** | Native parsing unverified [WEAK]; fixed standard form fields | Keyword over resumes, cover letters, locations, application answers | None documented | None documented |
| **Jobvite** | Yes | Full boolean, AND implied | None documented | **Yes** — knockout/knock-in; first knockout only if workflow changes; no auto email |
| **SmartRecruiters** | Yes | — | **Yes** — SmartAssistant 5-star via ESCO (14k skills/3k occupations), predicts *passing CV screen*; Winston Match ensembles skills/experience/education/title with per-job weights | **Yes** — Auto-Rejection Rules, up to 10 conditions per step (separate from the score) |

---

## Section 3: Myths vs reality

### 3.1 "75% of resumes are rejected by ATS before a human sees them" — **[MYTH]**

**Traced origin.** HR consultant **Christine Assaf** documented the trail in "Your job application was rejected by a human, not a computer," reprinted with permission on Ask a Manager ([askamanager.org, Oct 2020](https://www.askamanager.org/2020/10/your-job-application-was-rejected-by-a-human-not-a-computer.html); original at [hrtact.com](https://hrtact.com/2020/10/05/your-job-application-was-rejected-by-a-human-not-a-computer/)).

Her account: a conference speaker asserted "75% of applications are rejected by an ATS… and a human never sees them," citing topresume.com. Following the chain, sources gave "no links, but instead reference 'job search services firm **Preptel**'." And:

> "Preptel, the company who provided amazing, job seeker resume-writing and a totally unbiased study **went out of business in August 2013**."

Her conclusion:

> "the statement '75% of applications are rejected by an ATS system' is just false. It's false, because **there's no concrete source data, or research to even back up the statement**."

And in a follow-up interview:

> "as suspected, I didn't find any conclusive statistical evidence of this premise. Merely conjecture. **It's simply not true that ATS systems auto-reject. They may weigh, or sort, or filter, but any recruiter will tell you that most if not all resumes are reviewed by a person.**"
> — quoted in [HiringThing](https://blog.hiringthing.com/applicant-tracking-system-myths)

**Laundering path [FACT].** The claim gained authority through citation rather than evidence:
- A **March 2014 Forbes** article: "Studies have shown that up to 75% of qualified applicants are rejected by ATS programs because they can't be read" — written by "the founder of a resume service" ([documented at newsletter.jobsearch.guide](https://newsletter.jobsearch.guide/p/is-it-true-that-over-75-of-resumes))
- **April 2018 CIO.com**: "75 percent are never seen by a real person" — no data cited
- **2019 CNBC** repeated it, attributing to Preptel ([HiringThing](https://blog.hiringthing.com/applicant-tracking-system-myths); [CNBC](https://www.cnbc.com/2019/02/28/resume-how-yours-can-beat-the-applicant-tracking-system.html))

A plausible **misreading** origin: a 2013 article describing a hiring funnel as "75 of those 100 resumes will be screened out **by either the ATS or a recruiter**, 25 resumes will be seen by the hiring manager" ([jobsearch.guide](https://newsletter.jobsearch.guide/p/is-it-true-that-over-75-of-resumes)). The "or a recruiter" disjunct — carrying most of the actual work — got dropped. A funnel statistic about *human plus machine* triage became a claim about *machines alone*.

**[WEAK]** Enhancv's survey of 25 US recruiters found 23/25 (92%) said their ATS does **not** auto-reject for formatting, design or content; the 2 exceptions used Bullhorn and BambooHR "configured to auto-reject resumes that didn't meet specific match or experience thresholds." On AI scores: 44% had an AI/fit score available, 36% used it "as a guide only," 8% used it definitively, 56% ignored it or lacked it ([Enhancv](https://enhancv-cms.herokuapp.com/blog/does-ats-reject-resumes/)).

**n=25 is far too small to support the widely-quoted "92% of recruiters" headline**, which now circulates with the same false precision as the 75% figure it debunks. Directionally consistent with vendor documentation; not a statistic to cite as fact. Note also the 8% who *do* use scores definitively — the honest picture is "mostly no, with real exceptions," not "never."

**What Jobscan itself says [FACT].** Jobscan — which sells ATS optimization and is often blamed for spreading the myth — does not use the 75% claim in its 2025 research and instead grounds its position in the HBS survey ([Jobscan 2025 report](https://www.jobscan.co/blog/fortune-500-use-applicant-tracking-systems/)). Its current framing is retrieval-based, not rejection-based:

> "If you miss out on opportunities to highlight the details recruiters are searching for, **they may never see your resume**, even if you fit all the employer's requirements."

Jobscan also states **76.4% of surveyed recruiters "search and rank candidates by skills from the job description,"** then education, job title matches, licences/certifications, and years of experience (Jobscan *State of the Job Search Report*) — **[WEAK]**, as the underlying survey's n and sampling frame aren't given on that page.

Its marketing still says "99% of Fortune 500" while its own 2025 research measured **97.8%** — a small but real overstatement in the direction of its commercial interest.

### 3.2 "Does any major ATS auto-reject based on a keyword score?"

**Answer: No documented major ATS auto-rejects on a resume keyword/match score. Several auto-reject on structured rules.** Keep these two distinct.

**[FACT] Explicit vendor prohibitions on score-based dispositioning:**
- Greenhouse: "It does not automatically reject or advance candidates."
- SmartRecruiters: "AI-generated scores cannot be used as a criterion for automating hiring processes such as… rejecting candidates."
- Lever: "not intended to filter out candidates."
- Ashby: "a human must always be involved in decision-making."
- Workday: Spotlight output "is not intended to be the sole criterion, weighted more heavily than any other criterion, or overrule conclusions from human decision-making."

**[FACT] Rule-based automatic rejection that genuinely exists:**
- **Taleo disqualification questions** — "Answers to the disqualification questions decide if candidates move forward… or are **automatically disqualified**"
- **SmartRecruiters Auto-Rejection Rules** — "up to 10 custom conditions per hiring step"
- **Jobvite knockout questions** — automatic status change to Rejected
- **[WEAK]** Greenhouse spam blocklists (auto-reject by email domain/address/IP) — referenced in secondary sources; I did not retrieve the primary Greenhouse doc

**The precise, defensible statement:** *automatic rejection is triggered by the candidate's answers to structured screening questions, or by administrator-configured rules, not by how a resume's text scores against a job description.*

### 3.3 Are PDFs unreadable? — **[MYTH]** as stated; **[FACT]** with nuance

**PDFs are read by every major engine.** Textkernel lists PDF first among 70+ formats; HiredScore accepts PDF; Greenhouse accepts PDF.

**But PDF is measurably the riskier choice, per parsing vendors themselves:**
- **[FACT]** Textkernel flags "the document was PDF" as **ResumeQuality code 300 — a Major Issue**
- **[FACT]** Textkernel: "If you want to minimize conversion problems, **don't use PDF**… the reason for most of our 'this document did not parse correctly' bug reports is that the document is a **corrupt PDF file**. PDF is a broken standard that often hides issues with the underlying text."
- **[FACT]** Affinda: a PDF whose text layer "does not perfectly match the data in the document" means "we will not be able to accurately extract the data" — because a *present but wrong* text layer suppresses the OCR fallback

**What is genuinely unreadable [FACT]:** a PDF with **no text layer** (scan/photo/flattened export) requires OCR. Textkernel: "Without OCR, such documents cannot be parsed," and ~5% of documents need it. Greenhouse lists "Resumes that are uploaded as an image, rather than a document" as a parse-failure cause. Where OCR isn't enabled, these fail hard.

**Honest formulation:** *PDF is fine when it carries a clean text layer. DOCX is marginally safer. Image-only PDFs fail unless the vendor has OCR enabled. "PDFs are unreadable" is false; "PDF is the higher-variance format" is true.*

### 3.4 Do headers/footers break parsing? — **[FACT]**, with important extractor-dependence

**Vendor-documented:**
- **[FACT]** Greenhouse lists "Complex resumes with tables, headers, and footers" and "Resumes with the name and contact information in the header, footer, or text box" as parse-failure causes
- **[FACT]** Textkernel code **311** flags "contact information section… found somewhere other than the top of the resume. Contact information should only be found at the top"
- **[FACT]** Textkernel code **441** flags neither email nor phone found

**Measured directly (this document, see §4.1):** whether header/footer text survives depends entirely on the extractor. `python-docx` reading `.paragraphs` and `mammoth` both **drop** header/footer text; Apache Tika and `docx2python` **retain** it.

**Honest formulation:** *contact details in a DOCX header or footer are dropped by some common extraction paths and retained by others. Since you cannot know which the employer uses, putting contact info only in a header is an avoidable coin-flip. This is not superstition — it is measurable, and it varies.*

### 3.5 Do tables and columns break parsing? — **[MYTH]** in strong form; **[FACT]** in weak form

**Against the strong claim:**
- **[FACT]** Textkernel **detects and repairs** columns (code 433: "We rearranged this data to be machine readable with greater accuracy") and markets "Column layout auto-detection"
- **[FACT]** Affinda uses "Reading-order algorithms: Interpreting documents in the way humans read them and improving accuracy on complex, **multi-column**, semi-structured or unstructured layouts" ([Affinda whitepaper](https://www.affinda.com/whitepapers/intelligent-document-processing-solutions))
- **[FACT]** Greenhouse's own language is *partial* parse requiring manual correction, not deletion
- **[FACT, measured]** Tika, `docx2python`, `docx2txt`, `mammoth` and thorough `python-docx` all **do** extract DOCX table cell contents (§4.1)

**For the weak claim:**
- **[FACT]** Textkernel calls columns "a HUGE MISTAKE" even while repairing them, and issues the warning at *Fatal* severity (400-band)
- **[FACT, measured]** **Naive `python-docx` `.paragraphs` extraction silently drops table cells entirely** (§4.1)
- **[FACT, measured]** **Two-column PDFs are interleaved row-by-row by both pypdf and Apache Tika/PDFBox at default settings** (§4.2) — reading order genuinely destroyed
- **[FACT]** Peer-reviewed: layout materially affects extraction quality even holding content constant (§4.3)
- **[FACT]** The 2018 Ladders study found the worst-performing resumes had "cluttered layouts characterized by long sentences, **multiple columns**, and very little white space" — so columns hurt with *human* readers too ([PRNewswire](https://www.prnewswire.com/news-releases/ladders-updates-popular-recruiter-eye-tracking-study-with-new-key-insights-on-how-job-seekers-can-improve-their-resumes-300744217.html))

**Honest formulation:** *good parsers detect and repair columns; naive extraction pipelines mangle them; two-column PDFs demonstrably interleave under the most common libraries. Single-column is the lower-variance choice — and it also tests better with human reviewers, which is the stronger argument.*

### 3.6 Do graphics/icons break parsing? — **[FACT]**, the most robust of the formatting claims

- **[FACT]** Greenhouse: "Resumes that include **graphics, photos, or word art**" cause parse failure; and files over 2.5MB fail, which image-heavy resumes readily exceed
- **[FACT]** Textkernel on designers: "candidates will use images instead of text, have text run diagonally across the resume, use vertical text… **Parsing can only be as accurate as the text extracted from the source document**"
- **[FACT]** Text inside an image is not text. Skill-rating bars, icon-only contact details, and name-in-a-logo carry **zero** extractable content absent OCR.

**This one is not outdated advice.** It follows from how extraction works, not from parser quality.

### 3.7 The HBS "Hidden Workers" report — what it actually found

The most-misquoted document in this field. Full text: [hbs.edu PDF](https://www.hbs.edu/managing-the-future-of-work/Documents/research/hiddenworkers09032021.pdf) (Fuller, Raman, Sage-Gavin, Hines, 2021; with Accenture).

**Methodology [FACT]:** two-year study; survey of **8,720 hidden workers** and **2,275 executives** across US, UK, Germany; employer survey fielded **January–February 2020** ([HBS Working Knowledge](https://www.library.hbs.edu/working-knowledge/how-to-tap-the-talent-automated-hr-platforms-miss)).

**Actual quotes:**

On prevalence of filtering/ranking:

> "more than 90% of employers in our survey use their RMS to initially filter or rank potential middle-skills (94%) and high-skills (92%) candidates. These systems are vital; however, they are designed to maximize the efficiency of the process. That leads them to hone in on candidates, using very specific parameters, in order to minimize the number of applicants that are actively considered."

On employment gaps — **the report's most concrete and most misused finding**:

> "Almost half the companies surveyed weeded out resumes that present such a 'work gap.' **If an applicant's work history has a gap of more than six months, the resume is automatically screened out by their RMS or ATS, based on that consideration alone.**… **A recruiter will never see that candidate's application, even though it might fill all of the employer's requirements.** Such filters obviously cannot infer what caused such a gap to occur; they simply express an absolute preference for candidates with no such gaps."

Quantified: "**48% of employers filtered middle-skills candidates based on employment gaps of more than six months.**"

On credentials:

> "A veteran, for example, may have skills required for a hard-to-fill position but not the specific civilian credentials on their resume. **The AI at the front end of the RMS/ATS would disqualify such an applicant.** The result: A potentially qualified candidate is 'hidden' from the recruiter."

On magnitude:

> "As many as **78% of the business leaders we interviewed estimated that half or more of middle-skills candidates were eliminated by filtering, and 80% said that more than half of candidates for high-skilled positions** were similarly disqualified."

On employer self-awareness — **the source of the widely-cited "88%"**:

> "A significant majority—**88%—of employers believed that qualified high-skills candidates were vetted out of the process because they did not match the exact criteria established by the job description. That number rose to 94% in the case of middle-skills workers.**"

On the mechanism:

> "companies regularly eliminate all but those candidates who most closely match the job requirements specified. Others are excluded from the process, however marginal their deficiencies. Workers lacking a 'nice to have' secondary qualification, who fail to meet some inferential proxy the employer relies on to weigh the relative merits of candidates, **or who describe some skills or experience using language that differs from that utilized in the job description** are dropped from consideration."

On remedy:

> "**Shifting from 'negative' to 'affirmative' filters** in an ATS or RMS. An ATS/RMS largely relies on 'negative' logic to winnow the applicant pool."

Also documented: **27M+ hidden workers in the US**; firms hiring them are "36% less likely to face talent and skills shortages"; only 20% of surveyed hidden workers ever became candidates; and applicant volume grew from "almost 120 applicants" per posting in the early 2010s to "an average of 250 applications" by decade's end.

**How the report is misused — and this is important for honesty:**

1. **It does not support the 75% claim.** No such figure appears.
2. **The "88%" is employer *belief*, not measurement.** The report asks employers whether they think qualified candidates get vetted out. It is a striking indictment precisely *because* it's self-aware — but it is opinion data, and citing it as "88% of qualified candidates are rejected" is flatly wrong.
3. **The 78%/80% figures are executive *estimates*** ("business leaders… estimated"), not instrumented funnel data.
4. **The mechanism is employer *configuration*, not parser behaviour.** Employment-gap filters and credential requirements are choices customers make. The report's target is hiring policy, not text extraction. It contains **no finding about resume formatting, keywords-as-formatting, PDFs, or tables.** Using it to justify formatting advice is a category error.
5. **The employer survey predates COVID (Jan–Feb 2020)** and predates the entire 2024–2026 LLM-scoring generation. Gap-filtering norms may well have shifted after mass pandemic unemployment.
6. **It relies on Jobscan for the Fortune 500 ATS figure** ("In 2019, 99 percent of Fortune 500 firms used applicant tracking software, according to job seeker platform Jobscan") — so this is not independent corroboration.

**The defensible summary:** *HBS/Accenture found that automated filtering is near-universal among large employers, that employers themselves believe it excludes qualified people, and that roughly half of surveyed employers configured a hard filter on employment gaps over six months. These are employer-configured rule filters, not resume-parsing artifacts, and the employer data is from early 2020.*

### 3.8 Which formatting advice is still true in 2025–2026?

| Advice | Verdict | Basis |
|---|---|---|
| Don't put contact info only in a header/footer | **Still true** | Greenhouse doc; Textkernel 311/441; measured extractor divergence (§4.1) |
| Avoid images/graphics/word art/skill bars | **Still true** | Greenhouse doc; Textkernel designer guidance; physics of extraction |
| Ensure a real text layer (no scans/flattened exports) | **Still true** | Textkernel OCR necessity; Affinda 25-word rule |
| Use standard section headings | **Still true** | Textkernel 412/413/414/417/325 |
| Prefer single-column | **Still true, weaker reason than claimed** | Good parsers repair columns (TK 433); but naive extraction and default PDF extractors interleave (§4.2); Ladders shows humans dislike columns too |
| Avoid tables for layout | **Partly outdated** | Most extractors read table cells (§4.1 measured); naive `python-docx` does not; Greenhouse still lists tables |
| DOCX marginally safer than PDF | **Still true** | Textkernel code 300 + explicit "don't use PDF" |
| Don't letter-space your name | **Still true** | Greenhouse explicitly documents this |
| Include Inc./LLC/Ltd. in employer names | **Still true, rarely mentioned** | Greenhouse explicitly documents this |
| Spell out job titles ("Senior" not "Sr.") | **Still true, rarely mentioned** | Greenhouse explicitly documents this |
| Use unambiguous `Month YYYY` dates | **Still true** | Textkernel 418/419/224/225 |
| Keep the file small | **Still true** | Greenhouse 2.5MB hard cap; Ashby 16MB |
| Don't include DOB/passport/marital status/driving licence | **Still true (US/UK/AU/NZ)** | Textkernel 121–124 |
| Stuff keywords / white-font keywords | **Bad advice** | Ladders: keyword stuffing among worst-performing; Ashby cites source text; Greenhouse shows highlighted resume to a human; Textkernel warns integrators about gaming |
| "Beat the 75% robot" | **[MYTH]** | §3.1 |
| Custom "creative" section names | **True — genuinely risky** | Textkernel 417 explicitly cites nonstandard headers; 325 flags header-less sections |

---

## Section 4: Concrete, testable parsing failure modes

### 4.1 MEASURED: DOCX extraction varies enormously by library

I constructed a probe DOCX containing uniquely-tagged text in seven locations and ran six extraction paths plus Apache Tika. **These are measured results, reproducible on demand.**

| Extractor | Body para | Table cell | Header | Footer | Link anchor | Link **URL** | **Text box** |
|---|---|---|---|---|---|---|---|
| `python-docx` (`.paragraphs` only) | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `python-docx` (paras+tables+hdr/ftr+hyperlinks) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `docx2python` `.text` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `docx2txt.process` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| `mammoth` `extract_raw_text` | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `mammoth` `convert_to_html` | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **Apache Tika** (`tika-app.jar --text`) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |

**Findings:**

1. **DOCX text boxes are dropped by 4 of 7 paths**, including both `mammoth` modes and naive `python-docx`. Greenhouse's warning about "name and contact information in the header, footer, or **text box**" is empirically justified.
2. **Headers and footers are dropped by 3 of 7 paths.** This is *extractor-dependent*, not universal — which is exactly why the advice is sound: the candidate cannot know which path runs.
3. **Table cells are extracted by 6 of 7 paths.** Only naive `python-docx` `.paragraphs` misses them. **The strong "tables destroy your resume" claim is not supported for DOCX.**
4. **Hyperlink target URLs are dropped by 4 of 7 paths, including Tika.** Underexplored and practically important: if your LinkedIn/GitHub/portfolio URL exists only as a hyperlink behind anchor text like "LinkedIn," the URL itself may never be extracted. **Write URLs as visible literal text.** I have not seen this in any mainstream resume advice, and it is one of the more actionable findings here.
5. **Naive `python-docx` — the most common "just parse the DOCX" implementation — is the worst performer**, silently losing tables, headers, footers and text boxes.

Reproduce: `/tmp/test_docx.py` against `/tmp/resume_probe.docx`.

### 4.2 MEASURED: two-column PDFs interleave under default extraction

I generated a two-column PDF (left sidebar `SKILLS` / `L1_PYTHON`…, right column `EXPERIENCE` / `R1_SENIOR_ENGINEER`…) with columns sharing y-coordinates, then extracted with `pypdf` and Apache Tika/PDFBox.

**`pypdf.extract_text()` output:**

```
SKILLS
EXPERIENCE
L1_PYTHON
R1_SENIOR_ENGINEER
L2_SQL
R2_ACME_CORP
L3_AWS
R3_JAN2020_PRESENT
L4_DOCKER
R4_BUILT_PIPELINES
L5_KAFKA
R5_LED_TEAM
```

**Apache Tika/PDFBox produced the identical interleaving.**

> Columns kept as separate blocks (human reading order): **False**
> Columns INTERLEAVED (reading order destroyed): **True**

**Why this matters concretely.** The extracted stream reads `SKILLS EXPERIENCE L1_PYTHON R1_SENIOR_ENGINEER…`. A downstream section detector sees "SKILLS" immediately followed by "EXPERIENCE" and cannot bound either section. Skill tokens land inside work-history text, so *n*-gram or phrase matching produces false adjacencies: `KAFKA` sits next to `LED_TEAM`. A parser inferring "skills used in the most recent role" from proximity — which HireAbility ALEX explicitly does ("competencies and skills used in the last job") — will attribute skills to the wrong employer.

**Crucially, this is exactly the extraction path used by the ResumeBench paper** ("we utilize the pypdf package to extract text from the PDF files"). So the peer-reviewed layout-sensitivity result in §4.3 is measured on top of demonstrably column-interleaving extraction. The two findings corroborate each other.

**Caveat, stated plainly:** this measures *default library behaviour*, not commercial parsers. Textkernel (code 433) and Affinda explicitly implement column detection and reading-order repair. The correct conclusion is: **naive extraction destroys column reading order; commercial parsers invest specifically in preventing that.** Do not generalize this measurement to "ATSs mangle two-column resumes."

Reproduce: `/tmp/coltest.py`.

### 4.3 Peer-reviewed: layout is not cosmetic

**[FACT]** *ResumeBench* (EMNLP 2025 Main Conference), Ling, Zhang et al. ([ACL Anthology PDF](https://aclanthology.org/2025.emnlp-main.1626.pdf); [GitHub](https://github.com/ApplyU-ai/ResumeBench)) — 2,500 synthetic resumes, 50 templates, 30 career fields, 5 languages, evaluated across 24 LLMs.

Templates span three layout classes, defined in the paper:
- **Single-column** — "experiences and information are listed sequentially from top to bottom"
- **Double-column** — "One typically contains personal details like contact information and a summary, while the other presents professional experience"
- **Designed** — "A flexible template without a fixed structure, allowing experiences to be customized and positioned in different sections"

The key finding, in the authors' words:

> "vision-language models achieve higher parsing accuracy and, for successful parses, noticeably better performance in both structural (KM Ratio, TED) and semantic (ROUGE-L, BERTScore) metrics compared to their text-only counterparts. **This finding underscores that document layout is not merely a cosmetic element.** Even though we rely on text extraction in our main evaluation, **the arrangement of sections, headers, and nested blocks—which originates from the template designs—still affects how the extracted text is grouped and interpreted.** VLMs that directly process the visual layout appear to benefit from these visual cues."

Also: even strong models like GPT-4o "exhibit challenges in cross-lingual structural alignment"; code-specialized LLMs *underperform* generalists; and "JSON outputs enhance schema compliance but fail to address semantic ambiguities."

Their **Success Rate** metric — fraction of documents yielding valid parseable JSON — is precisely the "hard parse failure" concept a simulator needs, and it varies enormously across models (e.g. DeepSeek-R1-Distill-Qwen-1.5B at 0.7236/0.5824 vs GPT-4o at 0.9912/0.9816).

### 4.4 Failure modes assessed individually

| Failure mode | Verdict | Evidence |
|---|---|---|
| **Multi-column reading order** | **[FACT]** Real for naive extraction; repaired by commercial parsers | §4.2 measured; Textkernel 433; Affinda reading-order algorithms |
| **Header/footer text dropped** | **[FACT]** Extractor-dependent (3 of 7 drop) | §4.1 measured; Greenhouse; Textkernel 311/441 |
| **DOCX text boxes dropped** | **[FACT]** 4 of 7 paths drop | §4.1 measured; Greenhouse lists text boxes |
| **Tables flattened** | **[FACT] weak** — cells usually extracted; structure/pairing lost | §4.1 measured; Greenhouse lists tables |
| **Date format parsing failures** | **[FACT]** Vendor-coded | Textkernel 418 (vertical multi-line ranges), 419 (no dates), 224/225 (missing start/end), 233 |
| **Non-standard section headings** | **[FACT]** Vendor-coded | Textkernel 412, 413, 414, 415/416 (inferred), **417** (explicitly "nonstandard headers"), 325 |
| **Text embedded in images** | **[FACT]** Requires OCR or is lost | Textkernel OCR necessity + designer guidance; Greenhouse image uploads; Affinda 25-word rule |
| **PDF with no text layer** | **[FACT]** Hard failure without OCR | Textkernel: "Without OCR, such documents cannot be parsed"; Affinda <25 words triggers OCR |
| **Corrupted/duplicated text layer** | **[FACT]** Worse than no text layer — defeats OCR fallback | Affinda: "duplicated text, garbled output, or wildly incorrect values despite the document looking fine visually"; Textkernel on corrupt PDFs |
| **Hyperlink URLs lost** | **[FACT] measured** — 4 of 7 paths incl. Tika drop the target URL | §4.1 |
| **Letter-spaced text** | **[FACT]** Explicitly documented | Greenhouse: "the parser won't recognize the separate letters as a single word" |
| **Placeholder/fake-looking data skipped** | **[FACT]** Explicitly documented, widely unknown | Greenhouse "Fake resumes" |
| **Company names lacking Inc./LLC** | **[FACT]** Explicitly documented | Greenhouse |
| **Abbreviated job titles** | **[FACT]** Explicitly documented | Greenhouse: "Sr. Account Exec" |
| **Document too long / truncated** | **[FACT]** | Textkernel 408; OCR capped at 10 pages / 120s; Greenhouse 2.5MB; Ashby 16MB |
| **Too many jobs** | **[FACT]** | Textkernel 331 (>30 jobs) |
| **Academic CV overload** | **[FACT]** Only first work-history section parsed | Textkernel 417 |
| **Custom fonts / non-Unicode glyph mapping** | **[WEAK]** — mechanically real (bad `/ToUnicode` CMap → garbage or empty text), matches Affinda's "garbled output despite looking fine visually", but **no vendor names it explicitly.** Do not assert as vendor-documented | Inference + Affinda symptom description |
| **Ligatures (ﬁ/ﬂ)** | **[WEAK]** — plausible; a ligature glyph without proper Unicode mapping breaks `find`/`Firm`. **No vendor documentation found** | Inference |
| **Dropped whitespace / kerning-based word splitting** | **[WEAK]** — the inverse of Greenhouse's documented letter-spacing failure, and real in PDF extraction where spaces are positional rather than encoded. **Not vendor-documented** | Inference + Greenhouse letter-spacing analogue |
| **DOCX SmartArt** | **[WEAK]** — SmartArt stores text in a separate `diagramData` part not read by mainstream extractors. **I did not test this** and found no vendor doc. Worth measuring before asserting | Inference |

**Being explicit about the boundary:** ligatures, kerning-based word splitting, non-Unicode glyph mapping, and SmartArt were specifically asked about, and I could not substantiate any of them from vendor documentation. They are mechanically plausible and consistent with documented symptoms, but they are **inference**. SmartArt in particular is cheap to test empirically and should be measured rather than assumed.

---

## Section 5: How recruiters actually behave

### 5.1 The Ladders eye-tracking studies

**2012 study [FACT]** — full methodology, from the original report ([PDF, hosted by Boston University](https://www.bu.edu/com/files/2018/10/TheLadders-EyeTracking-StudyC2.pdf)):

- **Thirty professional recruiters, 10-week period**
- Three research questions, including whether recruiters process professionally-written vs self-written resumes differently, and explicitly to test prior **self-reported** data "suggesting that recruiters spend as much as 4 to 5 minutes per resume"
- Finding: "recruiters spend only **6 seconds** reviewing an individual resume"
- **Six data points** drove the decision: name; current company and title; previous company and title; current position start/end dates; previous position start/end dates; education
- "Beyond these six data points, recruiters did little more than scan for keywords to match the open position, which amounted to a very cursory 'pattern matching' activity. Because decisions were based mostly on the six pieces of data listed above, **an individual resume's detail and explanatory copy became filler and had little to no impact on the initial decision making**"

**2018 update [FACT]** ([PRNewswire](https://www.prnewswire.com/news-releases/ladders-updates-popular-recruiter-eye-tracking-study-with-new-key-insights-on-how-job-seekers-can-improve-their-resumes-300744217.html); [HR Dive](https://www.hrdive.com/news/eye-tracking-study-shows-recruiters-look-at-resumes-for-7-seconds/541582/)):

- **7.4 seconds**, up from 6 in 2012. Ladders attributes the rise partly to 2012 falling during the recession, when application volume was higher
- **Best-performing resumes:** simple layouts with clearly marked section and title headers in a clear font; layouts exploiting **F-pattern and E-pattern** reading; bold job titles with bulleted accomplishments
- **Worst-performing:** "Cluttered layouts characterized by long sentences, **multiple columns**, and very little white space"; "Text flow that did not draw the eye down the page, lacking section or job headers"; "A reliance on **keyword stuffing**"
- Recommendations: two-page limit for experienced seekers; "utilizing keywords **in context only**"

**Criticisms [WEAK but well-reasoned]:**

- **n=30.** A commenter on the original coverage: "n = 30 is a very small study… not statistically valid in the world of real science," and asked for the variance and distribution rather than a bare mean, noting the distribution is bounded at zero and therefore non-normal ([FlowingData, 2012](https://flowingdata.com/2012/04/11/how-recruiters-look-at-your-resume/))
- **The 2018 update never disclosed its methodology.** "the Ladders 2018 report does not specify the types of positions or lengths of resumes that recruiters were scanning. It also **doesn't state how many recruiters were in the study**, their experience, or how many times they repeated the two-stage study" ([Spectacle Talent Partners](https://spectacletalentpartners.com/is-the-6-second-resume-scan-a-myth/)). The commonly-repeated "30 recruiters over 10 weeks" for 2018 is a **carry-over from the 2012 methodology**, not a stated 2018 figure — a detail almost every citation gets wrong.
- **Face-validity problem:** "If it were true that recruiters will only review a resume for six seconds, would that mean they should be expected to review 10 resumes a minute? Perhaps 300 resumes in 30 minutes? I realize that this is part of the reason that an AI vendor would tout this metric." (same source)
- **Commercial interest.** Ladders is a job-search company selling to job seekers.
- **Mixed-population averaging.** The FlowingData commenter's point is sharp: including obviously-unqualified resumes drags the mean toward zero and "muddle[s] any attempt to evaluate the influence of good cartographic design."
- **Never peer-reviewed.**

**Honest formulation:** *the initial screening pass is very fast — single-digit seconds — and attention concentrates on a handful of identity/chronology/education anchors. The specific figures "6 seconds" and "7.4 seconds" come from small, non-peer-reviewed, commercially-motivated studies (n=30 in 2012; undisclosed n in 2018) and should be described as order-of-magnitude, not measurements. The robust finding is the **attention pattern**, not the number.*

The 2018 finding that **multiple columns and keyword stuffing hurt with human readers** is arguably more useful than the timing figure, and it points the same direction as the parsing evidence.

### 5.2 Applicant volume and funnel data

**[FACT]** HBS/Accenture: "By the early 2010s, the average job posting yielded almost **120 applicants**. By the end of the decade, jobs posted by corporations received an average of **250 applications**" ([HBS report](https://www.hbs.edu/managing-the-future-of-work/Documents/research/hiddenworkers09032021.pdf)).

**[WEAK]** Jobscan cites *The Times* for "an average of 250 applicants" per corporate posting, and CareerPlug's 2024 Recruiting Metrics report for wide industry variance: automotive ~212 applications per hire, hospitality/entertainment/recreation ~25 applicants per hire. Jobscan also reports 1,400+ applications for its own visual designer opening ([Jobscan](https://www.jobscan.co/blog/fortune-500-use-applicant-tracking-systems/)). Second-hand citations and an anecdote; the variance point is the durable takeaway.

**[FACT]** HBS: only **20%** of surveyed hidden workers ever transitioned from applicant to candidate; for the "missing from work" subgroup, **only 4% received full-time offers**.

**[FACT]** iCIMS' tiering thresholds imply real-world pool sizes spanning ≤10 to 101+ candidates per requisition — a useful independent sanity check that "250 applicants" is an upper-mid estimate, not typical.

**[FACT]** Recruiter attention is explicitly finite and vendors design around it: Textkernel advises integrators "it is a mistake to show a large number of skills or jobs… Most likely, the user only cares to see the most recent jobs and the top skills," and recommends limiting review to "the most recent three jobs, or all jobs in the last 5 years."

### 5.3 What recruiters look at first

**[FACT]** The 2012 Ladders six anchors (§5.1): name, current company/title, previous company/title, both date ranges, education.

**[FACT]** Consistent with vendor design: HiredScore "calculates **employment gaps and time in position**"; iCIMS' experience match uses "previously held job titles and other work history details (**e.g., length of employment**)"; SmartRecruiters' Winston Match scores "**title, seniority, trajectory**." Three independent vendors converge on **titles + tenure + trajectory** as primary signal.

**[WEAK]** Jobscan: 76.4% of surveyed recruiters "search and rank candidates by skills from the job description," then education, job title matches, licences/certifications, years of experience. Underlying survey n and frame not disclosed on the cited page.

---

## Section 6: LinkedIn Recruiter retrieval and ranking

LinkedIn has published more engineering detail than any ATS vendor. Note it is a **sourcing** product, not an ATS — different problem, and its architecture should not be transplanted onto ATS behaviour.

**[FACT]** ([AI Behind LinkedIn Recruiter Search and Recommendation Systems](https://www.linkedin.com/blog/engineering/recommendations/ai-behind-linkedin-recruiter-search-and-recommendation-systems))

**Search stack:** "LinkedIn has built a search stack on top of **Lucene** called **Galene**." Index has two field types:
- **Inverted field** — "a mapping from search terms to the list of entities (members) that contain them"
- **Forward field** — "a mapping from entities (members) to metadata about them"

**Two-layer ranking:**
- **L1** — "Scoops into the talent pool and scores/ranks candidates… candidate retrieval and ranking are done in a distributed fashion"
- **L2** — "Refines the short-listed talent to apply more dynamic features using external caches"

Flow: "The Galene broker system fans out the search query request to multiple search index partitions. Each partition retrieves the matched documents and applies the machine learning model… then the broker gathers the ranked candidates and returns them to the federator. The federator further ranks… using additional ranking features that are dynamic or referred to from the cache."

**The objective function is the most important detail [FACT]** — and it is *not* relevance:

> "the talent search domain requires **mutual interest** between the recruiter and the candidate… We define a new objective, **InMail Accept**, which occurs when a candidate received an InMail from a recruiter and replies with a positive response. We take the InMail accept as an indication of two-way interest."

Evaluated as **precision@k**. **LinkedIn optimizes for predicted two-way interest, not for who is best qualified.** A highly qualified but unresponsive candidate is, by design, ranked lower.

**Model evolution [FACT]:** linear → **GBDT** ("high single-digit percentage improvement over engagement metrics") → **pairwise learning-to-rank** GBDT ("low two-digit (in the tens) percentage improvement") → **GLMix** with tree interaction features for recruiter-level and contract-level personalization ("low single-digit statistically significant improvements"). Deep models showed "low single-digit improvements" offline; noted GBDT weaknesses with "sparse id features such as skill ids, company ids, and member ids."

**Query structure [FACT]:** "structured fields, such as canonical title(s), canonical skill(s), and company name, along with unstructured fields, such as free-text keywords," plus facets. Query expansion by related entities — "recommending titles like 'Data Scientist' and skills like 'Data Mining' to recruiters searching for title 'Machine Learning Engineer.'"

**A revealing negative result [FACT]:**

> "Our online experiments of a GBDT model with network embedding semantic similarity features have shown low single-digit improvements… **The ranking lift, however, was not statistically significant. The hypothesis is that, because the retrieval process is doing exact match based on title ids, the embedding-based similarity won't differentiate the retrieved results by much.** This motivated us to apply this to the retrieval stage."

**This is the single most valuable engineering lesson in the report.** Semantic similarity added nothing at ranking time because **exact-match retrieval had already constrained the candidate set**. Semantics only helped once moved into *retrieval*, via "a query expansion strategy that adds results with semantically similar titles, like 'Software Developer' for 'Software Engineer,' when the number of returned results from the original query is too small."

Implication: **retrieval, not ranking, determines who can possibly be seen.** Exactly matching the recruiter's vocabulary matters at the retrieval boundary, where no amount of downstream semantic cleverness can rescue you. This is the rigorous version of "keywords matter" — and it is a *findability* argument, not a scoring argument.

**Also [FACT]:** embeddings via **LINE** (Large-Scale Information Network Embeddings); in-session online personalization adapting to recruiter feedback mid-session; and learning which profile attributes (skill, title, industry, seniority) the recruiter is implicitly favouring — "implicitly learning a search query for the current intent of the recruiter."

**Corroborating academic sources [FACT]:**
- *Towards Deep and Representation Learning for Talent Search at LinkedIn* ([arXiv:1809.06473](https://doi.org/10.48550/arxiv.1809.06473)): "the system retrieves a candidate set of **a few thousand members from over 500 million** LinkedIn members, utilizing **hard filters** specified in the search query." Distinguishes **Explicit Features** (profile fields) from **Derived Features** (implied skills, embeddings).
- *An External Fairness Evaluation of LinkedIn Talent Search* (AAAI, [doi](https://doi.org/10.1609/aaai.v40i45.41161)): confirms two-stage architecture; "Galene generates an initial list of candidates based on a feature-level matching utilizing candidate profile aspects such as job titles, skills, employment history."
- [Did you mean "Galene"?](https://engineering.linkedin.com/search/did-you-mean-galene): "we retain Lucene as the indexing layer… all other functionality is outside Lucene."

**Note the dates:** the main engineering blog and arXiv paper are 2018–2019. LinkedIn's stack has certainly evolved. Cite as published architecture, not current state.

---

## Section 7: Open datasets and benchmarks

| Resource | Scale | Nature | Licence / access | Assessment |
|---|---|---|---|---|
| **ResumeBench** ([GitHub](https://github.com/ApplyU-ai/ResumeBench), [EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1626.pdf)) | 2,500 synthetic; 50 templates; 30 fields; 5 languages (en/zh/es/fr/de) | Synthetic via human-in-the-loop; PDF → JSON schema; also `ResumeBench-Real` and `ResumeBench-Mix` with real public samples | **CC BY-NC 4.0**, access by request to `zijian.ling@applyu.ai` | **Best available.** Peer-reviewed; privacy-compliant; layout-stratified (single/double-column/designed). **Non-commercial only** |
| **EraMatch CV Parsing Benchmark v3.0** ([Kaggle](https://www.kaggle.com/datasets/anasahmad25/cv-parsing-eramatch)) | 10,000 synthetic | LLM+template generated; **multimodal: PDF + image + aligned JSON**; layout annotations | Kaggle | Largest, and the only one with aligned PDF/image/JSON — well-suited to testing extraction and OCR paths. Synthetic; no peer review |
| **CareerCorpus** ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13080643/)) | 302 real resumes | 251 from a LiveCareer-scraped Kaggle set (5 categories) + 51 Research Assistant resumes; **dual independent annotation retained** | Published data paper | Small but **real** and **double-annotated** — good for inter-annotator agreement. HTML resumes were GPT-5-processed, introducing a preprocessing artifact |
| **Resume Corpus Dataset** ([GitHub](https://github.com/vrundag91/Resume-Corpus-Dataset)) | Not stated | **36 NER entity types** | Open, academic/research | Richest entity taxonomy. Low activity (8 stars, last push Aug 2024); unstated size |
| **Kaggle resume dataset** (`snehaanbhawal/resume-dataset`) | 2,400+ | LiveCareer-scraped, 24 job categories, HTML + string | Kaggle | The de facto baseline, used by ResumeBench and CareerCorpus as comparison. **No parsing annotations** |
| **Jiechieu & Tsopze (2021)** | — | Real English, engineering-focused | Academic | Single-domain; used as ResumeBench's comparison point |

**Assessment for validating a parser:**

**The gap is stark, and the ResumeBench authors say so explicitly [FACT]:** "There are very few publicly available resume datasets designed for NLP tasks." Their comparison table shows prior datasets cover 1 and 6 career domains with **no parsing annotation**, versus ResumeBench's 30 domains with annotation.

**Practical recommendation:**
1. **EraMatch** for extraction-layer testing — the only public set with aligned PDF + image + ground-truth JSON, so you can isolate text-extraction error from field-extraction error. Licence permits commercial use where ResumeBench does not.
2. **ResumeBench** for layout-stratified accuracy *if* your use is non-commercial. Its single/double-column/designed stratification is exactly the axis §4.2 shows matters.
3. **CareerCorpus** for a real-document sanity check — synthetic benchmarks systematically understate real-world messiness.
4. **Build your own probe corpus** for the failure modes in §4.4. No public dataset covers header/footer placement, DOCX text boxes, missing text layers, letter-spacing, or hyperlink-only URLs. The probes in §4.1–4.2 are the right shape and took minutes to construct.

**A caution on synthetic data [FACT]:** ResumeBench's own validation found that when GPT was asked to classify real vs synthetic, "ChatGPT is **100% confident in real samples** classification but **56% of our synthetic samples can pass** the judge." Nearly half their synthetic resumes were detectably synthetic. Synthetic benchmarks are necessary given privacy constraints, but they are not a substitute for real documents.

---

## Section 8: Implications for building an honest ATS simulator

### 8.1 Architecture the evidence actually supports

Model **four distinct stages**, because the evidence says failures are stage-specific and stage 1 dominates:

```
1. EXTRACTION   file bytes → plain text        ← Textkernel: "vast majority of problems"
2. STRUCTURING  text → sections → fields       ← Textkernel 412-417; Greenhouse formatting list
3. INDEXING     fields + text → search index   ← Lever/Ashby/Jobvite boolean; LinkedIn Galene
4. RANKING      (candidate, job) → score/rank  ← HiredScore A-D; Role Fit tiers; Match Score
```

**Do not collapse these into one "ATS score."** That is precisely the error the content-farm ecosystem makes, and it is what produces fake weightings like "Formatting 10%, Keyword Match 30%."

### 8.2 Mechanics a simulator can legitimately model

**Stage 1 — Extraction (strongest evidence; partly measured here):**
- Detect missing/thin text layer. **Affinda's <25-words → OCR rule is directly implementable** and citable.
- Detect and report **image-only PDFs**, flagging that OCR availability is vendor- and configuration-dependent (~5% of documents need it per Textkernel).
- Detect **text in headers/footers**, reporting honestly that 3 of 7 measured extractors drop it (§4.1).
- Detect **DOCX text boxes** — 4 of 7 measured paths drop them (§4.1).
- Detect **hyperlink-only URLs** — 4 of 7 paths, including Tika, lose the target (§4.1). Novel, actionable, measured.
- Detect **multi-column layout** and *show the interleaved extraction* (§4.2). Showing the mangled token stream is far more honest and more persuasive than asserting a score penalty.
- **File-size gates:** Greenhouse 2.5MB, Ashby 16MB — hard, documented, per-ATS.
- **Format support gates:** HiredScore accepts only DOC/DOCX/PDF/RTF/TXT — so `.odt`/`.pages` get **no grade at all**. Textkernel accepts 70+ formats. These differ by ATS and are citable.
- Detect **letter-spaced text** (Greenhouse-documented).

**Stage 2 — Structuring (strong vendor documentation):**
- **Implement Textkernel's ResumeQuality codes.** This is a published, severity-banded, vendor-authored rule set — the best available foundation, and it lets a simulator cite rather than invent. Report as *findings with severity*, mirroring Textkernel's own framing, never as a score.
- Section detection against conventional headings; flag missing work-history/education (413/414), inferred sections (415/416), header-less sections (325), and headers not on their own line (151).
- **Date parsing:** flag vertical multi-line ranges (418), missing job dates (419/224/225), ambiguous formats.
- **Contact extraction:** flag no email (211), no phone (212), neither (441), contact info not at top (311).
- **Greenhouse-documented specifics** (each directly citable): placeholder-looking names/companies, employer names lacking Inc./Co./Ltd./LLC, abbreviated job titles, graphics/photos/word art.
- **CV-overload:** >30 jobs (331), long-document truncation (408), academic-CV first-section-only behaviour (417).
- **Privacy findings:** DOB, passport, marital status, driving licence (121–124), for US/UK/AU/NZ.
- **Document Last Modified Date** as an explicit parameter — Textkernel calls it "100x more important than any other setting," and it changes computed tenure and recency.

**Stage 3 — Indexing / retrieval (this is where "keywords" belong):**
- Model **boolean retrieval**, per-ATS, using published operator sets. Ashby's four match modes (matches / contains / equals / **similar** stemming), prefix wildcards, and grouping are fully documented. Lever's chips (`Resume:`, `titles:`) are documented. Jobvite's implied-AND is documented.
- Model the **`Resume:`-scope distinction** in Lever, and that unfiltered Lever search also matches **notes and interview feedback** — while Ashby **cannot** search notes.
- Model **findability, not rejection**, as the core risk. This is the honest reframing that the LinkedIn negative result (§6) rigorously supports: exact-match retrieval bounds the candidate set before any semantic ranking can help.
- Model **skill normalization**: SmartRecruiters uses **ESCO — ~14,000 skills, ~3,000 occupations** (public, downloadable). This lets a simulator do genuine synonym normalization with a citable taxonomy instead of guessing.

**Stage 4 — Ranking (model per-ATS; the paradigms genuinely differ):**
- **Absolute grading (Workday/HiredScore):** A–D against job-description qualifications; no grade without a resume, an accepted format, or a job description.
- **Relative tiering (iCIMS/Role Fit):** tier count depends on pool size (1 / 3 / 5 at ≤10 / 11–100 / 101+); **no absolute score exists**; your tier moves as others apply. Also model the asymmetry: job edits re-score everyone, but **a candidate's new resume does not re-score their existing applications.**
- **Calibration-weighted (Greenhouse/Talent Matching):** 5 buckets from a recruiter's weighted skill list; "the match score is spread across the selected skills," 4–6 skills recommended; both exact and "similar" keyword matches count.
- **Ensemble (SmartRecruiters):** separate models for skills / work experience / education / title relevance, "ensembled into a single weighted score," weights per-job. Prediction target: **passing CV screen**, explicitly not being hired.
- **Per-criterion verdicts (Ashby):** Meets / Does not Meet / **unknown** (AI couldn't decide) / **skipped** (resume unreadable), with citations — plus the derived sortable percentage (§2.5).
- **Binary labelling (Lever/Talent Fit):** a label plus positives / clarifications / concerns; go-forward only; re-processes when the JD or resume changes.
- **Questionnaire scoring (Taleo/ACE):** Required / Asset / Weight over **candidate answers**, with a tunable threshold (`at least n%` or `n of 3 assets`). **Not resume-text scoring** — an important corrective.

**Automatic rejection — model only the documented forms:**
- **Taleo disqualification questions** → automatic disqualification
- **Jobvite knockout** → status change to Rejected, **no automatic email**, and **only the first knockout question evaluated if the workflow changes**; **no retroactive re-screening**
- **SmartRecruiters Auto-Rejection Rules** → up to 10 conditions per hiring step
- **File/format gates** → a `.pages` resume gets no HiredScore grade; a >2.5MB file fails Greenhouse parsing

**Model the benign failure path, which is counter-intuitive and well-documented:**
- Greenhouse: unparseable → **"Needs manual review"** → **guaranteed human review**
- Ashby: unreadable resume → criteria **"skipped"**, reviewer still decides
- Workday: unparseable → **no grade**, candidate still in the pipeline
- Greenhouse: total parse failure → resume still **attached to the candidate**

A simulator that says "your resume failed to parse, therefore you were rejected" is **contradicted by three vendors' documentation**. Sometimes an unparseable resume gets *more* human attention.

**Model candidate-side rights, which are real and shipping:**
- Greenhouse AI opt-out → manual review; configurable jurisdiction disclaimers (California ADMT cited)
- iCIMS `Role Fit Status – Unranked` for opted-out candidates
- Ashby automated-processing legal notice with `hide scores`
- Lever automatic AI Disclaimer Statement
- NYC Local Law 144 bias audits: SmartRecruiters ("As required by New York City Law 144"), iCIMS [WEAK], Workday impact-ratio testing

### 8.3 Claims to refuse — these would be dishonest

**Never assert:**

1. **"75% of resumes are rejected before a human sees them,"** or any percentage of ATS auto-rejection. Traced to a 2012 Preptel sales pitch; company defunct August 2013; no methodology ever published. Even inverted ("the 75% myth is false, actually it's X%") we have no X.

2. **A single numeric "ATS score."** No ATS exposes a universal score. Workday gives A–D letters. iCIMS gives **relative tiers and explicitly no absolute score** ("does not provide specific… candidate scores (i.e., candidate scored a 90/100)"). Greenhouse gives 5 named buckets. SmartRecruiters gives 5 stars. Ashby gives per-criterion verdicts. Presenting "your ATS score is 73/100" is fabrication.

3. **Invented scoring weights.** No vendor publishes dimension weights. SmartRecruiters says weights "reflect the relevance of each dimension for that specific job" — i.e. **per-job and undisclosed**. Any fixed table ("Keyword Match 30%") is fiction.

4. **Parser-to-ATS mappings without vendor confirmation.** I found no primary source for the widely-copied "iCIMS uses HireAbility ALEX." Most vendors don't disclose. And SuccessFactors demonstrably has *multiple* possible parsers depending on tenant.

5. **"Your resume was auto-rejected for missing keywords."** No documented major ATS does this. Greenhouse, SmartRecruiters, Lever, Ashby and Workday all state the opposite. The honest claim is **reduced retrieval probability and lower rank**.

6. **"Tables/columns will destroy your resume."** Textkernel *repairs* columns (433). 6 of 7 extractors I measured read DOCX table cells. Say "higher variance, and worse for human readers too."

7. **"PDFs can't be read."** Every major engine reads PDF. The true statements are narrower: PDF is flagged as a Major Issue by Textkernel (300); corrupt PDFs are the top bug source; image-only PDFs need OCR.

8. **"Headers/footers are always dropped."** Measured: 3 of 7 extractors drop them, 4 retain. State it as variance you can't control, which is a sufficient reason for the advice.

9. **HBS "Hidden Workers" as evidence about formatting or parsing.** It contains **nothing** about resume formatting, keywords-as-formatting, PDFs, or tables. It is about **employer-configured filters** — degree requirements, credentials, six-month employment gaps. Different mechanism entirely.

10. **"88% of qualified candidates are rejected by ATS."** The HBS 88% is what **employers *believe*** about their own processes. It is opinion data, not measurement.

11. **Mobley v. Workday as proof of discrimination.** The court granted **preliminary** collective certification and made **no finding** that Workday's AI discriminates. Misrepresenting a procedural ruling as a liability finding is both dishonest and legally reckless.

12. **"Recruiters spend exactly 6/7.4 seconds."** n=30 in 2012; **undisclosed n and undisclosed methodology in 2018**; never peer-reviewed; commercially motivated. Use "seconds, not minutes" and cite the attention *pattern*.

13. **"Ashby never ranks candidates."** Ashby's marketing says this; Ashby's documentation describes a sortable "AI job criteria met percentage." Report the tension rather than picking the flattering half.

14. **Precision from unaudited vendor marketing.** Affinda's "above 99%" and DaXtra's "up to 95%" have no published methodology or test set. Textkernel's ">95% for the most critical data points" is at least scoped — and note the scoping.

15. **"92% of recruiters confirm no auto-rejection."** n=25. Directionally consistent with vendor docs, but this figure is now circulating with exactly the false precision of the myth it debunks. And 2 of those 25 *did* auto-reject on thresholds.

16. **Undated claims.** This field moved fast: Greenhouse Talent Matching, Lever Talent Fit, SmartRecruiters Winston Match and Auto-Rejection Rules, and Workday's LLM Fit & Gap are all 2024–2026. "Greenhouse doesn't score resumes" was true and is now false. **Every ATS-behaviour claim needs a date stamp.**

### 8.4 The honest core narrative

Three sentences that are all defensible:

1. **Parsing is a real, mechanical risk — but it degrades and warns far more often than it rejects, and it sometimes routes you to guaranteed human review instead.**
2. **Retrieval is the real gatekeeper: if your document doesn't contain the terms a recruiter searches, in a form the index can match, you are not rejected — you are never retrieved.** (LinkedIn's own negative result is the rigorous version of this: exact-match retrieval bounds the set before semantics can help.)
3. **Automatic ranking is now near-universal and worth taking seriously; automatic content-based rejection is rare, bounded, and vendor-prohibited, while rule-based rejection from screening questions is real and expanding.**

That story is more useful than the myth *and* more accurate. It gives candidates things they can actually act on — text layer, contact placement, conventional headings, unambiguous dates, literal URLs, the recruiter's vocabulary — without pretending to a precision nobody has.

### 8.5 Recommended posture on uncertainty

- **Show, don't score.** For multi-column layouts, display the interleaved extraction (§4.2). Concrete, verifiable, self-evidently persuasive — and it makes no unfounded quantitative claim.
- **Report findings with severity, not a number.** Textkernel's four-band model is the right precedent, from the vendor with the best documentation.
- **Name the ATS and date the claim.** "Greenhouse (per its documentation, as of 2026) caps parsing at 2.5MB" beats "ATSs reject large files."
- **Distinguish measured / vendor-documented / inferred** in user-facing output, as this document does. If a simulator flags ligature risk, it should say that's mechanical inference rather than vendor-documented.
- **Heed Textkernel's own warning** about its quality codes: they indicate substandard aspects of the *resume*, and must "NEVER IN ANY SENSE WHATSOEVER" be read as parser failure. A simulator inherits that obligation — and should also inherit the bell-curve framing: most resumes are "Good to Pretty Good," not broken.
- **Test rather than assume.** SmartArt, ligatures, and kerning-based word splitting are all cheap to measure with the harness in §4.1. Measure them before claiming them.

---

## Appendix A: Primary sources

**Parsing vendors**
- Textkernel Parser Output / ResumeQuality codes — https://developer.textkernel.com/tx-platform/v9/resume-parser/overview/parser-output/
- Textkernel Getting Started (pipeline, OCR, problem documents) — https://developer.textkernel.com/tx-platform/v10/resume-parser/overview/getting-started/
- Textkernel Integration Steps — https://developer.textkernel.com/tx-platform/v10/resume-parser/overview/integration-steps/
- Textkernel Parse API — https://developer.textkernel.com/tx-platform/v10/resume-parser/api/
- Textkernel FAQ (>95% accuracy, LLM parser) — https://developer.textkernel.com/tx-platform/v10/faq/
- Textkernel Supported File Formats — https://developer.textkernel.com/TKPlatform/master/file-formats/
- Affinda OCR configuration (25-word rule) — https://docs.affinda.com/configuration/ocr
- Affinda IDP whitepaper — https://www.affinda.com/whitepapers/intelligent-document-processing-solutions
- HireAbility ALEX — https://www.hireability.com/products/
- RChilli Resume Parser — https://www.rchilli.com/solutions/resumeparser

**ATS documentation**
- Workday HiredScore Grades — https://doc.workday.com/hiredscore/en-us/workday-hiredscore/recruiter-productivity-/concept--hiredscore-grades.html
- Workday HiredScore full reference PDF — https://doc.workday.com/content/dam/fmdita-outputs/pdfs/hiredscore/en-us/Workday-HiredScore.pdf
- Workday Prospects and Candidates (parsed fields) — https://doc.workday.com/workday-education/en-us/course-manuals/recruiting-for-administrators/prospects-and-candidates.html
- Workday HiredScore Fetch — https://doc.workday.com/hiredscore/en-us/workday-hiredscore/hiredscore-fetch-/steps--using-hiredscore-fetch.html
- Workday Skills Cloud — https://blog.workday.com/en-us/foundation-workday-skills-cloud.html
- Workday responsible AI (archived) — https://web.archive.org/web/20250810074028/https:/www.workday.com/en-us/legal/responsible-ai-and-bias-mitigation.html
- Greenhouse Unsuccessful resume parse — https://support.greenhouse.io/hc/en-us/articles/200989175-Unsuccessful-resume-parse
- Greenhouse Talent Matching — https://support.greenhouse.io/hc/en-us/articles/41396009937307-Talent-Matching
- Greenhouse Talent Matching policy guide — https://support.greenhouse.io/hc/en-us/articles/44682413339675-Operational-readiness-guide-Talent-Matching-policy
- Lever Searching the Database — https://help.lever.co/s/article/Searching-the-Database-for-Candidates
- Lever Talent Fit — https://help.lever.co/s/article/Talent-Fit-in-Lever
- Ashby Candidate Search — https://docs.ashbyhq.com/candidate-search
- Ashby AI-Assisted Application Review — https://docs.ashbyhq.com/ai-assisted-application-review
- Ashby AI-Assisted Application Review (product update) — https://www.ashbyhq.com/product-updates/ai-assisted-application-review
- Ashby AI principles — https://www.ashbyhq.com/ai
- iCIMS AI Talent Explorer / Role Fit — https://community.icims.com/s/article/Understanding-iCIMS-Talent-Cloud-AI
- iCIMS candidate search — https://community.icims.com/articles/Knowledge/Searching-for-and-Adding-Candidates-in-iCIMS-Nurture
- Oracle Taleo Candidate Prescreening — https://docs.oracle.com/en/cloud/saas/taleo-enterprise/20d/otrec/candidate-prescreening.html
- Oracle Taleo Requisitions (ACE thresholds) — https://docs.oracle.com/en/cloud/saas/talent-acquisition/19c/otfru/requisitions.html
- Oracle Taleo Candidate Selection Workflow — https://docs.oracle.com/en/cloud/saas/taleo-enterprise/20a/otrcg/candidate-selection-workflow.html
- Oracle Taleo Recruiting Fundamentals — https://docs.oracle.com/en/cloud/saas/taleo-enterprise/21b/otrcg/recruiting-fundamentals.html
- SmartRecruiters AI whitepaper — https://ta.smartrecruiters.com/rs/664-NIC-529/images/SmartRecruiters-AI-Whitepaper.pdf?version=1
- SmartRecruiters AI whitepaper vol. 3 — https://ta.smartrecruiters.com/rs/664-NIC-529/images/SmartRecruiters%20-%20AI%20Whitepaper_Volume%203_july%2015.pdf?version=0
- SmartRecruiters Talent Matching — https://www.smartrecruiters.com/recruiting-software/talent-matching/
- SmartRecruiters July 2025 release (Auto Reject) — https://assets.smartrecruiters.com/resources/article/july-2025-product-release-highlights-talent-matching-powered-by-gen-ai/
- Jobvite Pre-screening Forms — https://help.jobvite.com/s/article/Pre-screening-Forms
- Jobvite Candidates Tab — https://help.jobvite.com/s/article/Candidates-Tab
- BambooHR candidate keyword search — https://www.bamboohr.com/product-updates/candidate-keyword-search-enhancements
- BambooHR API Create Job Opening — https://documentation.bamboohr.com/reference/create-job-opening

**Corporate / M&A**
- Bullhorn acquires Textkernel — https://www.bullhorn.com/blog/bullhorn-acquires-textkernel-to-accelerate-its-ai-strategy/
- Textkernel acquires Sovren — https://www.textkernel.com/learn-support/blog/textkernel-acquires-us-based-software-company-sovren-to-become-the-global-leader-in-ai-powered-recruitment-technology-2/
- Workday intent to acquire HiredScore — https://investor.workday.com/news-and-events/press-releases/news-details/2024/Workday-Announces-Intent-to-Acquire-HiredScore-02-26-2024/default.aspx
- Workday HiredScore GA — https://newsroom.workday.com/2024-08-01-Workday-Transforms-How-Companies-Hire-and-Manage-Talent-with-New-AI-Powered-HR-Solutions?asPDF=1
- SAP completes SmartRecruiters acquisition — https://news.sap.com/2025/09/sap-completes-smartrecruiters-acquisition/
- SAP to replace SuccessFactors Recruiting — https://www.cio.com/article/4068172/sap-sets-timeline-to-replace-successfactors-recruiting-module-with-smartrecruiters.html

**Research, litigation, standards**
- HBS/Accenture *Hidden Workers: Untapped Talent* — https://www.hbs.edu/managing-the-future-of-work/Documents/research/hiddenworkers09032021.pdf
- HBS Working Knowledge summary (methodology) — https://www.library.hbs.edu/working-knowledge/how-to-tap-the-talent-automated-hr-platforms-miss
- Mobley v. Workday, Dkt. 128 (16 May 2025) — https://www.courthousenews.com/wp-content/uploads/2025/05/ai-applicant-recommendation-system-class-certification.pdf
- Mobley v. Workday, HiredScore scope order — https://s3.documentcloud.org/documents/26037637/mobley-v-workday-inc.pdf
- Holland & Knight on Mobley — https://www.hklaw.com/en/insights/publications/2025/05/federal-court-allows-collective-action-lawsuit-over-alleged
- LinkedIn: AI Behind Recruiter Search — https://www.linkedin.com/blog/engineering/recommendations/ai-behind-linkedin-recruiter-search-and-recommendation-systems
- LinkedIn: Galene — https://engineering.linkedin.com/search/did-you-mean-galene
- Towards Deep and Representation Learning for Talent Search — https://doi.org/10.48550/arxiv.1809.06473
- External Fairness Evaluation of LinkedIn Talent Search — https://doi.org/10.1609/aaai.v40i45.41161
- ResumeBench (EMNLP 2025) — https://aclanthology.org/2025.emnlp-main.1626.pdf
- ResumeBench repo — https://github.com/ApplyU-ai/ResumeBench
- CareerCorpus — https://pmc.ncbi.nlm.nih.gov/articles/PMC13080643/
- EraMatch CV Parsing Benchmark — https://www.kaggle.com/datasets/anasahmad25/cv-parsing-eramatch
- Resume Corpus Dataset — https://github.com/vrundag91/Resume-Corpus-Dataset
- HR Open Standards — https://www.hropenstandards.org/standards
- HR Open Resumé/CV Project — https://learnworkecosystemlibrary.com/initiatives/the-hr-open-standards-resume-cv-project/
- LER schema crosswalk (LER-RS → TCP) — https://ler.me/embeds/ler-schema-crosswalk.html
- JSON Resume monorepo — https://github.com/jsonresume/jsonresume.org/

**Myth-tracing and recruiter behaviour**
- Christine Assaf via Ask a Manager — https://www.askamanager.org/2020/10/your-job-application-was-rejected-by-a-human-not-a-computer.html
- Christine Assaf, original (HRTact) — https://hrtact.com/2020/10/05/your-job-application-was-rejected-by-a-human-not-a-computer/
- HiringThing (Assaf interview) — https://blog.hiringthing.com/applicant-tracking-system-myths
- Job Search Guide (Forbes/CIO trail) — https://newsletter.jobsearch.guide/p/is-it-true-that-over-75-of-resumes
- Jobscan 2025 ATS Usage Report — https://www.jobscan.co/blog/fortune-500-use-applicant-tracking-systems/
- Ladders 2012 eye-tracking report (methodology, n=30) — https://www.bu.edu/com/files/2018/10/TheLadders-EyeTracking-StudyC2.pdf
- Ladders 2018 update — https://www.prnewswire.com/news-releases/ladders-updates-popular-recruiter-eye-tracking-study-with-new-key-insights-on-how-job-seekers-can-improve-their-resumes-300744217.html
- HR Dive on the 2018 study — https://www.hrdive.com/news/eye-tracking-study-shows-recruiters-look-at-resumes-for-7-seconds/541582/
- Spectacle Talent Partners critique — https://spectacletalentpartners.com/is-the-6-second-resume-scan-a-myth/
- FlowingData (n=30 critique) — https://flowingdata.com/2012/04/11/how-recruiters-look-at-your-resume/
- Enhancv 25-recruiter survey — https://enhancv-cms.herokuapp.com/blog/does-ats-reject-resumes/

## Appendix B: Reproducing the measurements

Both harnesses are self-contained.

**DOCX extraction comparison (§4.1)** — `/tmp/test_docx.py` against `/tmp/resume_probe.docx`. The probe embeds unique markers in a body paragraph, a table cell, the page header, the page footer, a hyperlink (anchor text and target URL separately), and a text box. Compares `python-docx` (naive and thorough), `docx2python`, `docx2txt`, and `mammoth` (raw text and HTML). Tika separately:

```bash
java -jar tika-app.jar --text resume_probe.docx
```

**Two-column PDF reading order (§4.2)** — `/tmp/coltest.py` generates a two-column PDF via reportlab with columns at matching y-coordinates, extracts with `pypdf`, and asserts whether column tokens form contiguous blocks. Tika comparison:

```bash
java -jar tika-app.jar --text twocol.pdf
```

**Worth adding:** DOCX SmartArt, WordArt, ligature-heavy PDFs (e.g. LaTeX output with `fi`/`fl`), a PDF with a deliberately corrupted `/ToUnicode` CMap, and a PDF exported with kerning-based rather than encoded spaces. Each is listed as **[WEAK]** in §4.4 precisely because it has not been measured.
