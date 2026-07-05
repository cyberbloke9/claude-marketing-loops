VERDICT: PASS
SCORE: 4.4
BLOCKERS: 0
HIGH: 0

# Sprint 001 Findings — Measurement Core

Mode: EVALUATE. Sprint: 001 (pure measurement library; no rendering, no UI).
Scope note: this sprint is a stdlib-only Python library. There is intentionally no
browser/Playwright click path (contract §0). The library was attacked directly via
independent Python probes plus the contract's own §6 attack script and §5 verification
commands. All checks were reproduced from a clean invocation.

## Evidence summary (all reproduced by the Evaluator, not taken on claim)

| Check | Command | Result |
|---|---|---|
| Unit tests | `python3 -m unittest discover -s tools/marketing-render/tests -v` | Ran 44 tests, OK, exit 0 |
| Import purity | AST scan (contract §5.2) | `imports: ['re']`, exit 0 (stdlib-only) |
| Contract attack script | contract §6 verbatim | `OK — all measurement-core assertions passed`, exit 0 |
| Independent adversarial probes | Evaluator-authored (below) | `FAILS: NONE` |
| Determinism | two invocations, byte-compare outputs | identical |
| File scope | `find tools/marketing-render -type f` | exactly `measure.py` + `tests/test_measure.py`; no `__pycache__`, no `.pyc`; no writes to `brand/` or `content/` |

## Independent adversarial probes (NOT from the generator's own script)

Confirmed all of the following independently — each is a way the implementation could
have cheated the contract's script but didn't:

- WCAG extremes exact: `#000000`/`#ffffff` == 21.0; identical color == 1.0; `#ffffff`/`#faf8f3` < 1.2 (near-invisible pair correctly low).
- `is_large_text` full boundary lattice: `(24,100)=True`, `(18.4,700)=False`, `(18.5,700)=True`, `(18.5,400)=False`, `(23.9,400)=False`.
- `normalize_hex` rejects `#fff` 3-digit shorthand, `None`, `123` (int), empty string, `#1234567`, `12g4f6`, ` zzz`; accepts hash-less uppercase.
- `safe_zone_ok` raises on length-3 bbox, negative width, and unknown canvas (1200×627); failure `reason` names the exact violated edge (top/bottom/left/right).
- `size_consistent` band edges inclusive at exactly ±25% (`48→36` and `48→60` True; `48→35.9` and `48→61` False; `48→24` 2× lie False).
- `type_min_ok` raises on unknown surface and unknown element role; hook takes headline minimum; source-stamp/wordmark/chart-label exempt (pass at 12px).
- `parse_blacklist` proven single-source: a synthetic temp `## 8` section returns *its* phrases (`alpha/beta/gamma`), not the brand-kit constants; missing `## 8` raises `ValueError`; en-dash phrase `Wed 4pm / Fri 3–4pm` preserved verbatim.
- `scan_blacklist` dash/case/whitespace-insensitive substring match; clean copy returns `[]`.

## Spec conformance (Sprint 001 slice of §5.2)

- V4 contrast: WCAG 2.x relative-luminance formula implemented correctly; `passes` computed on raw ratio, `ratio` display-rounded to 2dp. `#1c1917`/`#faf8f3` ≈ 16.5:1 (the contract's normative WCAG target, correctly NOT the brand-kit's approximate "~13:1" annotation). Large/normal threshold (24px OR 18.5px+bold) correct.
- V5 type minimums + glyph-size band (±25%, Risk 4) correct as band math.
- V6 safe-zone geometry for both canvases correct, inclusive edges, edge-naming reasons.
- V9 blacklist parser is genuinely single-source (parses the real `brand/brand-kit.md §8`), returns the 5 phrases verbatim, and fails loud on a moved section.
- §5.3 token rule: exactly nine tokens, lowercase, `is_brand_token`/`token_name` correct.
- States (§6/§7): malformed hex, unknown role, unknown canvas, bad bbox, missing `## 8` all raise `ValueError` naming the offending value — no bare crash, no silent `[]`.

## Trace review

`generator_trace.log` records the commands run and their outputs, and honestly flags the
one deferred seam (`size_consistent` `measured_px` em-scale semantics land in Sprint 004 —
explicitly out of scope here and documented in the docstring). It also correctly notes the
contract §9 "four files" wording is a typo vs §2's two named files; only the two files exist,
which matches §2. No skipped failures, no claim without a reproducible artifact.

## Scoring

Weights (pure infrastructure library — Functionality + Evidence weighted up, Design/Originality
low-relevance for a math library and scored on fidelity/cleanliness rather than novelty):

- Functionality: 5 — every function meets its exact signature/behavior; adversarial edges hold.
- Evidence/process: 5 — all contract commands + independent probes reproduced from clean state; determinism and file-scope verified.
- Craft: 5 — clean, documented, single-responsibility functions; loud errors; no dead code.
- Design: 4 — faithful implementation of locked WCAG/token/safe-zone rules; correctly resolves the brand-kit "~13:1" annotation vs true WCAG value.
- Originality: 3 — N/A for a deterministic math core; not penalized as slop (no filler, no generic defaults).

Weighted total = 4.4 under the rubric's DEFAULT 20%/20%/20%/20%/20% weights
(Design 4, Originality 3, Craft 5, Functionality 5, Evidence 5 → (4+3+5+5+5)/5 = 4.4).
Under the infrastructure reweight (Functionality+Evidence up, Design/Originality down) it rises to ~4.6;
the header records the conservative default (4.4). Passing bar met either way: no blockers, no high findings, evidence ≥ 4,
functionality ≥ 4, weighted total ≥ 4.

## Non-blocking observations (Low — informational, no fix required this sprint)

- `size_consistent` is band-math only; the `measured_px` em-scale calibration is the
  Sprint 004 seam. Documented and out of scope. Watch in S004 that a truthfully-rendered
  Inter glyph lands inside ±25% (the contract already warns cap-height mapping would false-fail).
- `normalize_for_scan` does not strip leading/trailing whitespace (per contract wording);
  harmless for substring scans. No action.
- `test_passes_uses_raw_not_rounded` is a weak test — it only asserts `ratio == round(ratio,2)`
  (trivially true). The *code* is correct (`passes` uses `raw_ratio`, verified by reading measure.py);
  only the test under-exercises the claim. Suggest strengthening in a later sprint. No behavior defect.
- `normalize_hex` regex `^[0-9a-f]{6}$` accepts a trailing newline (Python `$` matches before final `\n`),
  so `'faf8f3\n'` would pass. Irrelevant to clean token inputs; no impact this sprint. Optional hardening.

No findings block this sprint. VERDICT: PASS.
