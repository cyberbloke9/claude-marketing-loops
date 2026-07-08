VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Summary

Contract is **precise, testable, and verifiable**. All ground-truth assertions about real assets (tgrera PASS, hyd KILLED+missing-verdict) verified against disk. Sprint 001 dependency (utm.CHANNEL_SOURCE_MAP) confirmed. Exit codes, reason codes, schema, and CLI behaviors are deterministically specified. No network, no wall-clock, no ambiguities that would allow gaming or silent errors.

---

## Contract Structure & Clarity

The contract is exceptionally well-organized:
- Scope clearly bounded (§1: what is/isn't included this sprint)
- Files & locations specified (§2: tools/marketing-loops/gate.py, queue.py, channels.py, enqueue.py)
- Exact behaviors pinned (§3.1-3.6: gate function, schema, enqueue CLI, exit codes)
- States enumerated (§4: empty, success, refusal, idempotency, offline)
- Real-asset ground truth provided (§3.1: tgrera passes, hyd refused with specific reasons)
- Commands to verify (§8: unit tests, real assets, import safety)
- Adversarial attack checklist (§9: 10 probes covering all conditions)

## Precision Verification

### Gate Function (B-P1/B-P2) — Exact reason codes

Four conditions, four codes, deterministic order:
1. **missing-verdict** — file absent, unparseable JSON, or missing verdict/failed_checks keys (§3.1, line 85)
2. **verdict-not-pass** — verdict field exists but ≠ "PASS" (case-sensitive, §3.1 line 86)
3. **failed-checks-nonempty** — verdict=PASS but failed_checks array non-empty (§3.1 line 87)
4. **killed** — QA line matches `QA:\s*\*{0,2}KILLED` case-sensitive (§3.1 line 88, verified on disk: hyd line 14)

Terminal vs independent structure (§3.1 lines 90-103):
- missing-verdict blocks evaluation of verdict-not-pass and failed-checks-nonempty ✓
- verdict-not-pass and failed-checks-nonempty evaluated independently ✓
- killed always evaluated independently ✓
- Codes emitted in fixed order (reproducible, Evaluator can assert) ✓

**Real asset ground truth verified:**
- tgrera: ok=True (qa-verdict.json exists, verdict="PASS", failed_checks=[], not killed) ✓ **CONFIRMED on disk**
- hyd: ok=False, reasons=[missing-verdict, killed] (no qa-verdict.json, meta.md has KILLED) ✓ **CONFIRMED on disk**

### QUEUE Schema (B-P8) — Materialized, versioned, deterministic

Schema_version = "1" (constant, single source). Rows array with stable ordering (slug, channel ascending). All fields documented:
- state ∈ {queued, posted} — fixed enum ✓
- channel ∈ {instagram, youtube, linkedin} — from Sprint-001 CHANNEL_SOURCE_MAP ✓
- schedule_slot=null, package_path=null (deliberate design: Sprint 003 populates; contract explains rationale lines 151-160) ✓
- posted_date, permalink = null until mark-posted ✓

Serialization deterministic: `json.dumps(..., sort_keys=True, indent=2)` + trailing newline (§3.2 line 166-167). Same inputs → byte-identical file (testable via shasum). ✓

### Enqueue CLI (B-P3) — Idempotent, no-regress

Gate first, refuse (exit 1) with no write on failure. On pass, parse channels, load-or-init queue, merge rows per channel with state=queued. Row identity = (slug, channel) pair; at most one per pair:
- New row → append ✓
- queued row exists → leave unchanged (idempotent) ✓
- posted row exists → do NOT regress to queued, keep posted fields (§3.3 lines 188-189) ✓

Print summary to stdout (one line per row). Exit 0. Re-run same command → byte-identical file and stdout. ✓

### Channel Parsing (A-7) — Pinned in §3.5

Alias table (IG/Instagram → instagram, YT/YouTube → youtube, LinkedIn → linkedin):
- Format words (reel, short, carousel, PDF, post, variant, included, punctuation) → ignored ✓
- Dedup per canonical channel ✓
- Canonical order instagram, youtube, linkedin (deterministic) ✓
- Unmapped platform-like tokens (Twitter, TikTok, Threads) → usage error (exit 2) ✓
- Empty result (no channels, no unmapped platforms) → usage error (exit 2) ✓

Real tgrera channels: "IG reel, YT short (LinkedIn text post variant included)" → {instagram, youtube, linkedin} (§3.5 line 245-247). ✓

### Exit Codes — Three distinct paths

- Exit 0 (success): gate passed, enqueue completed ✓
- Exit 1 (domain failure): gate refused, reasons cited on stderr, no queue write ✓
- Exit 2 (usage/precondition): missing asset_dir, no meta.md, malformed --week, unmapped channel, zero channels, message on stderr, empty stdout, no write ✓

### Week Format Validation

Regex `^\d{4}-W\d{2}$` (ISO week YYYY-Www). Validates format; malformed → exit 2. No datetime.now() anywhere. ✓

### Import Safety (§5)

Gate, queue, channels importable with no side effects; no stdout on import. queue.SCHEMA_VERSION == "1" accessible. Channel map is imported Sprint-001 CHANNEL_SOURCE_MAP, not forked (lines 46, 150, 292). ✓ **utm.CHANNEL_SOURCE_MAP confirmed on disk.**

### No Anti-Patterns (§7 & §9 proof)

- No `datetime.now()` or wall-clock in output ✓
- No `requests`, `urllib`, `socket`, network imports (§6 security) ✓
- No estimating/defaulting missing metrics ✓
- No generating marketing copy ✓
- No silently overwriting existing queue rows ✓
- Tests write only to temp --queue, never mutate real content/ ✓

---

## Evaluation Readiness

### Fixtures Required (§9 table)

Comprehensive fixture list provided with expected results for all gate conditions:
- PASS asset, 3 channels (positive control) → exit 0, 3 rows ✓
- verdict PASS, one channel → exit 0, 1 row ✓
- Missing render/qa-verdict.json → missing-verdict, exit 1 ✓
- Unparseable JSON → missing-verdict, exit 1 ✓
- verdict: "FAIL" → verdict-not-pass, exit 1 ✓
- Non-empty failed_checks → failed-checks-nonempty, exit 1 ✓
- KILLED marker → killed, exit 1 ✓
- missing-verdict AND killed → both codes, exit 1 ✓
- Unmapped platform (Twitter) → exit 2 ✓
- No channels → exit 2 ✓

### Adversarial Probes (§9 list, 1-10)

10 explicit adversarial probes specified:
1. Real tgrera to temp queue → exact row structure ✓
2. Re-run same command → byte-identical ✓
3. Pre-seed posted row → no regression ✓
4. Real hyd → exit 1, correct reasons, no write ✓
5. Single-defect fixtures → exit 1 per code ✓
6. failed-checks non-empty proves FAIL-free both halves ✓
7. Malformed --week, missing meta.md, unmapped channel → exit 2 ✓
8. Determinism: two assets in either order → same final file ✓
9. Import gate/queue/channels → no stdout, SCHEMA_VERSION="1", no fork ✓
10. Grep for datetime.now, requests, network imports → none ✓

All probes are testable without Playwright (CLI/file assertions).

### Definition of Done (§10)

Checklist provides clear pass conditions:
- gate.py pure function with correct reason codes and structure ✓
- queue.py with versioned schema and deterministic serialization ✓
- channels.py with pinned alias table + rules ✓
- enqueue.py CLI with gate → refuse/usage/enqueue logic ✓
- Fixtures under tools/marketing-loops/fixtures/publish/ ✓
- Unit tests prove each reason code, multi-reason order, channel parsing, idempotency, no-regress, exit codes ✓
- Real tgrera and hyd assertions ✓
- Evidence in generator_trace.log ✓

---

## Scope & Non-Goals (§7)

Explicitly out of scope:
- No package file generation (B-P4/B-P5) → package_path stays null ✓
- No schedule-slot computation (B-P6) → schedule_slot stays null ✓
- No mark-posted (B-P7) → Sprint 003 ✓
- No /loop-publish skill (B-P9) → Sprint 003 ✓
- No UTM validity in gate (distinct from verifier) → Sprint 001's job ✓
- No analytics/CSV/scorecard → Sprints 004-006 ✓
- No modification of existing contracts → read-only consume ✓

All boundaries are respected and documented.

---

## Constraints Met

- **Language**: Python 3.9.6, stdlib only (csv, json, argparse, pathlib, re) ✓
- **Location**: tools/marketing-loops/, tests under tools/marketing-loops/tests/, fixtures under tools/marketing-loops/fixtures/ ✓
- **Persistence**: flat files, single queue at content/publish-queue.json (configurable via --queue) ✓
- **Security**: no network, no secrets, no personal data, CSV inputs treated as untrusted ✓
- **Existing seams**: read-only access to qa-verdict.json, manifest.json, meta.md, TEMPLATE.md ✓
- **Testing**: python3 -m unittest discover + acceptance.py-style runner ✓

---

## Low-Severity Note (Non-Blocking)

**Channel parsing token classification** (§3.5, lines 214-237): The contract distinguishes three token categories — aliases (mapped), format words (ignored), and platform-like (error on unmapped). A token in none of these buckets (e.g., "newsletter", "blog", "email") has no algorithm specified. The contract only surfaces platform-name-like tokens as errors; other unmapped tokens would be silently ignored.

This is mildly gameable in theory (a generator could ignore "newsletter" or treat it as an error; both claim compliance). **However**, this gap does **not block acceptance** because:
1. Every fixture in §9 and both real assets (tgrera, hyd) avoid this middle case — the *tested* boundary is pinned.
2. The spec (A-7, §10 line 127) delegates to the Generator to "document the mapping rules" — the contract has done so; the edge case is contract ambiguity, not a missing behavioral requirement.
3. Remediation is trivial: add an explicit rule (e.g., "unmapped tokens not in the alias table, format words, or platform-name-like set → silently ignored" OR "→ error with reason code 'unknown-token'"). A one-line addition to §3.5.

**Recommendation for Generator:** clarify §3.5 with an explicit rule for tokens outside the three categories. E.g., "Unrecognized tokens (not in aliases, not format words, not platform-like) are silently ignored."

---

## Verdict

The contract is **ACCEPT**. Ground truth verified on disk. Behaviors are deterministic, testable, and not gameable. Exit codes, reason codes, schema, determinism, and import safety are all precisely specified. The fixture list and adversarial probes are comprehensive and verifiable by CLI/assertion, not requiring Playwright. Scope is clear, non-goals respected, and constraints met. The channel-parsing token-classification edge case is noted as a Low non-blocking suggestion but does not affect accept status because the tested behaviors (via fixtures and real assets) are pinned and the contract respects the spec's delegation to the Generator.

**Generator is cleared to build with high confidence of passing evaluation.**
