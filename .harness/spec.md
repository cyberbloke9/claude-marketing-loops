# Product Spec — Asset Renderer + Deterministic QA Gate

## 1. Original Request

> Build the Asset Renderer + Deterministic QA Gate for the TERREM marketing-loop system, inside the existing repo at `/Users/prithviputta/Downloads/terrem-marketing-loops`.
>
> **(1) Renderer** — turns a content asset folder (`content/<slug>/chart-spec.md` + `carousel.md` + `meta.md`) into actual rendered graphics: 1080×1350 carousel slide PNGs and a 1080×1920 vertical variant for the chart card, using the locked brand tokens in `brand/brand-kit.md` (colors: bg `#faf8f3`, ink `#1c1917`, muted `#57534e`, accent `#0f766e`, accent-deep `#0d3d38`, chart-up `#0d9488`, chart-down `#dc2626`, border `#e0dbd3`; type: Inter, Major Third 1.25 scale, headline 48–72px, body ≥24px; charts: Tufte-clean, zero-based y-axis, on-graphic source + as-of date, TERREM wordmark).
>
> **(2) QA validator** — measures rendered PNGs and the asset specs against `brand/qa-checklist.md`: WCAG contrast math on actual hex pairs (≥4.5:1 normal / ≥3:1 large), pixel type-size minimums, safe zones (feed: critical content within center ~1000×1270; vertical: clear of top 250px / bottom 440px), hook slide ≤10 words, source/date stamp presence, blacklisted-stats detection (brand-kit.md §8), and data-provenance checklist prompts. Outputs a machine-readable PASS/FAIL verdict per asset that the `/loop-qa` skill can consume.
>
> **(3) Wire both into the repo** — a render script runnable via CLI, validator runnable via CLI, documented in README, and demonstrated end-to-end on the existing `content/2026-07-03-tgrera-enforcement-wave/` asset (add a minimal chart card spec for it if needed — its facts are public TGRERA orders, provenance-safe).
>
> **Constraints:** no network dependencies at render time (fonts vendored or system), no modifications to any other repo, everything stays inside this repo, Python or Node — pick what renders text/charts deterministically best.
>
> **Verification standard:** real PNGs rendered and measured (pixel checks, contrast), validator attacked with violating fixtures (11-word hook slide, truncated y-axis, low-contrast pair, missing source stamp), and the TGRERA asset passing end-to-end.

## 2. Product Goal

A CLI toolchain, living entirely inside this repo, that (a) renders a content asset folder into deterministic brand-locked PNGs plus a machine-readable render manifest, and (b) mechanically validates those PNGs + specs against the brand QA checklist, emitting a per-asset PASS/FAIL verdict the `/loop-qa` skill consumes. No taste debates: every check is binary and reproducible.

## 3. Target User

- **Primary:** a content/marketing operator (or an agent running the `/loop-qa` skill) who has authored an asset folder under `content/<slug>/` and needs published graphics plus a defensible pass/fail gate before publish.
- **They already know:** the folder structure (`chart-spec.md`, `carousel.md`, `meta.md`, `script.md`), the brand kit rules, and how to run one shell command.
- **They should NOT need to know:** the rendering library internals, WCAG luminance formulas, or how font pixel sizes are measured. They run two commands and read a verdict.

## 4. Core User Stories

1. **Render** — As an operator, I run one command against `content/<slug>/` and get PNG files (carousel slides + chart card) plus a `manifest.json`, written under `content/<slug>/render/`.
2. **Validate** — As an operator, I run one command against `content/<slug>/` and get a machine-readable verdict (`qa-verdict.json`) plus a human-readable verdict block appended to `meta.md`, telling me PASS or FAIL and exactly which checks failed and which brand rule each violated.
3. **Trust the gate** — As a QA agent, I feed a violating asset (11-word hook, truncated axis, low-contrast pair, missing source stamp) and the validator FAILs it, naming the violation.
4. **Ship the reference asset** — As an operator, I run render + validate on `content/2026-07-03-tgrera-enforcement-wave/` and it PASSes end-to-end.
5. **Re-render deterministically** — As an operator, I render the same input twice and get pixel-identical PNGs.

## 5. Required Behaviors

Each behavior is atomic and testable.

### 5.1 Renderer
- **R1.** Reads `content/<slug>/carousel.md` and renders each declared slide as a `1080×1350` PNG (feed/carousel format).
- **R2.** Reads `content/<slug>/chart-spec.md` and renders one `1080×1920` vertical chart card PNG.
- **R3.** All colors come from the locked tokens in §9 (`brand-kit.md §3`). No color outside that token set may appear as a declared text/element color in the manifest.
- **R4.** Text uses the **Inter** family (see §10 precedence rule). Font files are vendored inside this repo; rendering performs zero network access.
- **R5.** Chart card renders a zero-based axis when it plots a numeric axis; if an axis break exists it is explicitly marked and the manifest records the disclosure.
- **R6.** Every chart card and the carousel's source slide print an on-graphic source + as-of date string and the `TERREM` wordmark (`--accent-deep #0d3d38`, bottom-right).
- **R7.** For every PNG, the renderer also writes a **`manifest.json`** entry (schema in §5.3) describing the canvas and every text/graphic element it drew: text content, role, font pixel size, fill color hex, background color hex behind it, and bounding box `[x, y, w, h]`.
- **R8.** Deterministic: rendering the same input folder twice yields **pixel-identical** PNGs (identical decoded-RGBA SHA-256). No embedded timestamps, no run-varying metadata, fixed font, fixed layout math.
- **R9.** Output location: `content/<slug>/render/<surface-id>.png` and `content/<slug>/render/manifest.json`. The renderer creates the `render/` directory; it writes nowhere else.

### 5.2 Validator
- **V1.** Reads `content/<slug>/render/manifest.json`, the actual PNG files, and the asset's `*.md` specs, plus `brand/brand-kit.md` and `brand/qa-checklist.md`.
- **V2. Canvas (pixel check):** opens each PNG and reads its real width×height from the image bytes; FAIL if it does not match the declared format (carousel `1080×1350`, chart card `1080×1920`) and the manifest's declared canvas.
- **V3. Ink-present (pixel check, anti-stub):** for each text element, opens the PNG and confirms the declared fill-color token pixels actually appear inside the element's bbox. A blank/near-blank PNG (no ink pixels where text is declared) FAILs. This closes the "correct manifest + empty PNG" loophole.
- **V4. Contrast (math on declared hex pair):** computes WCAG 2.x relative-luminance contrast ratio on each text element's declared `color` vs `bg` hex. FAIL if ratio < 4.5:1 for normal text, or < 3:1 for large text. "Large" = font_px ≥ 24 (normal weight) **or** font_px ≥ 18.5 with bold weight. (Contrast is computed on declared hex, not sampled anti-aliased pixels, because sampled edges are noisy; V3 already proves those pixels are really on the canvas.)
- **V5. Type-size minimums (pixel, from manifest font_px, cross-checked against bbox height):**
  - Carousel: headline role `font_px ≥ 48`; body role `font_px ≥ 24`.
  - Chart card / vertical: headline role `font_px ≥ 36`; body role `font_px ≥ 24`.
  - `source-stamp` and `wordmark` roles are **exempt** from the body minimum (intentionally small) but must still satisfy V4 contrast and V8 presence.
  - Cross-check: the rendered glyph bbox height must be consistent with the declared `font_px` (within a tolerance the sprint contract fixes, e.g. ±25%), so the manifest cannot lie about size.
- **V6. Safe zones (from manifest bboxes):**
  - Carousel `1080×1350`: every element with role in {headline, body, hook} must lie within the centered rect `x∈[40,1040], y∈[40,1310]` (center ~`1000×1270`).
  - Vertical `1080×1920`: every critical element (headline, body, hook) must lie within `y∈[250, 1480]` (clear of top 250px and bottom 440px). Source-stamp/wordmark are exempt.
- **V7. Hook word count (spec):** the slide-1 hook text (manifest role `hook`, cross-referenced to `carousel.md` slide 1) must be ≤10 words. An 11-word hook FAILs.
- **V8. Source/date stamp presence (manifest + spec):** at least one element with role `source-stamp` exists per chart card and per carousel source slide, and its text contains both a source attribution and an as-of/order date. Missing → FAIL.
- **V9. Blacklisted stats (spec, single-source):** the validator loads the blacklist phrases by parsing `brand/brand-kit.md §8` (not a hardcoded copy) and scans all asset copy (`carousel.md`, `script.md`, `chart-spec.md`, rendered text). Any match → FAIL, naming the phrase.
- **V10. Chart integrity (conditional):** axis checks apply **only** to a chart card whose manifest declares `has_axis: true`. For such a card: FAIL if `axis_min ≠ 0` and `break_disclosed = false`. A card with `has_axis: false` (e.g., a receipts/data card) skips axis checks but still requires source-stamp + wordmark.
- **V11. Data-provenance prompts (presence-based):** the validator checks `meta.md` for a structured provenance attestation block. If absent → FAIL. If present → PASS for the gate, and the human-review provenance prompts (from `qa-checklist.md §Data provenance`) are emitted as informational `needs_review` items in the JSON (they do not block).
- **V12. Verdict output:** writes `content/<slug>/render/qa-verdict.json` (schema in §5.4) AND appends the human-readable verdict block (from `qa-checklist.md §Verdict`) to the asset's `meta.md`. A single FAIL sets overall `PASS=false`.

### 5.3 `manifest.json` schema (normative, versioned — the renderer↔validator seam)

```json
{
  "schema_version": "1",
  "slug": "2026-07-03-tgrera-enforcement-wave",
  "surfaces": [
    {
      "id": "chart-card",
      "role": "chart-card",              // "carousel-slide" | "chart-card"
      "png": "chart-card.png",
      "canvas": { "w": 1080, "h": 1920 },
      "has_axis": false,                 // chart cards only
      "axis_min": null,                  // number when has_axis=true
      "zero_based": null,                // bool when has_axis=true
      "break_disclosed": false,          // bool when has_axis=true
      "elements": [
        {
          "text": "Telangana's regulator just hit three builders in nine days.",
          "role": "headline",            // headline|body|hook|source-stamp|wordmark|chart-label
          "font_px": 54,
          "weight": 700,                 // numeric font weight
          "color": "#1c1917",
          "bg": "#faf8f3",               // resolved background token directly behind the text
          "bbox": [40, 300, 1000, 220]   // [x, y, w, h] in canvas pixels
        }
      ]
    }
  ]
}
```

Rules: `slide-1` carousel surface must carry exactly one `hook`-role element. Every `color` and `bg` must be one of the §9 tokens. `bg` is the actual resolved fill behind the text (used for V4 contrast). Fields marked axis-only may be `null` when `has_axis=false`.

### 5.4 `qa-verdict.json` schema (normative — the validator→`/loop-qa` seam)

```json
{
  "schema_version": "1",
  "slug": "2026-07-03-tgrera-enforcement-wave",
  "verdict": "PASS",                     // "PASS" | "FAIL"
  "checked_on": "2026-07-04",
  "checked_by": "validator-cli",
  "checks": [
    { "id": "V4-contrast", "surface": "chart-card", "element_bbox": [40,300,1000,220],
      "status": "PASS", "detail": "ratio 13.1:1 ≥ 4.5:1", "rule": "brand-kit.md §3" }
  ],
  "failed_checks": [],                    // list of {id, surface, detail, rule}
  "needs_review": []                      // provenance prompts (informational)
}
```

## 6. States That Must Exist

- **Empty / missing input:** asset folder or required `*.md` missing → validator exits non-zero with a clear message; renderer errors and writes nothing partial.
- **No render yet:** validator run before renderer → clear "manifest/PNG not found; run render first" error, not a crash.
- **Success (PASS):** all checks pass → `qa-verdict.json verdict=PASS`, exit 0, verdict block appended to `meta.md`.
- **Failure (FAIL):** one or more checks fail → `verdict=FAIL`, exit non-zero, `failed_checks` populated with rule citations; nothing "fixed silently."
- **Invalid input:** malformed manifest / unparseable spec / color outside token set → explicit validation error naming the offending field.
- **Blank/stub PNG:** manifest present but PNG has no ink where text is declared → V3 FAIL.
- **Deterministic re-render:** second render produces identical bytes; a diff test can assert this.
- **Provenance missing:** no attestation block in `meta.md` → FAIL (V11).

## 7. Design Direction

- **Fidelity to locked tokens, not novelty.** Colors, type family, scale, and safe zones are already locked by `brand-kit.md` (TERREM v4 visual-preservation constraint). The renderer reproduces them exactly; it does not introduce new brand colors, gradients, textures under type, or decorative fonts.
- **Tufte-clean charts:** maximize data-ink — no gridline forests, no 3D, no bar gradients, no chartjunk. Direct labels over legends. One accent per asset applied to the single most important element.
- **Typography:** Inter (weights per manifest). Major Third 1.25 scale (16→20→25→31→39→49→61). Line height 1.4–1.6×, line length 45–90 chars where the renderer wraps.
- **Anti-patterns (must not appear):** all-lowercase overlay headlines, condensed/thin faces, photo/texture behind text, more than one accent color per surface, truncated axis without disclosure.
- **Tone of tooling output:** terse, mechanical, cite-the-rule. No praise, no hedging in verdicts.

## 8. Non-Goals

- No video/reel rendering, animation, or audio.
- No LinkedIn 1200×627 link image or PDF carousel in v1 (only 1080×1350 feed + 1080×1920 vertical).
- No IBM Plex Serif pull-quote accent rendering in v1.
- No auto-fixing of failing assets — the validator reports, it does not edit copy or re-layout.
- No content generation — the renderer does not write copy; it renders authored specs.
- No changes to any repo other than this one. No changes to the live TERREM product.
- No CI/scheduling integration beyond making both tools CLI-runnable and documenting them.

## 9. Technical Constraints

- **Location:** all new code lives inside this repo. Proposed home: `tools/marketing-render/` (render entrypoint, validator entrypoint, vendored `fonts/`, shared measurement library, fixtures). No writes outside this repo.
- **Language:** Python or Node — generator picks whichever renders deterministic text + charts best (e.g. Python Pillow + matplotlib, or a headless SVG→PNG path). The choice is the generator's; **determinism (R8) and no-network-at-render (R4) are hard requirements**, not the library.
- **Locked color tokens** (from `brand-kit.md §3`, source of truth):
  ```
  --bg #faf8f3 · --surface #ffffff · --ink #1c1917 · --ink-muted #57534e
  --accent #0f766e · --accent-deep #0d3d38 · --chart-up #0d9488
  --chart-down #dc2626 · --border #e0dbd3
  ```
- **Fonts vendored:** Inter font files committed under `tools/marketing-render/fonts/`. Inter is SIL OFL — redistributable (confirm license file is included). System fonts are acceptable only if the exact face is guaranteed present and deterministic; vendoring is preferred.
- **No network at render or validate time.** No downloads, no remote font/CSS fetch.
- **Verdict consumption:** `qa-verdict.json` is the stable contract the `/loop-qa` skill reads; the skill is updated (in-repo, minimal) to invoke the validator CLI and consume the JSON. The human verdict block continues to be appended to `meta.md`.
- **Provenance-safety:** the TGRERA reference asset uses only public news-reported regulator orders (already declared in its `meta.md`); no TERREM DB numbers.

## 10. Risks and Ambiguities

1. **[RESOLVED — normative] Font contradiction.** `brand-kit.md §2` says headings = **Inter 600–700**; `brand/qa-checklist.md` (Typography) says "Headings **IBM Plex Sans 600**"; the human request says type = **Inter**. If the validator enforced the checklist literally it would FAIL the TGRERA asset (which uses Inter) — breaking the required end-to-end PASS. **Precedence rule the validator MUST enforce: human request > `brand-kit.md §2` > `qa-checklist.md`. The heading/body face is Inter.** The stale "IBM Plex Sans" line in `qa-checklist.md` should be corrected to "Inter" as part of this work (in-repo edit, allowed). Do not implement an IBM Plex Sans check.
2. **TGRERA asset has no chart-spec / carousel.** It currently holds only `meta.md` + `script.md` (a reactive short). The request permits adding a "minimal chart card spec." **Assumption:** author `content/2026-07-03-tgrera-enforcement-wave/chart-spec.md` as a **receipts/data card** (`has_axis: false`) containing the three public orders (dates, builders, amounts/interest), the source attribution (NewsMeter · Siasat · Deccan Chronicle · orders dated 2026-06-22/27/30), and the TERREM wordmark. No plotted numeric axis. Facts come only from the existing `script.md` / `signals` (public). The end-to-end demo validates the rendered chart card; a full carousel for TGRERA is optional/out-of-scope unless trivial.
3. **"Truncated y-axis" detection.** Implemented via manifest flags (`has_axis`, `axis_min`, `zero_based`, `break_disclosed`), not pixel baseline analysis. Default-safe: `axis_min ≠ 0 && !break_disclosed → FAIL`.
4. **Glyph-size cross-check tolerance.** Exact tolerance for V5 bbox-vs-`font_px` consistency is a sprint-contract detail (suggested ±25%); pick a value that passes correctly-rendered Inter and fails a 2× lie.
5. **Provenance is presence-based, not semantic.** V11 checks for a structured attestation block, not the truth of the claim; the deeper provenance checklist items are surfaced as `needs_review` informational prompts, matching the request's "checklist prompts" wording.
6. **Carousel source-slide vs chart-card source stamp.** Both must carry source+date; the validator requires the stamp on any surface declaring a chart card and on the carousel's designated source slide.

## 11. Suggested Sprint Breakdown

- **Sprint 001 — Measurement core (pure, unit-tested, no rendering).** WCAG relative-luminance + contrast-ratio functions; large-vs-normal threshold decision (V4); type-size minimum rules (V5); safe-zone containment math (V6); blacklist parser reading `brand-kit.md §8` (V9). Contract test: known hex pairs (e.g. `#1c1917`/`#faf8f3` ≈ 13:1 PASS; a deliberately low pair FAIL), known bboxes in/out of safe zones, blacklist hit/miss.
- **Sprint 002 — Carousel renderer + manifest.** Render `carousel.md` slides to `1080×1350` PNGs with vendored Inter and locked tokens; emit `manifest.json` (§5.3). Contract test: PNG dims = 1080×1350 (read from bytes), bg token dominates canvas, manifest validates against schema, and **pixel-identical re-render (R8)**.
- **Sprint 003 — Chart-card renderer + TGRERA spec.** Render `1080×1920` vertical chart card (zero-based axis when `has_axis`, source stamp, wordmark); author `content/2026-07-03-tgrera-enforcement-wave/chart-spec.md` as the `has_axis:false` receipts card (Risk 2). Contract test: card renders, dims 1080×1920, source-stamp + wordmark elements present in manifest, deterministic re-render.
- **Sprint 004 — Validator CLI + verdict.** Consume manifest + PNGs + specs; run V2–V12; emit `qa-verdict.json` (§5.4) + append verdict block to `meta.md`. Enforce the Inter precedence rule (Risk 1). Contract test: run against the rendered TGRERA card → structured PASS verdict, exit 0.
- **Sprint 005 — Adversarial fixtures + wiring + end-to-end.** Four violating fixtures each caught with the right rule cited: (a) 11-word hook slide → V7 FAIL; (b) truncated/undisclosed axis → V10 FAIL; (c) low-contrast text pair → V4 FAIL; (d) missing source stamp → V8 FAIL. Plus: blank-PNG stub → V3 FAIL. Wire render + validate CLIs into README with runnable commands; update `/loop-qa` skill to invoke the validator and consume `qa-verdict.json`. Acceptance: TGRERA asset renders + validates **PASS end-to-end**, and all five adversarial fixtures FAIL correctly.
