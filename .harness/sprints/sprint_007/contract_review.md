VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

---

## CONTRACT REVIEW — Sprint 007: Skill + README (documentation-only)

**Timestamp:** 2026-07-10  
**Mode:** CONTRACT_REVIEW  
**Scope:** Update `/loop-publish` skill and `README.md` to document the finalized `publish_api.py` CLI (built in Sprints 001–006).

---

## Summary

This is a **tight, testable, documentation-only sprint** with excellent specificity and clear reconciliation requirements. The contract is well-suited to multi-agent harness execution:

- ✅ **File scope:** Exactly 2 files changed (SKILL.md, README.md); nothing under `tools/`, `content/`, or `.env`
- ✅ **Core requirement:** Reconcile stale "no posting API" claims (§2), not merely append new prose
- ✅ **Greppable claims:** 14 specific claims (C1–C14) that must appear in docs, with grep-testable verification
- ✅ **Runnable verification:** 7 verification steps (§8) with explicit commands, expected outputs, and regression gates
- ✅ **Value/flag fidelity:** §5 value table enforces exact match to `--help` verbatim via C17
- ✅ **Secrets discipline:** No real tokens in docs; grep pattern test (§8.7) proves it
- ✅ **Anti-gameable:** Cannot reconcile without removing/reworded old sentences; cannot invent flags; cannot skip command testing; cannot add secret literals

---

## Elements Passing Review

### 1. Reconciliation Requirement (§2, C1, C15)
The contract explicitly identifies a **contradiction in current docs:**
- SKILL.md intro: *"no live posting API and no credentials"*
- README.md "Publish layer (Gap 2)": *"no posting APIs ... human posts manually"*

**Requirement is non-ambiguous:** These are stale claims that must be **reworded** (not just appended around), explicitly reframing the tool as **dry-run-first** with live mode **gated** on three preconditions (§7, C7). This prevents docs from remaining self-contradictory.

Verification: §8.2 greps confirm old sentences are gone/reworded.

### 2. Required Claims and Greppable Verification (C1–C14, §8.3)
All claims are **specific and testable via grep:**

| Claim | Target | Grep Test | Testable |
|-------|--------|-----------|----------|
| C1 | SKILL.md intro | rewords "no live posting API" | ✅ |
| C2–C4 | dry-run default command + behavior | multiple greps: `--dry-run`, `publish_api.py` | ✅ |
| C5 | manual flow retention | grep `mark_posted.py` present | ✅ human review |
| C6–C7 | live command + three preconditions | grep `--live`, `--i-have-verified-dry-run`, `SETUP-CHECKLIST` | ✅ |
| C8–C9 | day-cap + transition semantics | grep `--max-per-day`, `queued → posted` | ✅ |
| C10–C11 | facebook flag + LinkedIn selector | grep `--enable-facebook`, `round-5-gap`, `--linkedin-post-type` | ✅ |
| C12–C13 | exit codes + skill discipline | grep exit codes `0/1/2` + no auto-fix instruction | ✅ |
| C14 | secrets discipline | grep `REDACTED`, no real tokens | ✅ |

### 3. Verification Commands (§8, concrete and runnable)
Eight verification steps, each with **exact bash commands**:

1. **File scope:** `git status --porcelain` — confirms only 2 files changed ✅
2. **Stale-claim reconciliation:** `grep "no live posting API"` — confirms removal ✅
3. **Greppable claims:** 8 specific grep invocations for SKILL.md + README.md ✅
4. **Command execution:** `python3 tools/marketing-loops/publish_api.py --week 2026-W28 --dry-run` — must exit 0, write plan, leave queue untouched ✅
5. **Flag/default fidelity:** `python3 tools/marketing-loops/publish_api.py --help` — verifies `--max-per-day` default 3, `--linkedin-post-type` default document, etc. (§5 value table) ✅
6. **Regression gate:** `python3 -m unittest discover -s tools/marketing-loops/tests -v` — all prior tests green ✅
7. **Secrets audit:** `grep -nE "(EAAB|Bearer [A-Za-z0-9]{10,}|IGQ[A-Za-z0-9])" …` — no real tokens ✅

### 4. Value Table Fidelity (§5, C17)
**Value table § 5 specifies 11 key flags/defaults**, enforced by C17: *"Every flag/default the README cites must match `--help` verbatim."*

| Flag | Documented Fact | Testable |
|------|-----------------|----------|
| `--week YYYY-Www` | Required run scope | ✅ |
| `--dry-run` | Default when neither flag given | ✅ |
| `--live` | Gated on preconditions | ✅ |
| `--date YYYY-MM-DD` | Required in `--live`; never wall-clock | ✅ |
| `--max-per-day N` | Default **3** | ✅ |
| `--enable-facebook` | Default **OFF**; round-5-gap | ✅ |
| `--linkedin-post-type` | `{document,multi-image}`, default **document** | ✅ |
| `--linkedin-version` | Default **202506** (fixed constant) | ✅ |
| `--public-asset-base-url` | Optional dry-run; live gate (b) | ✅ |
| `--env` | Default **`.env`** | ✅ |
| `--i-have-verified-dry-run` | Live gate (c) acknowledgment | ✅ |

Verification: §8.5 `--help` diff against table.

### 5. Non-Goals and Scope Boundaries (§7, §10)
**Clear exclusions prevent scope creep:**
- No code changes to `publish_api.py` or tools
- No new flags or changed defaults
- No broad README rewrite (only one stale-claim reconciliation + one publish_api subsection)
- No edits to other skills
- No pasted full plan-dump output (show commands, describe behavior instead)
- No `.env` example with real-looking tokens
- Not documenting Ayrshare/Buffer, OAuth, LinkedIn org posting, or public asset hosting (all spec §8 non-goals)

### 6. Acceptance Criteria (A1–A8, testable)
All 8 acceptance criteria are **concrete and testable:**

- A1: Only 2 files changed (git status) ✅
- A2: Both stale claims reconciled (grep evidence) ✅
- A3: SKILL.md documents all required elements (C1–C14) ✅
- A4: README.md has publish_api subsection with required content (C15–C17) ✅
- A5: Documented commands run as specified; real-asset dry-run exits 0 (§8.4) ✅
- A6: Every flag/default matches `--help` verbatim (§8.5, §5 value table) ✅
- A7: Full prior unittest suite green (§8.6) ✅
- A8: No secret literal in either doc (§8.7 grep) ✅

---

## Risk Assessment

### Low Risk: Documentation-Only
- No code changes → no runtime breakage
- No new API facts → no re-derivation from spec
- No new adapters or transport changes → no blast radius to prior sprints

### Non-Gameable Enforcement
1. **Stale-claim reconciliation:** Cannot just append; §8.2 greps confirm OLD sentences gone/reworded
2. **Greppable claims:** C1–C14 must all appear in docs; §8.3 grep tests verify presence
3. **Command execution:** §8.4 RUNS the actual command; cannot fabricate output or skip testing
4. **Flag fidelity:** C17 + §8.5 enforce exact match with `--help`; cannot invent flags or change defaults
5. **Secrets discipline:** §8.7 grep pattern test proves no real tokens; cannot include fake-looking credentials
6. **Regression gate:** §8.6 full unittest suite must stay green; prior work must not regress

### Potential Vagueness (Mitigated)
- **§4 C16 "placed logically":** Subsection placement is subjective, but content requirements are concrete (C15–C17). Evaluator can make sound judgment.
- **C5 "manual flow retention":** Not grep-tested, but clear requirement; evaluator verifies during human review (mark_posted.py steps remain in SKILL.md).
- **"No pasted plan dump" (§7):** Not automatically tested, but C17 says "show commands, describe behavior" — evaluator can spot full dumps during review.

These are acceptable for a documentation sprint; prose requirements cannot be fully automated.

---

## Conclusion

**VERDICT: ACCEPT**

This contract is:
- ✅ **Specific:** 14 required claims (C1–C14), 8 verification steps (§8), 8 acceptance criteria (A1–A8)
- ✅ **Testable:** Grep commands, bash execution, regression gates, all deterministic
- ✅ **Non-ambiguous:** Reconciliation requirement explicit (§2); no invented features
- ✅ **Anti-gameable:** Cannot bypass old-claim reworded verification, command testing, flag fidelity, or secrets discipline
- ✅ **Tight scope:** Exactly 2 files; no tool/content/secret artifact changes
- ✅ **Well-founded:** Ground truth (`publish_api.py --help`, prior test suite, real-asset dry-run) specified

No blockers. No high-severity concerns. The documentation sprint can proceed with confidence that the contract will catch scope creep, unsupported claims, and incomplete reconciliation.

**Ready for implementation.**
