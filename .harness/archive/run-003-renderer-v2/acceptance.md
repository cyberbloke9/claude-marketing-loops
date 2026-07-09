VERDICT: PASS
SCORE: 4.7
BLOCKERS: 0
HIGH: 0

# Acceptance — EVALUATE_SYSTEM (Run 003, all sprints 001–006)

Cross-sprint, end-to-end regression pass over the WHOLE project (Renderer V2 Format
Library + QA Gate V2, layered on run-001 renderer + run-002 publish/analytics loops).
Scope: spec.md (R10–R19, V13–V19), all six sprint contracts, and the cumulative
behavior of runs 001/002/003 exercised together from a clean state. No cross-sprint
regression found. All evidence below is reproduced by the Evaluator, not taken from
Generator claims.

## Environment
- Python 3.9.6, Pillow 11.3.0, vendored Inter fonts. Zero network at render time.

## Cumulative behavior re-exercised (all PASS)

### 1. Full test suites — green together (regression budget honored)
- `tools/marketing-render/tests` → **Ran 266 tests, OK** (RC 0). Run-001's baseline of
  139 render tests was **consciously extended** (additive v2 tests), never weakened.
- `tools/marketing-loops/tests` → **Ran 254 tests, OK** (RC 0). Run-002 loop suite fully
  intact — no run-003 change regressed the publish/analytics layer.

### 2. Renderer acceptance runner — 25/25
`tools/marketing-render/acceptance.py` → `ACCEPTANCE: PASS (25/25)`, exit 0. Covers:
- TGRERA v2 end-to-end: 2 format-slide PNGs + carousel.pdf + schema-"2" manifest, no
  chart-card.png; decoded-RGBA PNGs pixel-identical and carousel.pdf byte-identical on
  re-render; validate exit 0, verdict PASS.
- **12 frozen v1 fixtures** each reach their existing verdict on the RIGHT check with the
  RIGHT rule (V2/V3/V4/V5-floor/V5-crosscheck/V6/V7/V8/V9/V10/V11 + fx-good-min exit 0).
- **9 v2 adversarial fixtures** each fire EXACTLY their named check (one-fixture-one-check):
  V13-dominant-ratio, V14-type-floor, V14-wordmark, V15-thumbnail, V16-so-what,
  V17-cover-pattern, V18-slide-count, V19-one-dataset + fx-v2-good exit 0.

### 3. Loops acceptance runner — 50/50
`tools/marketing-loops/acceptance.py` → `ACCEPTANCE: PASS (50/50)`, exit 0. Run-002
chain (enqueue → package → schedule → mark_posted → scorecard → idempotency) intact.

### 4. Reference asset TGRERA — independent fresh render + validate
- `render.py content/2026-07-03-tgrera-enforcement-wave` → format-01.png, format-02.png,
  carousel.pdf, manifest.json; RC 0.
- `validate.py … --checked-on 2026-07-08` → `VERDICT: PASS (98 checks, 0 failed)`, RC 0.
- Manifest: schema "2", 2 format-slides (RECEIPTS + CHECKLIST). Each content slide carries
  exactly one dominant (132px) at 4.4× body (30px) ≥ 3× (V13); body ≥26 / source-stamp 26
  ≥24 (V14); wordmark on every slide (V14); so-what + source-stamp present (V16/V8);
  ≤10 slides (V18); meta.md carries cover-pattern (pattern: BIG-NUMBER) + one_dataset (V17/V19).
  The 2-slide structure is NOT a shortfall: sprint_006/contract.md §1.1 normatively pins
  TGRERA as a Path-A **2-slide** carousel (F1 RECEIPTS cover with headline "3 builders. 9
  days.", dominant "SALES FROZEN" 132px, three order chips at body; F2 CHECKLIST dominant
  index "3" 132px, steps, INLINE so-what + INLINE source-stamp, wordmark). The render matches
  that accepted contract exactly. Path-A (all-dominant-bearing content slides, so-what/source
  inline rather than as dedicated utility slides) is a conscious contract choice that spends
  zero regression budget — it edits no frozen render/validate/measure code. Risk-6's 6-slide
  layout is spec-labeled [ASSUMPTION] with explicit "count/layout is the Generator's" latitude.
  Compliant with the accepted contract, not a regression.
- Determinism re-render (independent of the runner): decoded-RGBA PNG sig identical
  (05145bcf789e) AND carousel.pdf byte sig identical (e906c4192daf) across two runs.

### 5. Frozen v1 surfaces not retroactively broken (Risk-1 guarantee holds)
- All 7 format tags present in render.py: BIG-NUMBER, TIMELINE, RECEIPTS, VS-CONTRAST,
  LEADERBOARD, CHART, CHECKLIST.
- The hyd-premium-vs-budget v1 carousel (body 25px) validates to `FAIL (117 checks, 1
  failed)` firing ONLY V11-provenance — its **pre-existing** deliberate provenance kill
  (commit 512b4cc "QA kill: Ledger #1 synthetic-data provenance"). Critically it does
  **not** fail any raised-floor v2 check (V14) despite 25px body, proving the v2 hard
  rules are scoped to format-slide surfaces and do not reach v1 carousel-slide/chart-card
  surfaces. This is the unchanged existing verdict required by spec §10 Risk 1 — not a
  regression introduced by sprints 001–006.

## Cross-sprint regression check
No behavior that passed in an earlier sprint is broken by a later sprint. Run-001 render
V1 path, run-001 V2–V12 checks, run-002 loop chain, and run-003 V2 renderer/QA all pass
together from a clean state. TGRERA's conscious surface-type re-point (chart-card →
format carousel + PDF, spec Risk 2) is reflected in acceptance.py and reactive-single
coverage is retained via fx-good-min.

## Scoring
- Functionality: 5.0 — every promised behavior across 3 runs reproduced end-to-end.
- Evidence/process: 5.0 — real renders, byte/pixel determinism verified, adversarial
  fixtures fire on named checks, both acceptance runners + both test suites green.
- Craft: 4.7 — clean additive layering, frozen v1 constants untouched, one-fixture-one-check.
- Design: 4.5 — brand-locked tokens, one-dominant hierarchy enforced mechanically.
- Originality: 4.0 — infrastructure; deterministic PDF + measured 360px thumbnail gate are non-trivial.
- Systems-weighted total (Functionality 30% + Evidence 30% + Craft 20% + Design 10% +
  Originality 10%) = **4.7**. Bar met: no blockers, no highs, evidence ≥4, functionality ≥4.

No findings. VERDICT: PASS.
