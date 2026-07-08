VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Summary

This contract closes the final sprint of the TERREM marketing-loops build by delivering a cross-gap acceptance runner and README rollout documentation. All required artifacts exist, the contract is comprehensive and testable, and no blocking deficiencies were found.

## Verification of Core Artifacts

**Frozen CLIs (Sprints 001–005):** Confirmed present under `tools/marketing-loops/`: `verify_utm.py`, `enqueue.py`, `package.py`, `mark_posted.py`, `scorecard.py`, `ingest.py`, `schedule.py`, `utm.py`, `gate.py`, `captions.py`, `channels.py`, `queue.py`, `assetmap.py`, `csvspec.py`.

**UTM fixture assets:** All 8 fixtures exist under `fixtures/`: `2026-07-03-valid-asset`, `2026-07-03-wrong-medium`, `2026-07-03-campaign-mismatch`, `2026-07-03-unknown-source`, `2026-07-03-absent-source`, `2026-07-03-malformed-query`, `2026-07-03-missing-line`, `2026-07-03-multi-defect`.

**Publish fixtures:** All 18 fixtures confirmed under `fixtures/publish/`: gap-2 gate tests (`pass-one-channel`, `pass-three-channels`, `missing-verdict`, `verdict-fail`, `failed-checks-nonempty`, `killed`, `missing-verdict-and-killed`, `unparseable-verdict`, `no-channel`, `unmapped-channel`), plus package-generation tests (`pkg-pass`, `pkg-no-captions`, `pkg-missing-channel-caption`, `pkg-bad-utm`, `pkg-empty-surfaces`, `pkg-no-manifest`, `pkg-multi-surface`, `pkg-per-channel-caption`).

**Metrics fixtures:** All test-case directories present: `full/`, `truncated/`, `wrong-header/`, `wrong-colcount/`, `non-numeric/`, `wrr-partial/`, `wrong-utm/`, `unmatched/`, `blank-cell/`, `blank-join/`, `header-only/`, `zero-cell/`.

**Golden scorecards:** All expected markdown files present under `fixtures/metrics/expected/`: `full.md`, `empty.md`, `partial.md`, `wrr-partial.md`, `wrong-utm.md`, `unmatched.md`.

**Real PASS asset:** `content/2026-07-03-tgrera-enforcement-wave/` confirmed present with `verdict: "PASS"`, `failed_checks: []`, and `captions.md` present.

## Strengths

1. **Clear and complete specification:** §3 defines invocation, exit codes, temp directory isolation, normative expectation table, cross-gap seam chain (6 numbered steps with specific assertions), and table coverage checking.

2. **Testable at every level:** Each row in the expectation table (§3.3) specifies fixture name, expected exit code, cited reason substring, and whether writes should occur. The seam chain (§3.4) defines path-independent invariant assertions (JSON fields, not byte-equality, accounting for temp-dir path instability). Golden markdown files are byte-compared. Attack checklist (§9) provides 12 specific failure modes to verify.

3. **Not gameable:** 
   - Cited-reason enforcement prevents false passes (wrong exit reason fails the row).
   - Table coverage checking catches unchecked fixtures or missing directories.
   - Determinism requirements (sorted output, fixed table order) prevent randomness.
   - "No write" assertions after refusals prevent sneaky queue/package writes.
   - Repo cleanliness check prevents leftover artifacts.
   - Frozen-module integrity check prevents modification of earlier sprints.

4. **Well-justified design choices:** §7 explicitly explains why generated artifacts are NOT byte-compared (temp paths are absolute and unstable) but use path-independent field invariants instead. This is sophisticated and correct.

5. **Assumptions properly documented:** §11 lists A-6.1 (frozen CLI messages stable), A-6.2 (week 2026-W27 canonical), A-6.3 (join key is utm_campaign), A-6.4 (unparseable-verdict exit code flexibility). Each is reasonable and grounds the contract's dependencies.

6. **Verification commands explicit:** §8 provides 5 exact reproducible commands for the Evaluator, plus hygiene greps for network/wall-clock contamination.

## Findings

### Finding M-001: Ambiguous fixture-to-row mapping in publish table

**Severity:** Medium  
**Category:** Specification clarity  
**Status:** Clarify  

**Issue:**  
§3.3 (Gap 2 publish table) row 160 is:  
```
| `no-channel` / `unmapped-channel` | 2 | zero/unmapped channels | **no** |
```

This single row names two fixture directories. However, §3.5 table coverage states: "the set of committed fixture directories on disk and the set named by table rows, and fails if any on-disk fixture is unnamed or any table row names a missing directory."

The phrase "exactly one expectation-table row" (advisor notes) could be read as requiring each directory to have its own row. The current phrasing leaves ambiguous whether one row covering two directories satisfies coverage, or if two separate rows are required.

**Expected clarification:**  
Either:
1. Confirm that a single row with "fixture-a / fixture-b" syntax covers both directories for the coverage invariant.
2. Create two separate rows (one per fixture directory).
3. Reword §3.5 to explicitly allow "one or more rows may name a single fixture directory" if intent is flexibility.

**Pass condition:**  
The contract or the Generator's trace clarifies the intended semantics and implements coverage checking accordingly (both interpretations are valid; consistency is required).

---

## No Blockers

The contract is complete, grounded in existing artifacts, and ready for implementation. The ambiguity noted above is not a gate-closer — it is a minor specification clarity item that the Generator can resolve by choosing one interpretation and documenting it in the trace.

