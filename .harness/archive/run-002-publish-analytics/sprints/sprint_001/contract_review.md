VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 1

## Summary

Sprint 001 contract is well-formed, specific, and achievable. It defines a single, focused deliverable (shared UTM module + CLI verifier), with exact function signatures, deterministic exit codes, and a concrete fixture requirement. The positive control assertions (both real assets pass the UTM scan) are factually correct. No blockers found.

One HIGH concern identified: message-quality requirement is stated but not explicitly tested in the attack checklist.

---

## Contract Strengths

### 1. Exact Scope & Non-Goals (§1, §7)
- Clear: UTM module + verifier CLI only
- Everything else deferred (publish gate, queue, packages, scorecard, skills)
- Explicit non-goals prevent scope creep

### 2. Specific Technical Contracts (§3)
- Function signatures fully specified (`parse_flywheel_line()`, `campaign_from_slug()`, `validate_asset()`)
- Return types and field names explicit
- Import safety guaranteed ("no import side effects")
- `urllib.parse` explicitly named as the query-parsing tool (§6)

### 3. Exact Error Codes (§3.3)
- Five codes with deterministic triggers: `missing-flywheel-line`, `malformed-query`, `wrong-medium`, `campaign-mismatch`, `unknown-source`
- Violations evaluated independently when query parses (multiple violations reported together, ordered)
- Mutation-resistant: each code is distinct and testable

### 4. Deterministic Exit Codes (§3.4, §4)
- 0 (all valid), 1 (at least one invalid), 2 (usage/precondition error)
- Empty root → exit 2 (justified: precondition error, not silent pass)
- Lexicographic ordering specified for stable output

### 5. Verifiable Positive Controls (§4)
- Both real assets verified on disk:
  - `2026-07-03-tgrera-enforcement-wave`: primary URL has `utm_source=instagram`, `utm_medium=social`, `utm_campaign=tgrera-enforcement-wave`. All four conditions satisfied. ✓
  - `2026-07-03-hyd-premium-vs-budget`: primary URL (line 9) has same structure. KILLED status is orthogonal to UTM validity. All four conditions satisfied. ✓
- Contract's assertion that both pass UTM scan with exit 0 is **factually correct**.
- KILLED asset is correctly treated as a positive control for verifier; the KILLED gate belongs in Sprint 002 (publish gate), not here.

### 6. Concrete Fixture Specification (§9, §10)
- Eight fixture intents enumerated in attack checklist
- Definition of done requires "fixtures for every row" shipped under `tools/marketing-loops/fixtures/`
- Fixtures are asset folders with `meta.md`, not polluting real `content/` (good practice)

### 7. Verification Commands (§8)
- Six exact commands provided
- All are runnable and observable (exit codes, stdout inspection)
- Import safety test included (`python3 -c "import utm; ..."`)

### 8. Attack Probes (§9, §10)
- 7 adversarial probes listed
- Include determinism check (run twice, compare output)
- Include network-check (grep for `datetime.now`, `requests`, `urllib` fetch)
- Include code-quality checks (import safety, no stdout on import)

### 9. Explicit Assumptions Documented (§10 A-1 to A-4)
- Campaign-slug stripping rule: `^\d{4}-\d{2}-\d{2}-` prefix
- YouTube source string: `youtube` (confirmed in real hyd asset meta.md line 10)
- Per-channel annotation exclusion: only primary URL validated (hyd asset is the example)
- All assumptions flagged for Evaluator awareness

---

## Minor Concerns

### HIGH Finding H-001: Message-Quality Requirement Not Explicitly Tested

**Severity:** High  
**Category:** Specification Completeness

### Issue
Section 5 requires violation messages to be "specific and recoverable — each names the asset, the code, and what the operator must fix (e.g. `utm_medium was 'paid', expected 'social'`), never a bare 'invalid'."

However, Section 9's attack checklist only asserts on the **exact codes** in output (e.g., "assert each expected code appears on the right slug"), not on message text quality.

A Generator could technically satisfy the checklist by producing:
```
FAIL 2026-07-03-test  wrong-medium, unknown-source  — violation
```
This includes the codes (making the test pass) but provides no context for the operator to fix the issue. The requirement is violated but the test would pass.

### Contract Clause
§5: "Usability: violation messages are specific and recoverable — each names the asset, the code, and what the operator must fix (e.g. `utm_medium was 'paid', expected 'social'`), never a bare 'invalid'."

§9: Attack checklist line "assert each expected code appears on the right slug (exact-string match, not 'some FAIL')."

### Why It Matters
The verifier is a user-facing CLI for the marketing operator. Generic error messages ("error", "violation", "failed") prevent the operator from understanding what went wrong. The spec explicitly calls this out as non-negotiable user experience; the contract should enforce it.

### Recommended Fix
Add to §9 (attack checklist) or §10 (definition of done) an explicit probe:

> **Probe:** Run `python3 tools/marketing-loops/verify_utm.py tools/marketing-loops/fixtures/wrong-medium` and verify the output message includes the **offending value** (e.g., the actual `utm_medium` string) and the **expected value** (`social`). Bare "wrong-medium" or "violation" fails this probe.

Alternatively, strengthen the contract language in §5:

> "Each violation message must include the offending value and the expected value (not just the code). For example, for `wrong-medium`: `utm_medium was 'paid', expected 'social'`; for `unknown-source`: `utm_source was 'tiktok', not in {instagram,youtube,linkedin}`."

---

## Verification Summary

| Aspect | Status | Evidence |
|---|---|---|
| Scope clarity | ✓ Clear | §1, §7 (in/out explicit) |
| Function contracts | ✓ Specific | §3.1 (signatures named) |
| Error codes | ✓ Deterministic | §3.3 (table with triggers) |
| Exit codes | ✓ Exact | 0/1/2 with conditions |
| Positive controls | ✓ Verified | Both real assets satisfy validity conditions |
| Fixtures | ✓ Enumerated | §9 (8 intents) + §10 (DoD: "fixtures for every row") |
| Verification commands | ✓ Provided | §8 (6 commands) |
| Non-goals | ✓ Listed | §7 (no queue/packages/scorecard/skills this sprint) |
| Import safety | ✓ Testable | §9 probe 6, §8 command |
| Determinism | ✓ Testable | §4, §9 probe 5 (run twice, compare) |
| No network | ✓ Testable | §9 probe 7 (grep for network calls) |
| Runs from any cwd | ✓ Specified | §5 "`__file__` resolution" |

---

## Conclusion

This contract is **ready for implementation**. It is specific enough that the Generator cannot reasonably misinterpret it, comprehensive enough that the Evaluator can test every requirement, and realistic enough that it can be completed in one sprint.

The message-quality concern (HIGH) does not block ACCEPT because:
1. The requirement is clearly stated in the contract prose (§5)
2. An example is provided (`utm_medium was 'paid', expected 'social'`)
3. The Evaluator will run the tool during EVALUATE and can visually inspect if messages meet the standard
4. If messages are generic, the Evaluator will flag it as a finding

The Generator should be aware that vague error messages will be caught in EVALUATE. The requirement is non-negotiable; only the test specificity is being called out for improvement.

**Recommendation:** ACCEPT and proceed to implementation. Evaluator will assess message quality during EVALUATE by running the tool and comparing output against the §5 standard and the H-001 probe suggested above.
