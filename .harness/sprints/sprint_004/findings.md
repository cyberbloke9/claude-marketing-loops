VERDICT: PASS
SCORE: 4.7
BLOCKERS: 0
HIGH: 0

# Sprint 004 Findings — Deterministic Multi-Page PDF Emitter (carousel.pdf)

Mode: EVALUATE · Sprint 004 · Renderer V2 Format Library + QA Gate V2
Evaluated on disk against sprint_004/contract.md §§1-10, spec §5.1 (R15/R16/R18/R19), §5.3, §6, §9, §10 Risk 1/8.
CLI/raster sprint — no DOM/UI. Playwright is not applicable (contract §0, §5); attacked by rendering real assets across two independent processes, byte-comparing/parsing and pixel-extracting the emitted PDFs, and running both unittest suites plus the acceptance harness. All checks executed; evidence complete.

## Verdict

PASS. Every Definition-of-Done item (§10.1-§10.9) and every §8 adversarial matrix row (1-20) reproduced by direct observation against shipped code. 0 blockers, 0 high. One Medium craft/fidelity finding (F-001: PDF pages are lossily JPEG/DCTDecode-encoded, contradicting the contract's "same rendered pixels" prose) — does not gate PASS and does not break any mechanically-required behavior. One informational note (contract's Image.open verification snippet cannot run — Pillow has no PDF decoder).

## Evidence (commands run from repo root)

DoD 1 + rows 1-4, 10 — PDF emitted, page count == slide count, ORDER (observed), dims, manifest key:
- carousel.pdf written per v2 fixture, starts %PDF (PDF 1.4 per pdfinfo).
- Byte-parse of /Count, /Type /Page, /MediaBox all equal format-slide count: fmt-big-number 1, fmt-chart 1, fmt-receipts 1, fmt-multi 3. pdfinfo: Pages 3, Page size 1080 x 1350 pts.
- ORDER OBSERVED (not argued): pdfimages -png extracted 3 pages; mean-abs-diff of page i to format-01/02/03 gives a clean diagonal (page0->format-01 0.66 vs 13.2/7.1; page1->format-02 0.78 vs 13.2/11.3; page2->format-03 0.55 vs 7.1/11.3). Every page nearest its own slide -> order == format-01..NN confirmed by pixels, not just structural claim.
- Manifest top-level "pdf":"carousel.pdf" present on every v2 asset; schema_version "2".

DoD 2 + rows 5-9 — R16 byte-determinism (cross-process, on-disk):
- Two independent render.py process runs into /tmp/s4a vs /tmp/s4b (identical basename, distinct parents): cmp byte-identical for fmt-multi, fmt-chart, fmt-receipts, fmt-big-number.
- PDF bytes have no CreationDate, no ModDate, no /ID; fixed "created by Pillow" comment present.
- Producer "TERREM marketing-render" + Title "TERREM carousel" confirmed via pdfinfo (stored UTF-16, so ASCII grep misses them — not a defect; determinism proven by byte-identity). Title pinned path-independent (render.py:1296).
- test_cross_process_byte_identical uses a real subprocess.run of render.py — genuine cross-run proof, not a same-process BytesIO shortcut.

DoD 3 — multi-page proof:
- New tests/inputs/fmt-multi/formats.md = 3 format-slides -> 3-page PDF. Under tests/inputs/ (not fixtures/), no committed PNG/PDF (git ls-files clean of carousel.pdf/inputs render dirs).

DoD 4 + rows 11-13 — v1 freeze:
- hyd (carousel-slide) + tgrera (chart-card) re-render -> no carousel.pdf, schema "1", no pdf key.
- git status --porcelain content/ empty after re-render (PNG + manifest byte-identical).
- Acceptance harness: 14/14 expectations met — all 12 frozen fixtures reach existing verdicts, tgrera-determinism + tgrera-validate exit 0. No regression.

DoD 5 + row 15 — atomic fail-loud:
- 11-slide formats.md -> "cap is 10 (R14...)", exit 1, no render/ dir (no partial PDF).

DoD 6 + row 14 — validate on v2 asset carrying pdf key:
- validate.py /tmp/s4a/fmt-multi -> clean exit 2, cited "V13-V19 ... not yet wired (Sprint 005) ... [PIPELINE-V2.md §4]", no traceback. No validate.py edit in scope.

DoD 7 + row 17 — conscious re-point:
- Both test_no_pdf_key_this_sprint (batch-A :86, batch-B :467) now assert positive manifest["pdf"]=="carousel.pdf" on v2 AND re-prove preserved negative assertNotIn("pdf", v1) on schema-"1" hyd. Honest relocation, not weakening; no other assertion deleted.

DoD 8 + rows 18-20 — suites, dependency, no-network:
- Render suite Ran 263 ... OK (baseline 252, +11). Loop suite Ran 254 ... OK (unchanged).
- render.py imports argparse/json/math/re/sys/pathlib/PIL/measure only — no reportlab/fpdf/weasyprint. import render, validate, measure -> import-ok (no network).

Row 16 — mixed asset:
- carousel.md (8 carousel-slides) + formats.md (1 format-slide) -> 9 surfaces, pdf key present, PDF /Count = 1 (format-slide only; no carousel-slide page enters the PDF).

## Finding F-001: PDF pages are lossily JPEG (DCTDecode) encoded, not the exact PNG raster

Severity: Medium
Category: Craft
Status: Fail (non-blocking; verdict remains PASS)

### Contract Clause
Contract §1.1: "each page is the same 1080x1350 raster as its format-NN.png (built from the identical in-memory RGB image, so the page and the PNG are the same rendered pixels)." Contract §9 non-goal: "pages are the exact rendered 1080x1350 slide rasters, not re-scaled or re-flowed." Spec §5.1 R15: "the ordered format-slide PNGs as PDF pages."

### Reproduction Steps
1. python3 render.py /tmp/s4a/fmt-multi
2. pdfimages -list render/carousel.pdf  ->  enc column = "jpeg" (DCTDecode) for all 3 pages.
3. pdfimages -png render/carousel.pdf /tmp/pg ; compare each extracted page to its format-NN.png.

### Expected
If "the same rendered pixels" / "exact rendered raster" is taken literally, the PDF page pixels equal the PNG pixels (lossless, e.g. FlateDecode).

### Actual
PDF pages are JPEG (DCTDecode). Extracted-page vs PNG: max localized pixel diff 69-74, ~0.07-0.11% of pixels off by >30 (JPEG ringing concentrated at high-contrast text edges), mean ~0.6-0.8. Provenance is correct (same in-memory RGB image, same dims, no re-scale/re-flow) and the encoding is deterministic (R16 byte-identity holds), but the pages are not bit-exact copies of the PNGs.

### Evidence
pdfimages -list: "enc jpeg" x3. Pixel diff analysis: format-01 max74/mean0.66; format-02 max73/mean0.78; format-03 max69/mean0.55. Filter set parsed from PDF bytes = {DCTDecode}.

### Required Fix
Non-blocking for Sprint 004 (R15/R16 are met; Pillow's default PDF driver — which the contract explicitly builds around, incl. its metadata behavior — encodes RGB as DCTDecode). Before Sprint 006 ships the real public-facing TGRERA carousel PDF, consciously decide: either (a) encode PDF pages losslessly for brand-locked text-edge fidelity, or (b) correct the contract wording from "the same rendered pixels / exact raster" to "deterministically JPEG-encoded from the same source raster" so the claim matches behavior. Whichever is chosen, keep the byte-determinism guarantee and re-prove it.

### Pass Condition
Either the PDF pages decode bit-exact to their format-NN.png (lossless filter) with byte-determinism preserved, OR the contract/spec language is corrected to state the pages are deterministically lossy-JPEG-encoded and a pixel-fidelity threshold (e.g. max diff / SSIM floor) is stated and met.

## Informational note (NOT a finding)

Contract §7(c)/(d) + rows 2-4 snippets call Image.open(...carousel.pdf)/n_frames/seek. Pillow 11.3.0 has no PDF decoder ('PDF' in Image.OPEN is False; Image.open raises UnidentifiedImageError) — reproduced. The emitted PDF is valid (pdfinfo/pdfimages read it; stdlib byte-parse agrees). Generator disclosed this; shipped tests use the byte-parse route, so no shipped behavior affected. Verification-snippet defect in the contract, harmless to the deliverable; Planner should correct the snippet (use pdfinfo/pdfimages or byte-parse) in future PDF-touching contracts.

## Trace review

generator_trace.log (Sprint 004) records 252/254 baseline re-confirmed BEFORE code, files changed (render.py + test_render_v2.py + inputs/fmt-multi only), +11 tests -> 263, two-test conscious re-point justification, freeze evidence, cross-process byte-equality path, disclosed risks (env-pinned producer comment; path-independent Title; mixed-asset rule; Image.open contract defect). No skipped failures, no claim without artifact, no broad rewrite. The Generator did NOT disclose the DCTDecode/lossy-page property (F-001) — surfaced here by the Evaluator via pdfimages. Prior-sprint uncommitted state (measure.py/validate.py/test_measure.py/test_validate.py modified; inputs/ + test_render_v2.py untracked) disclosed and is Sprint 001-003 work, not touched by Sprint 004 — confirmed: this sprint's render.py diff is additive at the emission seam; v1/batch-A/B render/layout code byte-unchanged.

## Scoring

Infrastructure/raster sprint — weights: Functionality 35%, Evidence 35%, Craft 20%, Design+Originality 10% combined (no user-facing surface; PDF re-containers already-approved pixels).

- Functionality: 5 — every required behavior (emit, page count, order-by-pixels, byte-determinism, freeze, atomicity, manifest key, mixed-asset) reproduced.
- Evidence/process: 5 — baseline-before-code, cross-process on-disk proof, page order observed by pixel extraction, acceptance 14/14, honest disclosure of the contract Image.open defect + prior-sprint uncommitted state.
- Craft: 4 — clean additive deterministic seam; docked for the undisclosed lossy DCTDecode page encoding vs the contract's "same rendered pixels" claim (F-001, Medium, non-blocking).
- Design/Originality: 4 — appropriate, no slop; not the axis this sprint exercises.
- Weighted total: 0.35*5 + 0.35*5 + 0.20*4 + 0.10*4 = 4.7.

Passing bar met: 0 blockers, 0 high, evidence 5 >= 4, functionality 5 >= 4, weighted 4.7 >= 4. F-001 is Medium and does not gate PASS.
