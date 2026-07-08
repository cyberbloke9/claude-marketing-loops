VERDICT: PASS
SCORE: 4.7
BLOCKERS: 0
HIGH: 0

# Sprint 001 Findings — Measurement Core + Schema-v2 Seam

Mode: EVALUATE. Sprint scope: pure measurement functions in `measure.py` + widened
manifest-schema acceptance in `validate.py`. No rendering, no PNG/PDF, no V-check
wiring. Playwright N/A (CLI/pure-library sprint, no browser UI) — attacked with
`python3 -m unittest` + the §8 adversarial matrix, per contract §8.

## Verdict basis (behavior, independently reproduced — not claims)

Every check below was run by the Evaluator against the actually-imported
`measure`/`validate` modules, not read from the Generator's own tests.

### Test suites (contract §7 / §10.4)
- Render suite: `Ran 182 tests ... OK` (baseline 139 → +43 additive; count rose, none weakened). Reproduced.
- Loop suite: `Ran 254 tests ... OK` (unchanged). Reproduced.
- No-network import: `import measure, validate` → `import-ok`. Reproduced.

### §8 adversarial matrix — all 26 rows reproduced independently (PASS)
- Rows 1–2 (V13 ratio boundary): dominant 78/26 = 3.000 → pass; 77/26 ≈ 2.962 → fail. Exact float, no round-up.
- Row 3 (zero dominant, has body): fail, reason "no dominant element on content slide".
- Row 4 (two dominants): fail, reason "2 dominant elements; exactly one required".
- Rows 5–6 (utility slides {so-what,wordmark} / {source-stamp,wordmark}): exempt, pass.
- Row 7 (utility roles + a body): NOT exempt (content role present).
- Row 8 (no body element): `body_reference` = 26 fallback.
- Rows 9–12 (V14 floors): body 26 pass/25 fail; source-stamp 24 pass/23 fail/20 fail; headline 48 pass/47 fail; wordmark exempt pass.
- Row 13 (`format_slide_type_min("banana")`): `ValueError` naming role.
- Rows 14–15 (V15 comparator): headline 13.0 pass/12.99 fail; dominant 21.0 pass/20.99 fail.
- Row 16 (`thumbnail_ink_ok("body")`): `ValueError` (gates only headline/hook/dominant).
- Row 17 (`thumbnail_scale_band(39.84)`): 13.28.
- Rows 18–21 (cover-pattern parser): valid block parsed with inline `#`-comment stripped; CHART-FIRST valid; TIMELINE invalid; absent block → None, both predicates False on None.
- Rows 22–26 (schema widening in `_validate_manifest_schema`): v1 manifest accepted; v2 (schema_version "2", format-slide, format RECEIPTS, dominant+so-what+wordmark, top-level `pdf`) accepted; bogus `format` "BOGUS" → `PreconditionError` naming `surfaces[0] ('format-01') ... 'BOGUS'`; v1 missing-field and v1 non-token color still rejected naming the field.

### Isolation / regression guarantees (spec §9, §10 Risk 1; contract §1.2, §9) — verified
- `measure.py` diff: 274 insertions, 0 deletions → every existing symbol byte-unchanged (`_TYPE_MINIMUMS`, `type_min_ok`, `size_consistent`, contrast, safe-zone, blacklist intact).
- `validate.py` diff: only schema-local frozensets widened (`_ELEMENT_ROLES`, `_SURFACE_ROLES`) + new `_FORMAT_TAGS` + format-tag guard inside `_validate_manifest_schema`. No `run_checks`, `_check_v*`, `_FORMAT_BY_ROLE`, or `_SAFEZONE_ROLES` edits.
- `measure._SURFACE_ROLES` deliberately NOT widened (`{carousel-slide, chart-card}`) — check-routing untouched, per contract §1.2.
- Only 4 in-scope files touched. `render.py`, `acceptance.py`, all `fixtures/` untouched. Test edits additions-only.
- Widening invariant (rows 22/25/26): no previously-accepted manifest becomes rejected; no previously-rejected manifest becomes accepted.

## Findings

## Finding F-001: Latent uncaught ValueError if full validate CLI is run on a hand-crafted v2 asset (forward-carry, non-blocking)

Severity: Medium
Category: Process
Status: Noted (does NOT fail this sprint)

### Contract Clause
Contract §1.2 isolation guarantee + §9 non-goals ("No V-check wiring... format-slide surfaces are not routed through any `_check_v*` — Sprint 005"). Spec §6 end-state ("invalid input → exit 2, no crash") is a later-sprint target, not this sprint's.

### Reproduction Steps
1. Hand-craft a schema_version "2" manifest with a `format-slide` surface.
2. Run it through the full `validate.run` CLI (not `_validate_manifest_schema` alone).
3. Schema acceptance was widened but check-routing intentionally not, so flow reaches `type_min_ok(surface_role="format-slide")` → `ValueError` uncaught by `main` (catches only `PreconditionError`).

### Expected (end-state, post-Sprint-005)
Clean exit 2 with a rule-cited message, or a real V13–V19 verdict.

### Actual (this sprint)
Would raise an uncaught `ValueError` instead of the pre-sprint clean exit-2 rejection.

### Evidence
Generator trace [2026-07-06 12:28] disclosed this honestly. Evaluator verified UNREACHABLE via a corrected repo-wide search: no manifest.json carries schema_version "2" (both content assets — hyd + tgrera — are still "1"); "format-slide" appears only in source (measure.py/validate.py), in no manifest/fixture/asset; this sprint renders nothing. Not reachable by any §7 command or §8 matrix row.

### Required Fix
Sprint 005 must wire V13–V19 + format-slide check-routing (or add an early exit-2 guard) so a v2 asset run through the full CLI produces a clean verdict, not a traceback. Carry as an explicit Sprint-005 acceptance row.

### Pass Condition
A hand-crafted v2 format-slide manifest fed to the full `validate.run` CLI exits cleanly (0 with real verdict, or 2 with a cited message) — never an uncaught traceback.

Rationale for non-blocking: the contract consciously scoped V-check wiring out of Sprint 001, documented the alternative (routing v2 through v1 checks) as a worse crash, and the defect is unreachable by any artifact this sprint produces. Forward-carry item, not a shipped bug in the sprint's stated deliverable.

## Scoring

- Functionality: 5 — all 26 adversarial rows behave exactly per contract; exact float boundaries; correct error types/messages.
- Evidence/process: 5 — trace records baselines, files, new-test count, passing output, and honestly discloses provisional 13/21 thresholds + the latent-crash boundary; all independently reproduced.
- Craft: 5 — fully additive to `measure.py` (0 deletions), surgical widening in `validate.py`, docstrings cite spec, matches existing `_parse_provenance_block` grammar.
- Design (API/isolation discipline; no UI): 4.5 — clean seam, deliberate non-widening of check-routing to avoid an untested crash.
- Originality: 4 — faithful, precise spec implementation (not slop); N/A as a creative surface.

Weighted (20% each): (5 + 5 + 5 + 4.5 + 4) / 5 = 4.7 (header SCORE = 4.7, matching this arithmetic). Both functionality and evidence exceed the ≥4 bar. No blockers, no highs, evidence ≥4, functionality ≥4, weighted ≥4 → PASS.

## Trace review
`generator_trace.log` complete and honest: confirms 139/254 baseline BEFORE code, lists exact files/symbols, records 182/254 post-run, discloses two provisional risks and one sharpened latent-crash boundary. No skipped failures, no premature-completion language, no broad rewrite after a small finding. No prompt_patch warranted.
