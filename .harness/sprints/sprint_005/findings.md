VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Sprint 005 Findings — QA Gate V2 checks (V13–V19) + adversarial fixtures

Mode: EVALUATE · Sprint 005 · Renderer V2 Format Library + QA Gate V2
Evaluated on disk against sprint_005/contract.md §§1–10, spec §5.2 (V13–V19), §5.3 (schema seam), §5.4 (meta blocks), §6 (states), §9 (tokens/no-network), §10 Risks 1–6.
CLI/raster sprint — no DOM/UI. Playwright is not applicable (contract §0, §13). Attacked with `python3 -m unittest`, the `acceptance.py` runner, direct `validate.py` invocations, and — critically — **independent hand-crafted attacks** that do not reuse the Generator's pre-baked fixtures. All checks executed; evidence complete.

## Verdict

PASS. Every Definition-of-Done item (§10.1–§10.7) and every §6.4 adversarial matrix row (1–15) reproduced by direct observation against shipped code. 0 blockers, 0 high. One Low process note (F-001: v2 fixtures + `make_v2_fixtures.py` are git-untracked while the 12 v1 fixtures are tracked) — non-gating; fixtures are on disk and deterministically regenerable, which is what the file-only harness judges.

## Evidence (commands run from repo root)

### Suites + acceptance (DoD 4, 5)
- Render suite `Ran 266 tests … OK` (baseline 263 at Sprint-004 end; +3 net, none weakened).
- Loop suite `Ran 254 tests … OK` (unchanged — does not import validate/measure).
- `acceptance.py` → exit 0, **`ACCEPTANCE: PASS (23/23)`**. TGRERA chart-card pixel-identical on re-render (R8) + validate exit 0 UNCHANGED; all 12 v1 fixtures reach their existing verdicts with correct id+rule; 9 v2 rows met with exact-id + rule-substring match.

### One-fixture-one-check discipline (DoD 3; matrix rows 1–9) — SINGLETONS CONFIRMED
Each fixture's `failed_checks` is a singleton of exactly its target id (validate.py invoked per fixture, `qa-verdict.json` parsed):
```
good             PASS  []
dominant-small   FAIL  [V13-dominant-ratio]
body-24          FAIL  [V14-type-floor]
no-wordmark      FAIL  [V14-wordmark]
thumb-illegible  FAIL  [V15-thumbnail]
no-so-what       FAIL  [V16-so-what]
bad-cover        FAIL  [V17-cover-pattern]      (NOT also V19 — isolated)
no-dataset       FAIL  [V19-one-dataset]        (NOT also V17 — isolated)
11-slides        FAIL  [V18-slide-count]
```

### Independent attacks (NOT the Generator's fixtures) — checks have real teeth
- **V13:** copied `fx-v2-good`, injected a 2nd `dominant` element → `failed_checks == [V13-dominant-ratio]`. Fires on multiplicity, not just the baked ratio<3.
- **V16:** stripped all `so-what` elements from a good manifest → `[V16-so-what]` alone.
- **V17:** corrupted the `pattern:` value in a good `meta.md` → V17 fires (my crude regex co-tripped V19; the shipped `fx-v2-bad-cover` uses a clean valid-token wrong-value `pattern: TIMELINE` and isolates V17 alone, verified above — so isolation is a fixture-craft property, present and correct).
- **V15 is a genuine PIXEL measurement, not manifest math:** bumped `fx-v2-thumb-illegible` manifest `headline.font_px` 48→96 (PNG untouched). V15 STILL fires (plus V5-crosscheck now, since declared 96 ≠ rendered band). A manifest lie cannot buy past V15 — the check reads the downscaled raster. This is the property Risk 4 demanded.

### V15 margin probe (Risk A) — reproduced with validate's real `_crop_rows_ink`/`_median_band_height`
- `fx-v2-good`: headline decl 56 → 360px band **18** (floor 13, +5) PASS; dominant decl 100 → band **24** (floor 21, +3) PASS.
- `fx-v2-thumb-illegible`: headline decl 48 → band **10** (< 13) **FAIL**; dominant band 24 PASS.
- Invariant "positive clears, illegible fails" confirmed empirically; matches the Generator's trace probe. Margins are thin (headline +5, dominant +3) — the Generator disclosed this and flagged Sprint-006 revalidation against the real TGRERA render.

### Routing invariant / no-regression (DoD 1, 2; matrix rows 11, 14)
- `fx-v2-good` full roster: V2/V3/V4/V5-crosscheck/V6/V7/V8/V9/V10/V11 **plus** V13/V14-type-floor/V14-wordmark/V15/V16/V17/V18/V19. **V5-floor = `skipped`** on all format-slides (V14 owns the v2 floor); V14-type-floor present. All V13–V19 emitted.
- The `type_min_ok("format-slide", …)` ValueError landmine is correctly avoided: **zero tracebacks** across all 9 v2 fixtures (stderr scanned).
- v1 asset `fx-good-min` re-validate → exit 0, `checks[]` carries **zero** V13–V19 ids. Asset-scope gate holds.

### R14 render fail-loud twin (DoD 6; matrix row 10)
- 11-slide `formats.md` (correct `**F<n> BIG-NUMBER**` grammar) → `render.py` exit 1, cited `"the cap is 10 (R14, Instagram API limit)"`, **no `render/` dir written** (no partial write).

### Determinism (matrix row 15)
- Re-ran `make_v2_fixtures.py`; hashed all 28 v2 PNG+manifest files before/after → **zero drift** (byte-identical).

## Finding F-001: v2 fixtures + generator are git-untracked

Severity: Low
Category: Process
Status: Fail (non-blocking; verdict remains PASS)

### Contract Clause
Contract §2 / §6.1: v2 fixture dirs "live on disk (mirrors the 12 v1 fixture dirs that live on disk)."

### Reproduction Steps
1. `git ls-files tools/marketing-render/fixtures/` → lists the 12 v1 `fx-*` dirs + `make_fixtures.py`.
2. `git status --porcelain tools/marketing-render/fixtures/` → the 9 `fx-v2-*` dirs and `make_v2_fixtures.py` appear as `??` (untracked).

### Expected
For "mirrors the v1 fixture dirs" to be literal, the v2 fixtures + generator would be tracked alongside the v1 set.

### Actual
The 12 v1 fixtures are tracked; the 9 v2 fixtures and `make_v2_fixtures.py` are untracked. This is a pre-existing repo pattern (Sprint-001–004 also left measure.py/validate.py edits and tests/inputs uncommitted, disclosed in prior traces). It does **not** affect any behavior: `acceptance.py` reads dirs from disk (23/23 passed), the fixtures are byte-deterministically regenerable, and the file-only harness judges disk state, which is fully correct.

### Evidence
`git ls-files` vs `git status --porcelain` output above; determinism proof (28 files, zero drift).

### Required Fix
Commit the `fx-v2-*` dirs + `make_v2_fixtures.py` (and the prior-sprint uncommitted validate.py/measure.py/tests) so the tracked tree matches the on-disk tree before the Sprint-006 handoff. No code change required.

### Pass Condition
`git status --porcelain tools/marketing-render/` is clean (or the untracked set is a conscious, documented choice), with acceptance still 23/23.

## Trace review

`generator_trace.log` (Sprint 005 entry) records: baselines re-confirmed BEFORE code (render 263 / loop 254); exact files changed (validate.py wiring + `_FORMAT_BY_ROLE` addition; new `make_v2_fixtures.py` + 9 dirs; acceptance +9 rows; conscious `TestFormatSlideGuard`→`TestV2GateWiring` rewrite + batch-B guard-test re-point + acceptance table-count 12→21, all with the frozen assertions preserved); the empirical V15 measured-band probe for BOTH the positive control and the illegible fixture (Risk A); the singleton evidence; and a disclosed deviation from the contract's fixture table — the `fx-v2-dominant-small` values were changed from the contract's "body 30 / dominant 80" to "body 40 / dominant 100" because dominant-80 measured a 360px band of 19 (<21) and would co-fire V15, breaking the singleton. That is a correct, disclosed one-fixture-one-check fix (ratio 100/40 = 2.5 < 3 keeps it a clean V13-only trip), not a weakening. No skipped failures, no claim without artifact, no broad rewrite after a small finding. Trace is honest and complete.

## Scoring

Infrastructure/QA-gate sprint — weights: Functionality 35%, Evidence 35%, Craft 20%, Design/Originality 10% (no user-facing surface; mechanical gate, matching the Sprint-004 rationale).

- Functionality: 5 — all V13–V19 wired, correctly surface-role-scoped, one-fixture-one-check discipline holds under independent attack, V15 proven genuinely pixel-based, zero v1 regression, R14 fail-loud intact.
- Evidence/process: 5 — baseline-before-code, empirical V15 probe reproduced, singletons + independent injections reproduced, determinism (28 files zero drift), acceptance 23/23, honest trace with a disclosed contract-table deviation.
- Craft: 4.5 — clean additive routing that dodges the `type_min_ok` ValueError landmine (V5-floor skip → V14), no `measure.py` edit, justified test re-points; docked for the git-untracked fixtures (F-001, Low) and the thin V15 margins (+5/+3) flagged for Sprint-006 revalidation.
- Design/Originality: 4 — appropriate mechanical gate; not the axis this sprint exercises.
- Weighted total: 0.35·5 + 0.35·5 + 0.20·4.5 + 0.10·4 = 4.8.

Passing bar met: 0 blockers, 0 high, evidence 5 ≥ 4, functionality 5 ≥ 4, weighted 4.8 ≥ 4. F-001 is Low/process and does not gate PASS.
