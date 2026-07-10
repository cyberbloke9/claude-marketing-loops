VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

# Contract Review: Sprint 001 — Frozen-module extension (facebook) — Round 2

## Round 1 Blocker: RESOLVED

Round 1 identified Finding C-001 (contradictory baseline / test-exclusion claim). The contract has been corrected:

- **§4d** now states: "`test_tgrera_enqueues_three_rows` **PASSES** in the current baseline (§6 confirms 254 OK, zero failures)" — the false "pre-existing-failing" claim has been removed.
- **§6** baseline is empirically verified: `python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_*.py'` → `OK, 254 tests` ✓
- **§7 Gate clause 2** expects "zero failures" — now unambiguously consistent with §6 and §4d.

All three sections are now mutually consistent and factually grounded.

---

## Contract Strength Assessment

### Testability
- **Gate clause 1** (channel-map-touching files fully green): explicit unittest commands, expected output `OK, 0 failures`.
- **Gate clause 2** (both suites stay green): explicit discover command, baseline counts verified (254).
- **Gate clause 3** (no KeyError; behaviors hold): inline Python script with 8 atomic assertions, expected output `OK, exit 0`.
- **Gate clause 4** (import silence): explicit command, expected empty stdout.

All gates are deterministic and unambiguous.

### Specificity
- **§2** (Files affected): production files listed (utm.py, channels.py, schedule.py), verification files listed (queue.py, captions.py).
- **§4** (Test-site enumeration): comprehensive breakdown (4a: must update with exact file:line; 4b/4c/4d: unaffected with reasoning).
  - §4a: `tests/test_utm.py:39-40` exact new assertion `== ["facebook","instagram","linkedin","youtube"]` (alphabetical).
  - §4a: `tests/test_channels.py:27-28` exact new assertion `== ("instagram","youtube","linkedin","facebook")` (insertion order).
  - §4b/4c/4d: 7 derived/looping/unaffected test sites explicitly triaged with pass/no-edit reasoning.
- **Fallback (end of §4)**: "If BUILD reveals a channel-set assertion not listed here, it must be updated too (B37: 'enumerate all, do not stop at these')."

No vague "test carefully"; every assertion is enumerated or explicitly out-of-scope.

### Anti-Gameable Safeguards
1. **Ordinal preservation**: §4a requires exact sorted and insertion order; byte-identical on the first three channels (testable).
2. **Conscious updates**: Contract uses "consciously" multiple times to signal deliberate action, not accidental. Test breakage is the natural enforcement.
3. **No-KeyError guard**: §7 gate clause 3 asserts six function calls that would KeyError if captions.py or queue.py are not map-derived — empirically catching any drift.
4. **Unmapped-token preservation**: §5 explicitly states "a genuinely unknown platform (e.g. `Twitter`, `TikTok`) is STILL surfaced as unmapped" — guards against collateral damage.
5. **No-regress baseline**: §6 locks the baseline to "254 OK"; gate clause 2 requires "zero failures" — any new breakage is caught.

### Comprehensive Coverage
- **Baseline state** (§6): "As of orchestrator commit `201456c`…" — specific, reproducible.
- **Non-goals** (§8): No `publish_api.py`, no adapters, no renderer changes, no queue-schema change, no wall-clock, no dependency.
- **Risks** (§12): Re-render wipes qa-verdict (not relevant this sprint), ordinal preservation (explicit), hyphenated module paths (documented workarounds).
- **Acceptance summary** (§11): 6 atomic criteria, all testable.

### Schedule Times (Minor Pattern Guidance)
- §2 specifies: `"facebook": {BUCKET_MORNING: "<HH:MM>", BUCKET_EVENING: "<HH:MM>"}` to `_TIMES`.
- §2 provides pattern: "fixed documented A/B-hypothesis constants (module-authored, same shape as the existing three)."
- §7 gate clause 3 verifies behavior (bucket math works, no KeyError) rather than exact times — reasonable, since times are local policy.

### Test Case Location (Flexibility, Well-Documented)
- §2 states: "Tests (add — new regression cases, **may live in the existing files**)".
- §7 gate clause 3 provides the exact Python assertions that must pass — author can place these in existing test files or new methods; the behavior is what matters.

---

## Final Assessment

**The contract is:**
- ✓ Specific: exact file paths, line numbers, required assertions.
- ✓ Testable: four concrete gate clauses; empirical baseline verified.
- ✓ Unambiguous: no contradiction; all parts mutually consistent.
- ✓ Anti-regressive: preserves ordinals, enforces all-green baseline, guards unmapped-token behavior.
- ✓ Comprehensive: non-goals explicit, risks documented, acceptance summary atomic.

**No remaining blockers or high-severity concerns.** The contract resolves the round-1 finding and is ready for implementation.

---

## Trace Note

Round 1 rejection: C-001 (contradictory baseline / test-exclusion).  
Round 2 fix: §4d rewording removes false pre-existing-failure claim; §6 baseline verified empirically (254 OK); gate clause 2 consistency restored.  
Evaluation: Contract is now consistent and testable.
