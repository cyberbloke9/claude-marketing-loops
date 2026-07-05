VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Sprint 004 Findings — Validator CLI + verdict (V2–V12)

Mode: EVALUATE. Sprint 004 builds `tools/marketing-render/validate.py`, a headless
Python/Pillow CLI. There is no browser / no web UI, so no Playwright click-path
exists (contract §0 states this explicitly and correctly). The gate was attacked
directly from the shell with crafted-manifest fixtures + tiny PNGs and Python probes,
exactly as contract §7/§9/§10 prescribe. Every acceptance command was reproduced
independently by the Evaluator — no reliance on the Generator's self-reported output.

## What was verified (all reproduced from a clean invocation)

1. Full unit suite — `python3 -m unittest discover -s tools/marketing-render/tests`
   -> `Ran 117 tests … OK`, exit 0. 93 pre-existing (S001/002/003) + 24 new. No
   regression after the two source edits (`qa-checklist.md`, TGRERA `meta.md`).
2. TGRERA PASS end-to-end (this sprint's demo) —
   `validate.py content/2026-07-03-tgrera-enforcement-wave --checked-on 2026-07-04`
   -> exit 0, stdout `VERDICT: PASS (36 checks, 0 failed, 6 skipped)`. qa-verdict.json
   has verdict:"PASS", failed_checks:[], V7 + V10 recorded skipped (N/A for a
   has_axis:false chart-card with no hook — not silently absent, not a false FAIL),
   V2/V3/V4/V5/V8/V9/V11 all PASS.
3. qa-verdict.json schema (§5.4) — top-level keys exact; 0 malformed check records;
   every record status in {PASS,FAIL,skipped}; every FAIL carries a rule; needs_review
   holds 3 informational provenance prompts. Schema-faithful.
4. Idempotency — two extra runs -> meta.md holds exactly one qa-verdict:start block
   and one provenance:start block; qa-verdict.json byte-identical to the prior run
   (determinism with fixed --checked-on confirmed).
5. All 12 fixtures discriminate — each fx-* exits 1 failing exactly its intended check
   with the correct rule cited, and fx-good-min exits 0 PASS:
   - fx-blank-png -> V3-ink FAIL (0 ink px < 50) — anti-stub loophole closed.
   - fx-low-contrast -> V4-contrast FAIL (1.58:1 < 3.0:1).
   - fx-size-lie -> V5-crosscheck FAIL (declared 44px vs measured ~24.1px band 20px) —
     proves V5 reads real PNG pixels, not two manifest numbers.
   - fx-small-headline -> V5-floor FAIL (30 < 48).
   - fx-out-of-safezone -> V6 FAIL.
   - fx-11-word-hook -> V7 FAIL (11 words > 10).
   - fx-missing-source -> V8 FAIL.
   - fx-blacklist -> V9 FAIL naming '90% of recall in first 6 seconds'.
   - fx-truncated-axis -> V10 FAIL (axis_min=20, break not disclosed).
   - fx-no-provenance -> V11 FAIL.
   - fx-canvas-mismatch -> V2 FAIL (PNG 1080x1080 != 1080x1920).
   Isolation holds: no fixture trips a second check family (fx-blank-png fails V3 on
   all 4 declared elements by design).
6. Error states (exit 2, §6) — nonexistent folder -> exit 2 + named path; deleted
   manifest -> exit 2 `manifest/PNG not found; run render first`; non-token color
   (#123456) -> exit 2 naming surfaces[0].elements[0].color. Distinct from a content
   FAIL (exit 1). No tracebacks.
7. Purity / no-network (§4.14) — AST scan of validate.py imports
   {PIL, argparse, datetime, json, measure, pathlib, re, sys}; zero network modules.
8. Inter precedence (Risk 1) — qa-checklist.md line corrected to
   "Headings Inter 600; body Inter 400–500"; stale "IBM Plex Sans 600" heading line
   gone; no font-family raster check implemented (correctly declared out).
9. Acceptance #7 (contrast spot-check) — source-stamp #57534e on #faf8f3 @20px/400
   treated as normal text (threshold 4.5) and passes 7.19:1 — proving
   exempt-from-size-floor != exempt-from-contrast.
10. Scope boundary — protected files untouched (mtimes: measure.py 09:18, render.py
    10:47, test_render.py 10:11, test_chart_card.py 10:48 — all predate the S004 build
    at 11:xx). V9 blacklist parses brand-kit.md §8 single-source (5 phrases), not a
    hardcoded copy.

## Trace review

generator_trace.log records the calibration honestly and reproducibly: INK_TOL=60,
INK_MIN_PX=50 (smallest real element wordmark = 804px, 16x margin; blank crop = 0),
K_INTER=0.83 with per-element band/font_px ratios (0.72 all-caps wordmark -> 0.955
headline) all inside +/-25%, and a 2x/0.5x lie falling outside. No skipped failures,
no claims without artifacts, no broad rewrites. Disclosed residual risks (R-A K_INTER
drift on extreme glyph mixes, R-C regex date presence, meta.md excluded from V9 to
avoid the appended-block circular scan) are legitimate, spec-consistent, and correctly
scoped to design intent — not defects.

## Assessment against the Harsh Pass Standard

Infrastructure, not UI. Every check has a real, reproduced effect (fixtures prove the
gate is not a pass-everything stub). Error handling is explicit and recoverable with
named fields. The Generator's evidence reproduces the claim exactly. No stubs, no dead
checks, no placeholder verdicts. Applicability gating is recorded (skipped), never
silently dropped and never a false FAIL. Output tone matches §7 (terse, mechanical,
cite-the-rule).

## Scoring (weights shifted toward infra: Functionality 30%, Evidence 30%, Craft 20%, Design 10%, Originality 10%)

- Functionality: 5 — V2–V12 implemented, applicability-gated, correct PASS/FAIL/skip
  and exit codes; TGRERA PASS, every fixture FAILs its target.
- Evidence/process: 5 — 117 tests, 12 fixtures, idempotency, purity, determinism,
  error states all independently reproduced; calibration recorded.
- Craft: 5 — clean cite-the-rule output, idempotent meta writes, precondition errors
  name the offending path/field, unknown-field tolerance.
- Design (tooling tone): 4.5 — matches §7 terse mechanical spec.
- Originality: 4 — spec-faithful infrastructure; fidelity is the goal, not novelty.

Weighted total: 5(.30) + 5(.30) + 5(.20) + 4.5(.10) + 4(.10) = 4.85 -> 4.8.
Passing bar met: 0 blockers, 0 high findings, evidence >= 4, functionality >= 4,
weighted total >= 4.

## Verdict

PASS. No findings at Blocker/High/Medium/Low severity. The validator mechanically
discriminates PASS from FAIL, cites the rule for every check, passes the TGRERA card
end-to-end, and fails every crafted violation on the correct check. Sprint 005
(adversarial content asset folders, README wiring, /loop-qa skill update, cross-fixture
end-to-end) remains correctly out of scope per contract §"Explicitly NOT".

## Post-verdict hardening (independent on-distribution mutation, per advisor)

To close the circularity risk (fixtures + tests are generator-authored), the two
loophole-closing seams were re-tested by mutating the REAL TGRERA manifest against the
REAL rendered PNG (calibration is tuned on this render, so this is the on-distribution
attack the synthetic fixtures do not cover):
- V5-crosscheck: doubled headline font_px 44 -> 88 on the unchanged real PNG ->
  FAIL "declared 88px vs measured ~50.6px (band 42px) outside +/-25%", exit 1. The
  anti-lie seam measures real pixels on real data, not two manifest numbers.
- V3-ink: changed headline color #1c1917 -> #dc2626 (not the color rendered there) ->
  FAIL "0 ink px < 50", exit 1. The anti-stub seam catches a color lie on real data.
Both fired correctly. PASS is airtight.
