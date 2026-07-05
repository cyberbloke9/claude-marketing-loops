VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Contract Review — Sprint 005

The Sprint-005 contract is **well-formed, testable, and non-gameable**. All frozen dependencies (INGEST structure, QUEUE schema, schedule slot format, template headings) are verified to exist with the exact structure the contract requires.

### Verification Summary

**1. Template fidelity (§3.2)** ✓
- Confirmed: `metrics/TEMPLATE.md` contains exact headings the contract pins:
  - `## North star`
  - `## Flywheel`
  - `## Craft diagnostics (per asset)`
  - `## Posting-time A/B (weeks 1–8)`
  - `## Vanity (tracked, never optimized)`
  - `## Decisions fed back`
- All byte-equality golden-match tests are verifiable against the template.

**2. INGEST schema keys verified** ✓
- `tools/marketing-loops/ingest.py` (frozen Sprint-004) produces the exact INGEST structure the contract reads:
  - `ingest["wrr_components"]` — dict with keys `"returning_viewers"`, `"digest_opens"`, `"returning_visitors_social"`, each mapping to `{"present": bool, "value": int|None, "source": "site"}` (line 169).
  - `ingest["flywheel_clicks_by_campaign"]` — list of `{campaign, clicks}` dicts, sorted lexicographically (lines 140-143).
  - `ingest["craft"]` — list of `{campaign, channel, slug, hook_number, three_s_hold_pct, completion_pct, shares, clicks}` dicts (lines 113-122).
  - `ingest["absences"]` — deduplicated list of `{kind, detail}` dicts (line 197).
  - `ingest["assets"]` — sorted list with `utm_valid` field per asset (line 60 of `assetmap.py`).
- No INGEST key the contract requires is missing or misnamed. The B-A5 WRR critical edge (all-three-components-present check) is fully implementable from these keys.

**3. Schedule slot format pinned** ✓
- Confirmed: `tools/marketing-loops/schedule.py` line 79 produces slot strings exactly as the contract specifies: `"{}/{}/{}".format(week, bucket, _TIMES[channel][bucket])` → `<week>/<bucket>/<HH:MM>`.
- §3.6 A/B parsing logic (split on `/`, index 1 for bucket) is correct and deterministic.

**4. Loop-measure SKILL exists** ✓
- `.claude/skills/loop-measure/SKILL.md` exists. Current form is narrative documentation.
- The contract B-A12 deliverable is to update it to invoke `scorecard.py` (with CLI commands, malformed-CSV-vs-missing-input distinction, never-invent rule), mirroring loop-publish SKILL style — this is a clear, implementable requirement, not vague.

### Strengths

1. **Precise test specifications** — §8 provides exact CLI commands with fixture paths and expected outputs (golden-match diffs, exit codes, stdout substrings).
2. **Comprehensive adversarial checklist** — §9 enumerates 13 specific attack vectors, each with exact pass criteria:
   - WRR critical edge (one component blank → **blank WRR, NOT partial sum**)
   - Corruption never silently becomes blank (exit 2, no file written)
   - Unmatched campaigns flagged
   - Determinism (two runs → identical shasum)
   - Import safety (no network, no datetime.now)
3. **Non-gameable requirements**:
   - Golden-match byte equality forces correct implementation.
   - Missing-data section must enumerate every blank with specific reason.
   - A/B single-week semantics are pinned with explicit acknowledgment of half-empty table as intent (§3.6 rationale).
4. **Clear boundaries**:
   - §7 Explicit non-goals: no acceptance runner, no README update, no new JSON schema, no reading prior scorecard, no network, no estimation.
   - §2 "No modification of any Sprint-001..004 module" — frozen reference is concrete and verifiable.
5. **Template-faithful rendering** — §3.2–3.10 specify exact Markdown structure, heading-for-heading reproduction, stable row ordering, byte determinism.

### Minor Notes (non-blocking)

1. **Deliverables vs prerequisites clarified** — The contract uses "New" language for fixtures (`wrr-partial/site.csv`, `expected/*.md`, `full/queue.json`, SKILL update). These are Sprint-005 deliverables, not prerequisites. The contract is clear: Generator must create them.
2. **INGEST schema reference external** — The contract does not reproduce the full INGEST schema inline, instead describing it through usage (§3.3–3.9 show which keys are read). This is acceptable because Sprint-004's `ingest.py` is frozen and documented; Sprint-005 only imports it read-only.
3. **Template preamble and decisions qualitative content** — The contract references "the template's" exact wording (e.g., "which signal types resonated / flopped") but does not repeat it. Generator must consult the template file, which is standard practice and explicit in §3.8 ("reproduce the template's ... structure").

### Testability Assessment

The contract is **fully testable by automated CLI invocation**:
- All commands in §8 are deterministic (no wall-clock, no randomness).
- All expected outputs are byte-verifiable (golden-match diffs, exit codes, grep assertions).
- All fixtures referenced are either pre-existing (Sprint-004 exports, full/ig.csv etc.) or specified for creation (wrr-partial/, expected/).
- All error paths are testable (corrupt CSV → exit 2, bad queue path → exit 2, etc.).

The Evaluator can:
1. Run the full command suite in §8.
2. Verify golden-match byte equality for full/empty/partial cases.
3. Confirm exit codes and stderr messages for error cases.
4. Grep for never-invented numbers (no `N/A`, no partial sums, no fabricated trend).
5. Re-run determinism test (shasum comparison).
6. Verify frozen Sprint-001–004 suite still passes.
7. Inspect the SKILL update for CLI invocation and rule documentation.

---

## Recommendation

**ACCEPT for implementation.** The contract meets all standards:
- ✓ Requirements are specific and testable.
- ✓ All frozen dependencies are verified.
- ✓ Exit codes and error paths are pinned.
- ✓ Golden fixtures and commands are precise.
- ✓ WRR critical edge is un-gameable (blank-not-sum rule enforced by test).
- ✓ No vague references; all template/structure references are resolvable from repo files.

The Generator can proceed with implementing `scorecard.py`, tests, fixtures, and the SKILL update exactly as specified in §2–§10, and the Evaluator can verify using §8–§9.
