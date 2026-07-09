# Product Spec — Renderer V2 Format Library + QA Gate V2

## 1. Original Request

> Build Renderer V2 + QA Gate V2 for the TERREM marketing-loop system in the existing repo at `/Users/prithviputta/Downloads/terrem-marketing-loops`, per the finalized PIPELINE-V2.md (§4 format library and hard rules, §5 TGRERA redesign) and the evidence in RESEARCH.md Round 4. In scope:
>
> **(1) FORMAT LIBRARY** in the renderer (extend `tools/marketing-render/`, reusing its deterministic Pillow + vendored-Inter machinery and brand tokens): seven format templates — BIG NUMBER, TIMELINE, RECEIPTS, VS/CONTRAST, LEADERBOARD, CHART (existing, upgraded hierarchy), CHECKLIST — each with fixed visual grammar and a dominant element. Default asset shape is a 4:5 carousel (1080×1350) of up to 10 slides where each slide is one of these formats; single 1080×1920 card remains for reactive takes.
>
> **(2) NEW HARD RULES** enforced at render and/or QA time (all from PIPELINE-V2 §4): one dominant element ≥3× body size per surface; body/chart-label type floor raised to ≥26px and footnote/source floor ≥24px (1080-wide canvas); so-what line + source stamp + wordmark on-card always; one dataset per post; 360px feed-thumbnail gate (QA renders or simulates a 360px preview and checks the headline + dominant element clear minimum effective sizes); cover-slide pattern logged in meta.md (BIG-NUMBER vs CHART-FIRST) for A/B measurement.
>
> **(3) PDF VARIANT:** for every carousel, also emit a multi-page PDF of the slides (LinkedIn's organic carousel-equivalent — organic carousels are API-impossible, verified). Deterministic PDF bytes.
>
> **(4) TGRERA RE-RENDER** as the reference asset: rebuild `content/2026-07-03-tgrera-enforcement-wave/` as a carousel per PIPELINE-V2 §5 (RECEIPTS format cover "3 builders. 9 days.", order chips with amounts dominant, so-what slide with checkable action, source slide) + the PDF variant, passing the full V2 QA gate end-to-end.
>
> **(5) QA GATE V2:** extend `validate.py` (or add checks) for the new rules — dominant-element ratio, raised type floors, thumbnail gate, so-what presence, cover-pattern recorded. All checks mechanical, pixel/manifest-based, adversarially attackable. Existing V2–V12 checks and all run-1/run-2 frozen behavior must not regress (139 render tests + 254 loop tests must stay green, or be consciously extended — never silently weakened).
>
> **Constraints:** Python + Pillow + vendored fonts only, no network at render time, deterministic (decoded-RGBA SHA equality; PDF byte equality), everything in-repo, no changes to TERREM product repo. **Verification standard:** evaluator renders real PNGs/PDFs, measures pixels, attacks with violating fixtures (dominant element too small, body text at 24px, thumbnail-illegible slide, missing so-what line, 11-slide carousel), and confirms the TGRERA carousel + PDF pass end-to-end while the old fixtures still behave.

## 2. Product Goal

Extend the existing deterministic renderer + QA gate so a content operator (or agent) can turn an authored asset into a brand-locked **4:5 format-library carousel** (1080×1350 PNG slides, each one of seven named formats) plus a **byte-deterministic multi-page PDF**, and mechanically gate it against the PIPELINE-V2 §4 hard rules. Every new rule is binary, pixel/manifest-derived, and adversarially attackable. The existing single-card (1080×1920) path, all V1 checks, and all run-1/run-2 behavior stay frozen.

## 3. Target User

- **Primary:** a content/marketing operator (or an agent running `/loop-create` → `/loop-qa`) who has authored an asset folder under `content/<slug>/` and needs scroll-stopping carousel graphics + a PDF + a defensible pass/fail gate before publish.
- **They already know:** the `content/<slug>/` folder structure, the brand kit tokens, PIPELINE-V2 §4 format names, and how to run one shell command.
- **They should NOT need to know:** the rendering-library internals, WCAG luminance math, how effective mobile sizes are computed, or how PDF bytes are made deterministic. They run render + validate and read a verdict.

## 4. Core User Stories

1. **Render a format carousel** — As an operator, I run one command against `content/<slug>/` and get up to 10 PNG slides (each an authored format: BIG NUMBER / TIMELINE / RECEIPTS / VS-CONTRAST / LEADERBOARD / CHART / CHECKLIST), a `manifest.json`, and a multi-page `carousel.pdf`, all under `content/<slug>/render/`.
2. **Validate against V2 rules** — As an operator, I run one command and get `qa-verdict.json` + a verdict block in `meta.md` telling me PASS/FAIL and exactly which V2 rule each failed check violated (dominant ratio, raised floors, thumbnail, so-what, cover-pattern, ≤10 slides).
3. **Trust the V2 gate** — As a QA agent, I feed a violating asset (dominant element too small, body at 24px, thumbnail-illegible slide, missing so-what line, 11-slide carousel) and the validator FAILs it naming the exact V-check and rule.
4. **Ship the reference asset** — As an operator, I render + validate the TGRERA carousel (RECEIPTS cover, order chips, so-what, source) and it PASSes end-to-end, PNGs + PDF included.
5. **Re-render deterministically** — As an operator, I render the same input twice and get pixel-identical PNGs (decoded-RGBA SHA-256) and a byte-identical PDF.
6. **Keep the old path working** — As an operator, I still render a reactive single 1080×1920 card from `chart-spec.md`, and all existing V1 checks still pass unchanged.

## 5. Required Behaviors

Each behavior is atomic and testable. Numbering continues the run-001 renderer (R1–R9) and validator (V2–V12) conventions; all new work is **additive**.

### 5.1 Renderer — Format Library (new)

- **R10. Format-slide surface.** A new surface type renders at **1080×1350** and carries a `format` tag ∈ {`BIG-NUMBER`, `TIMELINE`, `RECEIPTS`, `VS-CONTRAST`, `LEADERBOARD`, `CHART`, `CHECKLIST`}. Each format has a fixed visual grammar (below) and reuses the vendored Inter faces + the nine locked brand tokens (§9). No new colors, gradients, textures, or fonts.
- **R11. One dominant element per content slide.** Every content format-slide declares **exactly one** element with role `dominant` — the number or figure doing the hook's work — at `font_px ≥ 3 × body_reference` (see V13 for `body_reference`). The renderer emits this element and marks it `dominant` in the manifest.
- **R12. Raised type floors on v2 surfaces.** On format-slide surfaces, `body` and `chart-label` roles render at **≥26px**, and `source-stamp`/footnote roles render at **≥24px** (previously 20px and exempt). Headline/hook floor unchanged (≥48px). This is a real renderer change: the v2 body/source style constants move up from the v1 25px/20px values. **V1 surfaces (`carousel-slide`, `chart-card`) keep their existing style constants unchanged** (see §10 Risk 1).
- **R13. On-card essentials, always.** Every format-slide carries the `TERREM` wordmark (`--accent-deep #0d3d38`, bottom-right). Every carousel asset carries at least one `so-what` element (a stand-alone utility line, typically with a checkable action + TERREM link) and at least one `source-stamp` element. The visual must stand alone without its caption.
- **R14. ≤10 slides.** A carousel asset renders **at most 10** format-slide surfaces (Instagram API cap, R4-B2). An 11th declared slide is a fail-loud render error (no partial write).
- **R15. Multi-page PDF variant.** For every carousel, the renderer also emits `content/<slug>/render/carousel.pdf` — the ordered format-slide PNGs as PDF pages, in slide order. This is the LinkedIn organic-carousel equivalent (R4-B4).
- **R16. PDF byte-determinism.** `carousel.pdf` is **byte-identical** across runs of the same input: no embedded creation/modification timestamps, a fixed producer string, no run-varying document ID. (Distinct from R8 PNG determinism — Pillow's default PDF save embeds a per-run date/ID that MUST be suppressed or fixed.)
- **R17. Cover-pattern record.** The asset's `meta.md` carries a delimited cover-pattern block recording the cover slide's pattern ∈ {`BIG-NUMBER`, `CHART-FIRST`} for Loop-5 A/B measurement (block format in §5.4). The renderer or authoring step writes it; the validator checks presence + valid value (V17).
- **R18. Determinism + no network (inherited).** Same input twice → pixel-identical PNGs (decoded-RGBA SHA-256) and byte-identical PDF. Fonts loaded only from the vendored `fonts/` dir. Zero network at render time.
- **R19. Output location.** All outputs land under `content/<slug>/render/`: `format-01.png … format-NN.png` (or equivalently named per surface `id`), `carousel.pdf`, and `manifest.json`. The renderer writes nowhere else and does partial-write-free atomic emission.

**Format grammars (express as required-roles + which-role-is-dominant + canvas; exact pixel coordinates are the Generator's to choose deterministically):**

| Format | Dominant element | Supporting roles | Notes |
|---|---|---|---|
| **BIG-NUMBER** | the single number (role `dominant`) | one-line context (`headline`/`body`) above, `so-what` below, `wordmark` | one striking stat; number at ≥3× body |
| **TIMELINE** | span/count headline or anchor figure (role `dominant`) | dated event chips (`body`), `wordmark` | enforcement waves, delay histories |
| **RECEIPTS** | the lead amount/consequence (role `dominant`) | 2–4 bordered chips: amount dominant per chip, builder/date at `body`; `wordmark` | multi-item evidence (TGRERA) |
| **VS-CONTRAST** | one of the two opposing numbers (role `dominant`) | the second number (`body`/`headline`), split labels, `wordmark` | ANAROCK vs PropEquity; premium vs budget |
| **LEADERBOARD** | top row's value (role `dominant`) | ranked rows (`body`), accent on one row, `wordmark` | city/locality rankings |
| **CHART** | headline figure or peak label (role `dominant`) | chart marks + `chart-label`s (≥26px), `source-stamp`, `wordmark` | v1 chart upgraded hierarchy; axis rules (V10) still apply if `has_axis` |
| **CHECKLIST** | big index numeral (role `dominant`) | numbered utility steps (`body`), `so-what`, `wordmark` | "check before you pay" utility posts |

### 5.2 QA Gate V2 — new checks (scoped to v2 format-slide surfaces)

All new checks apply **only** to surfaces of role `format-slide` (routed by **surface role**, not by `schema_version` — a v2 manifest may legitimately also contain a frozen `chart-card` reactive single). `carousel-slide` and `chart-card` surfaces skip the new checks and keep their frozen V2–V12 behavior (§10 Risk 1). New checks continue the V-numbering:

- **V13. Dominant-element ratio.** Each **content** format-slide must declare exactly one `dominant` element with `dominant.font_px ≥ 3 × body_reference`, where `body_reference =` the **max** `font_px` among that surface's `body`-role elements, falling back to the raised body floor **26** if the surface has no body element. Zero or ≥2 dominant elements → FAIL. Ratio < 3 → FAIL. **A utility slide is exempt** (no dominant required), defined as a slide whose elements are a subset of the utility roles `{so-what, source-stamp, wordmark}` — i.e. a standalone so-what slide, a source slide, or a combination, carries no content roles (`headline`/`hook`/`body`/`chart-label`/`dominant`) and is skipped by V13. Any slide carrying a content role is NOT a utility slide and MUST carry exactly one dominant. Rule cite: `PIPELINE-V2.md §4`.
- **V14. Raised type floors (v2) + wordmark presence.** On format-slides: `body` and `chart-label` `font_px ≥ 26`; `source-stamp`/footnote `font_px ≥ 24`; `headline`/`hook` `font_px ≥ 48`. `wordmark` exempt from the floor. Any element below its floor → FAIL. Also asserts each format-slide carries **exactly one** `wordmark` element (R13 "wordmark on-card always", making it adversarially attackable) — zero wordmarks → FAIL. Rule cite: `qa-checklist.md §Typography`.
- **V15. Thumbnail gate (360px, measured — independent teeth).** For each content format-slide, downscale the real PNG to **360px wide** with a **locked resample filter** (`Image.LANCZOS`, stated so the measurement is deterministic; the preview is a transient measurement, never a committed artifact, so it does not affect the PNG/PDF byte-equality guarantees) and measure the **rendered ink-band effective height** (reusing the existing V5-crosscheck `K_INTER` ink-band machinery) of the slide's `headline`/`hook` and its `dominant` element. FAIL if the measured headline ink is below the headline thumbnail floor **or** the measured dominant ink is below the dominant thumbnail floor (concrete px thresholds pinned by the Sprint-001 contract from the `K_INTER` calibration; suggested starting point: headline ≥ 13px, dominant ≥ 21px effective). **This is deliberately a pixel measurement, not manifest `font_px` math** — so a slide that passes V13 (ratio) and V14 (declared floors) but is *rendered* thumbnail-illegible (e.g. an honest-looking manifest whose glyphs shrink at 360px, or a thin/degraded render) FAILs V15 in isolation. A pure `font_px/3` inequality would be arithmetically dominated by V13/V14 and could never fire alone; the measured route is what makes the "thumbnail-illegible" adversarial fixture a distinct, isolable attack (one-fixture-one-check). Rule cite: `PIPELINE-V2.md §4`.
- **V16. So-what presence.** The carousel asset must carry at least one element with role `so-what` (across its format-slides). Absent → FAIL. Rule cite: `PIPELINE-V2.md §4`.
- **V17. Cover-pattern recorded.** `meta.md` must contain the delimited cover-pattern block (§5.4) with a value ∈ {`BIG-NUMBER`, `CHART-FIRST`}. Missing block or invalid value → FAIL. Rule cite: `PIPELINE-V2.md §4`.
- **V18. Slide-count cap.** A carousel asset (surfaces of role `format-slide`) must have **≤10** such surfaces. 11+ → FAIL. Rule cite: `PIPELINE-V2.md §4`.
- **V19. One dataset per post (presence attestation, NOT semantic).** `meta.md` must carry a `one_dataset:` attestation line (in the cover-pattern block or a sibling block, §5.4) naming the single dataset the post uses. This is a **presence** check (like V11 provenance), not a truth check — the semantic "is it really one dataset" judgment is a design-direction rule surfaced as `needs_review`, not a mechanical gate (§10 Risk 5). Missing attestation → FAIL. Rule cite: `PIPELINE-V2.md §4`.

Existing checks V2 (canvas), V4 (contrast), V3 (ink), V5 (floor + cross-check), V6 (safe zone), V7 (hook ≤10 words), V8 (source stamp), V9 (blacklist), V10 (axis), V11 (provenance), V12 (verdict) continue to run on all surfaces per their existing applicability, with V5's floor table extended for format-slide roles (V14 covers the raised numbers; V5 stays as the v1 floor for v1 surfaces).

### 5.3 `manifest.json` schema v2 (additive — the renderer↔validator seam)

The validator MUST accept both `schema_version` `"1"` (frozen old assets/fixtures) and `"2"` (new format carousels). v2 additions:

```json
{
  "schema_version": "2",
  "slug": "2026-07-03-tgrera-enforcement-wave",
  "surfaces": [
    {
      "id": "format-01",
      "role": "format-slide",            // NEW surface role; v1 roles unchanged
      "format": "RECEIPTS",              // NEW: one of the 7 format tags
      "png": "format-01.png",
      "canvas": { "w": 1080, "h": 1350 },
      "has_axis": false,
      "elements": [
        { "text": "₹14.95L", "role": "dominant", "font_px": 96, "weight": 700,
          "color": "#0f766e", "bg": "#faf8f3", "bbox": [90, 300, 600, 130] },
        { "text": "R Homes · Jun 22", "role": "body", "font_px": 28, "weight": 500,
          "color": "#57534e", "bg": "#faf8f3", "bbox": [90, 460, 700, 40] },
        { "text": "TERREM", "role": "wordmark", "font_px": 26, "weight": 700,
          "color": "#0d3d38", "bg": "#faf8f3", "bbox": [820, 1250, 170, 40] }
      ]
    }
  ],
  "pdf": "carousel.pdf"                   // NEW: present when a carousel PDF was emitted
}
```

New element roles: **`dominant`** (the ≥3× hook element), **`so-what`** (the stand-alone utility line). Existing roles (`headline`, `hook`, `body`, `source-stamp`, `wordmark`, `chart-label`) unchanged. Every `color`/`bg` must be one of the §9 tokens. The validator's schema check must **tolerate** the new top-level `pdf` key and per-surface `format` key without erroring on old manifests that lack them.

### 5.4 `meta.md` structured blocks (validator-consumed)

Model on the existing `<!-- provenance:start -->` block. Cover-pattern + one-dataset attestation:

```md
<!-- cover-pattern:start -->
pattern: BIG-NUMBER            # or CHART-FIRST  (V17)
one_dataset: TGRERA enforcement orders, Jun 2026   # (V19)
<!-- cover-pattern:end -->
```

The `qa-verdict.json` schema (§5.4 of run-001) is unchanged; new checks appear as additional entries in `checks`/`failed_checks` with their V13–V19 ids and rule cites.

## 6. States That Must Exist

- **Empty / missing input:** asset folder or required spec missing → renderer errors, writes nothing partial; validator exits 2 with a clear message.
- **No render yet:** validator before renderer → "manifest/PNG not found; run render first" (exit 2), no crash.
- **Success (PASS):** all applicable checks pass → `verdict=PASS`, exit 0, verdict block in `meta.md`, PNGs + `carousel.pdf` + `manifest.json` present.
- **V2-rule failures (each a distinct FAIL, right check cited):** dominant ratio < 3 (V13), zero/multiple dominants (V13), body at 24px (V14), thumbnail-illegible headline/dominant (V15), missing so-what (V16), missing/invalid cover-pattern (V17), 11-slide carousel (V18 at QA and R14 fail-loud at render), missing one-dataset attestation (V19).
- **Invalid input:** malformed manifest / unknown format tag / color outside token set → explicit validation error naming the offending field (exit 2).
- **Blank/stub PNG:** manifest present but PNG blank under declared text → V3 FAIL (inherited).
- **Deterministic re-render:** second render → pixel-identical PNGs AND byte-identical `carousel.pdf`.
- **Frozen old path:** a `chart-spec.md`-only reactive single (1080×1920) still renders + validates exactly as before; the hyd carousel and all 12 existing fixtures reach their existing verdicts unchanged.

## 7. Design Direction

- **Data becomes the picture.** The v2 renderer renders *formats*, not documents: one dominant element per surface at ≥3× body, information hierarchy matching the story (PIPELINE-V2 §1 root cause). No inert text-only cards.
- **Fidelity to locked tokens, not novelty.** Nine tokens (§9), Inter faces, Major-Third scale. One accent use per surface, applied to the single most important element. No new brand colors, gradients, textures under type, decorative faces, or chartjunk.
- **Tufte-clean CHART format:** maximize data-ink; direct labels over legends; zero-based axis unless a disclosed break (V10).
- **Anti-patterns (must not appear):** all-lowercase overlay headlines; condensed/thin faces; photo/texture behind text; >1 accent per surface; truncated axis without disclosure; body/source below the raised floors on a v2 surface; a cover with no dominant element.
- **Accessibility (mechanically gated):** WCAG contrast ≥4.5:1 normal / ≥3:1 large on every element (V4); raised legibility floors (V14) and 360px thumbnail floors (V15); safe zones (V6). Every asset text element carries an explicit `text`, `role`, and `bbox` in the manifest (labeled, measurable).
- **Tone of tooling output:** terse, mechanical, cite-the-rule. No praise, no hedging in verdicts.

## 8. Non-Goals

- No video/reel/animation/audio rendering.
- No publisher / direct posting to Instagram/LinkedIn/Facebook — that is PIPELINE-V2 §6, gated on the round-5 checklist (harness run 4). This run stops at PNG + PDF + gate.
- No public asset hosting / URL plumbing (the `image_url` architecture constraint, R4-B2) — deferred with the publisher.
- No auto-fixing of failing assets — the validator reports, it never edits copy or re-layouts.
- No content generation — the renderer renders authored specs; it does not write hooks or copy.
- No change to any other repo, or to the live TERREM product.
- No semantic "is this really one dataset / is the so-what genuinely useful" judgment — presence-checked only; quality stays in `needs_review`.
- No rewrite of the v1 renderer/validator/measure internals; v2 is additive alongside frozen v1 code paths.

## 9. Technical Constraints

- **Location:** all new code under `tools/marketing-render/` (extend `render.py`, `validate.py`, `measure.py`, `acceptance.py`; add fixtures). No writes outside this repo.
- **Language/stack:** Python + Pillow + vendored Inter only (matching existing code). No new third-party dependency. **Determinism (R18) and no-network-at-render (R18) are hard requirements.**
- **Locked color tokens** (from `brand-kit.md §3`, source of truth): `--bg #faf8f3 · --surface #ffffff · --ink #1c1917 · --ink-muted #57534e · --accent #0f766e · --accent-deep #0d3d38 · --chart-up #0d9488 · --chart-down #dc2626 · --border #e0dbd3`.
- **Fonts vendored** under `tools/marketing-render/fonts/` (Inter, SIL OFL — license file present). No system fonts.
- **PDF determinism:** suppress Pillow's per-run PDF metadata (creation/mod date, document ID); fix the producer string. Assert byte-equality in a test.
- **Regression budget (hard):** the existing **139 render tests + 254 loop tests must stay green**, or be **consciously extended** (new assertions/fixtures added, existing assertions never weakened or deleted). Any change to a frozen assertion must be justified in the sprint contract as a conscious extension, not a silent relaxation.
- **`measure.py` discipline:** **add** new pure functions (dominant-ratio, parameterized/raised floors, thumbnail effective-px math) — do **not** mutate existing `_TYPE_MINIMUMS`, `type_min_ok`, or other functions the v1 checks depend on. Route v2 floors through new code keyed on the format-slide surface role.
- **Provenance-safety:** the TGRERA reference asset uses only public news-reported regulator orders (already in its `meta.md`/`script.md`); no TERREM DB numbers.

## 10. Risks and Ambiguities

1. **[RESOLVED — normative] Raised floors must not retroactively fail frozen assets.** The existing `fx-good-min` positive control is a **chart-card** with `body font_px = 27` and `source-stamp = 20` (currently exempt); the hyd carousel body is **25px**. Raising floors globally (body ≥26, source ≥24 for all surfaces) would FAIL `fx-good-min` (source 20 < 24), the hyd carousel (body 25 < 26), and flip acceptance — a silent regression. **Resolution the request forces: the V2 hard rules (V13 dominant, V14 raised floors, V15 thumbnail, V16 so-what, V17 cover-pattern, V18 ≤10, V19 dataset) apply ONLY to `format-slide` surfaces (schema_version "2"). `carousel-slide` and `chart-card` surfaces keep their exact frozen V2–V12 behavior and v1 style constants.** TGRERA passes the raised floors because it is re-rendered from scratch as format-slides; the 12 existing fixtures pass because the new checks never reach them. The sprint MUST verify `fx-good-min` stays exit 0 and the hyd carousel unchanged.
2. **[RESOLVED — normative] TGRERA changes surface type; acceptance.py must be consciously updated.** `acceptance.py` hard-codes `chart-card.png`, its SHA, and TGRERA's exit-0 expectation. TGRERA moves from a 1080×1920 chart-card to a 1080×1350 format-slide carousel + PDF. **The acceptance runner's TGRERA path must be updated (new baseline: carousel PNGs pixel-identical on re-render + `carousel.pdf` byte-identical + validate exit 0).** This is a conscious extension, not a weakening. The old `chart-card` render/validate code path stays exercised via the frozen `fx-good-min` fixture, so reactive-single coverage is not lost.
3. **[RESOLVED — normative] Dominant-ratio denominator.** `body_reference = max(font_px of body-role elements on the surface)`, fallback **26** if no body element. Dominant must be exactly one element; ratio `dominant.font_px / body_reference ≥ 3`. This makes all 7 formats uniformly checkable and gives "dominant too small" a clean failure mode (V13).
4. **[RESOLVED — normative] Thumbnail gate must measure rendered pixels, not manifest `font_px`.** A pure `effective_px = font_px/3` inequality is arithmetically dominated by V13 (dominant ≥ 3×body ≥ 78 > any font_px thumbnail floor) and V14 (headline ≥ 48), so it could never be the failing check in isolation — breaking the repo's one-fixture-one-check discipline (`acceptance.py`: the RIGHT check with the RIGHT rule, not merely "some FAIL"). V15 therefore **downscales the real PNG to 360px with a locked `Image.LANCZOS` filter and measures rendered ink-band height** (reusing V5-crosscheck `K_INTER` machinery). The transient preview is never committed, so PNG/PDF byte-determinism is untouched; only the locked filter must be stated. Concrete thresholds are pinned as fixed integers by the Sprint-001 contract from the `K_INTER` calibration.
5. **[RESOLVED — normative] "One dataset per post" is presence-attested, not semantic.** V19 checks for a `one_dataset:` attestation line in `meta.md`; the semantic judgment is `needs_review` only. The request's own adversarial fixture list omits a two-dataset fixture — confirming this is not a mechanical pixel/manifest check.
6. **[ASSUMPTION] TGRERA carousel slide plan (PIPELINE-V2 §5) — every slide is V13-valid.** Each slide is either a content slide with exactly one `dominant ≥ 3×body_ref`, or a V13-exempt **utility slide** (elements ⊆ `{so-what, source-stamp, wordmark}`). Plan: (1) **cover** — RECEIPTS, dominant = "9 days" / "3 builders. 9 days." figure; (2–4) **order-chip** content slides, each dominant = the amount/consequence (₹14.95L +10.7% · SALES FROZEN · 45 DAYS), builder/date at body; (5) **so-what** — a utility slide `{so-what, wordmark}` ("check the RERA number before you pay — free → intel.terrem.in"), V13-exempt (satisfies V16); (6) **source** — a utility slide `{source-stamp, wordmark}` (NewsMeter · Siasat · Deccan Chronicle · orders 2026-06-22/27/30), V13-exempt (satisfies V8). ≤10 slides, **wordmark on every slide** (V14), cover-pattern + one_dataset recorded in `meta.md`. Exact count/layout is the Generator's within these required elements; every slide MUST be either dominant-bearing or utility-exempt — no content slide without a dominant. Every fact identical to v1; only the hierarchy changes.
7. **[ASSUMPTION] v2 input grammar.** The Generator chooses a deterministic, human-authorable input grammar for format-slides (extended `carousel.md` or a new `formats.md`), so long as it produces the §5.3 manifest. The **manifest is the normative seam**; the input grammar is the Generator's to design and document in README. TGRERA's existing `chart-spec.md` may remain for reference or be superseded — the carousel is the shipped asset.
8. **PDF page order + determinism.** Pages MUST follow slide order; Pillow PDF metadata MUST be stripped/fixed (R16). A byte-equality test guards this independently of PNG determinism.

## 11. Suggested Sprint Breakdown

Small slices, each contract-testable. `measure.py` changes are **additive** throughout.

- **Sprint 001 — Measurement + schema v2 core (pure, unit-tested, no rendering).** Add pure functions: dominant-ratio (`body_reference` + ≥3× rule), raised-floor table for format-slide roles (new, leaving `_TYPE_MINIMUMS` untouched), thumbnail effective-px math (`font_px/3` + 16/24 thresholds), cover-pattern/one-dataset block parser. Extend the validator's manifest schema to accept `schema_version "2"`, the `format-slide` surface role, `format` tag, `dominant`/`so-what` roles, and the top-level `pdf` key — while still accepting v1 manifests. Contract test: known ratios pass/fail at the 3× boundary; body 26 passes / 25 fails on v2, source 24 passes / 20 fails on v2; thumbnail 48/72 boundary; v1 manifest still validates.
- **Sprint 002 — Format templates batch A (BIG-NUMBER, RECEIPTS, CHECKLIST) + manifest v2.** Render these three format-slide types to 1080×1350 PNGs with one `dominant` element each, raised floors, wordmark; emit schema-v2 manifest. Contract test: dims 1080×1350, dominant present at ≥3× body, raised floors met, deterministic re-render (decoded-RGBA SHA).
- **Sprint 003 — Format templates batch B (TIMELINE, VS-CONTRAST, LEADERBOARD, CHART upgraded).** Same rigor; CHART reuses/upgrades v1 chart hierarchy and keeps V10 axis rules when `has_axis`. Contract test: each format renders, dominant + floors satisfied, deterministic.
- **Sprint 004 — Deterministic multi-page PDF emitter.** Emit `carousel.pdf` from ordered format-slide PNGs; suppress/fix PDF metadata for byte-determinism; add top-level `pdf` manifest key. Contract test: PDF page count = slide count, pages in order, **byte-identical** across two runs.
- **Sprint 005 — QA Gate V2 checks + adversarial fixtures.** Wire V13–V19 into `validate.py`, scoped to `format-slide` surfaces; emit them in `qa-verdict.json`. Add adversarial fixtures, each caught on the RIGHT check with the RIGHT rule: dominant-too-small → **V13**; body at 24px → **V14**; thumbnail-illegible slide → **V15**; missing so-what → **V16**; missing/invalid cover-pattern → **V17**; 11-slide carousel → **V18** (and R14 fail-loud at render); missing one-dataset attestation → **V19**; plus a v2 positive control → exit 0. Contract test: extend `acceptance.py`'s expectation table with these rows; confirm the 12 existing fixtures still reach their existing verdicts unchanged.
- **Sprint 006 — TGRERA carousel + PDF + full end-to-end, no regression.** Author the TGRERA v2 carousel (Risk 6 plan) with cover-pattern + one-dataset blocks in `meta.md`; render PNGs + `carousel.pdf`; validate full V2 gate → PASS end-to-end. Update `acceptance.py` TGRERA path (Risk 2) to the new baseline (carousel PNGs pixel-identical, PDF byte-identical, validate exit 0). Acceptance: TGRERA PASSes; every adversarial fixture FAILs on its named check; **139 render tests + 254 loop tests green (or consciously extended)**; README documents the v2 render + validate + PDF commands and the format library.
