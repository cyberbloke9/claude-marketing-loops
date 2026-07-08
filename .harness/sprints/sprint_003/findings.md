VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Sprint 003 Findings — Format Templates Batch B (TIMELINE, VS-CONTRAST, LEADERBOARD, CHART)

Mode: EVALUATE. Evaluated by rendering real PNGs, hashing decoded-RGBA bytes, feeding
violating `formats.md` fixtures, measuring the emitted manifest with Sprint-001 `measure`
functions, visually inspecting all four rendered slides, running both unittest suites, and
running the full `acceptance.py` gate. No browser/Playwright (CLI/raster sprint, per contract §0).

Environment: Python 3.9.6, Pillow 11.3.0, network not required (import-ok offline).

## Verdict rationale

Every row of the contract §7 command block and the §8 adversarial matrix reproduces as
specified. All four batch-B formats render at 1080×1350 with exactly one `dominant` (132px,
accent) at ratio >=3x body_reference, raised v2 floors, exactly one wordmark; CHART draws
genuine zero-based `--chart-up` bars with direct chart-labels (decorative primitives, not
manifest elements); VS-CONTRAST is asymmetric-by-construction (one 132 dominant + one 52
headline). The v1 path stays byte-frozen (hyd + tgrera re-render to schema "1", `git status
--porcelain content/` empty). No forbidden files were changed. `acceptance.py` PASSes 14/14.

## Evidence log (all reproduced by the Evaluator)

- Canvas + schema + tags (§7b): `canvas+schema+tags OK` — all four PNGs 1080x1350,
  schema_version "2", role format-slide, has_axis:false, tags {TIMELINE, VS-CONTRAST,
  LEADERBOARD, CHART} all present.
- Determinism (§7c, R18): `determinism OK` — decoded-RGBA PNG SHA-256 + manifest bytes
  identical across two same-basename renders (/tmp/s3a vs /tmp/s3b).
- V13/V14 via measure (§7d): `V13/V14 (measure) OK` — dominant_ratio_ok passes each surface
  (TIMELINE/VS/LEADER 132/30=4.40; CHART 132/26=5.08 no-body fallback), exactly one dominant +
  one wordmark each, every non-wordmark element clears format_slide_type_min.
- CHART decorative bars (§7e): roles = [chart-label x3, dominant, headline, source-stamp,
  wordmark] — no phantom "bar" manifest rows; >=2 chart-labels; all roles within allowed set.
- validate.py on v2 asset (§7f, F-001): clean exit 2, cited "V13-V19 ... Sprint 005" message,
  no traceback, nothing written.
- Regression freeze (§7g, rows 22-23): hyd schema "1", tgrera schema "1"; `git status
  --porcelain content/` empty (byte-frozen on re-render).
- Suites (§7h, row 28): render `Ran 252 tests ... OK` (baseline 219; +33, none weakened);
  loop `Ran 254 tests ... OK`.
- No-network import (§7i, row 29): `import-ok`.
- Acceptance gate: `ACCEPTANCE: PASS (14/14 expectations met)` — all 12 v1 fixtures reach
  their existing verdicts; tgrera determinism + validate PASS unchanged.

### Adversarial fail-loud matrix (rows 10-19, 25) — every attack caught on the right check, no partial write

| Attack | Result |
|---|---|
| CHART Bar no numeric run | ValueError "Bar line ... has no numeric value", exit 1, no partial write |
| CHART 1 bar | ValueError "at least 2 Bar chart-labels, got 1" |
| CHART missing Source | ValueError "at least one Source, got 0" |
| TIMELINE 1 event | ValueError "at least 2 Event chips, got 1" |
| LEADERBOARD 1 row | ValueError "at least 2 Row elements, got 1" |
| VS-CONTRAST 0 headlines | ValueError "exactly one headline ... got 0" |
| VS-CONTRAST 2 headlines | ValueError "exactly one headline ... got 2" |
| VS-CONTRAST 1 body label | ValueError "at least 2 Body side-labels, got 1" |
| CHART 2 dominants | ValueError "exactly one dominant, got 2" |
| Missing wordmark | ValueError "exactly one wordmark, got 0" |
| Bogus PIE-CHART | ValueError "unknown/unsupported format tag" (re-pointed test) |
| 11 slides (mixed A+B) | ValueError "cap is 10 (R14 ...)", no partial write |

- Tokens (row 24): every emitted color/bg is one of the nine §9 tokens (bad tokens: NONE).
- Conscious regression change (DoD #6): test_unknown_format_tag_fail_loud re-pointed to
  PIE-CHART; test_batch_b_tags_now_render added. Confirmed at test_render_v2.py:321-333. This is
  the only flipped assertion; the "unknown tag fails loud" guarantee is preserved.

### Visual inspection (rows 27, 2-4)

- CHART: genuine zero-based proportional bars (Gachibowli 18000 fills the track, Kokapet 14500
  ~80%, Narsingi 9200 ~50%), direct labels drawn on --bg above each bar (not on the bar), single
  accent = the Rs18k dominant, bars in --chart-up teal. Tufte-clean, no chartjunk.
- VS-CONTRAST: asymmetric split — Rs18k dominant (132, accent) vs Rs7k headline (52, ink),
  Premium/Budget body labels, 1px --border divider, wordmark. Reads as one dominant, not two.
- TIMELINE: "9 days" accent anchor dominant + three bordered event chips (RECEIPTS primitive) +
  headline eyebrow + wordmark. One accent.
- LEADERBOARD: "Gachibowli" accent dominant top value + muted ranked rows 2-4 + headline +
  wordmark. One accent = dominant, no second accent.

### Scope discipline

- Forbidden files untouched: acceptance.py, make_fixtures.py, and fixture PNGs/manifests are
  byte-clean. measure.py/validate.py show diffs vs HEAD, but these are cumulative Sprint-001/002
  changes (never committed by the harness), not Sprint-003 edits — the Sprint-003 build touched
  only render.py, test_render_v2.py, and new tests/inputs/ fixtures.

## Non-blocking note (informational, not a finding)

fixtures/fx-good-min/meta.md and .../qa-verdict.json show a dirty diff, but it is a
date-stamp-only change (checked_on: 2026-07-04 -> 2026-07-06). This is an inherent side-effect
of the acceptance runner: acceptance.py runs validate.py against each fixture, which stamps the
current date into the verdict block on every run. The verdict stays PASS with no failed checks,
all fixture PNGs/manifests are byte-frozen, and acceptance still reports 14/14. It is not
attributable to Sprint 003 and causes no behavioral regression, so it is not scored as a finding.
(Optional hygiene: `git checkout` the two stamped files, or have the acceptance runner write the
verdict stamp to a temp copy so committed fixtures never go dirty.)

## Scoring

Weights adjusted for a raster/infrastructure sprint (Functionality + Evidence emphasized).

- Functionality: 5 — all four formats render; every fail-loud path fires on the correct check
  with a descriptive message and no partial write; determinism holds; freeze holds.
- Design: 5 — brand-locked, one-accent discipline, genuine data-ink CHART, asymmetric VS.
- Craft: 5 — additive scope, byte-frozen v1/batch-A, atomic emission, clean error messages.
- Originality: 4 — real chart marks and asymmetric composition rather than inert text cards.
- Evidence/process: 5 — trace records baselines before code, files changed, +33 tests, the
  conscious re-point justification, and freeze evidence; all reproduced independently here.

Weighted total ~= 4.8/5. No blockers, no high findings, evidence >=4, functionality >=4.


## Additive-only verification (DoD #6 — verified by presence, not just count)

A rising test count (219->252) cannot detect a silent deletion, so confirmed directly:
all eight Sprint-002 batch-A test classes are intact and byte-preserved at the TOP of
test_render_v2.py (TestCanvasAndSchema, TestDominantAndFloors, TestFormatGrammar,
TestSchemaAcceptance, TestDeterminism, TestFailLoud, TestAntiTofu, TestV1Freeze; lines
69-405), including batch-A determinism (test_written_outputs_byte_identical_across_runs),
anti-tofu / missing-glyph, and v1-freeze (test_v1_freeze_still_holds). The seven new
TestBatchB* classes are appended below (lines 441+). Only the one flipped assertion
(test_unknown_format_tag_fail_loud -> PIE-CHART) changed. Additive-only confirmed.

## LEADERBOARD note (non-blocking, plain-reading holds)

LEADERBOARD's dominant is the winning entry NAME ("Gachibowli"), not a numeric ask value,
and ask amounts are not shown despite the "by ask" title. This is acceptable: the spec's
"top row's value" plainly accommodates the winning entry, visual grammar is explicitly the
Generator's to choose, and every mechanical gate (V13 ratio 4.40, raised floors, exactly one
dominant) passes. Not a finding.

VERDICT: PASS.
