VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Review Summary

The Sprint 003 contract is comprehensive, testable, and not gameable. All requirements are specific enough for implementation without clarification.

## Strengths

### 1. Testability
Eight gate clauses (§11) provide exact reproduction commands with concrete expected outputs:
- Gate 1: Full test suite green (new Sprint-003 cases + consciously updated Sprint-002 cases)
- Gate 2: No regression (all prior suites still pass)
- Gate 3: Real-asset dry-run with 8-step plan, queue unchanged, exit 0
- Gate 4: Fidelity inspection (redaction, placeholders, base-URL, determinism, blacklist guard)
- Gate 5: Concrete base-URL preview + >10/0 validation (exit 2)
- Gate 6: Live no-op is honest (exit 0, "nothing posted", no fake permalink, queue untouched, no secret echoed)
- Gate 7: AST no-network proof (1 urlopen site) + import clean
- Gate 8: Hygiene (only publish_api.py and test_publish_api.py modified, no secrets staged)

Each gate is reproducible from repo root; expected outputs are explicit.

### 2. Exact API Specification
Section 4 freezes the Instagram call sequence with zero ambiguity:
- Exact endpoints (`graph.instagram.com`, endpoint paths)
- Exact parameter names and order (params sorted, `access_token` as query param, no auth header)
- Exact response field paths (e.g., `resp.json()["data"][0]["quota_usage"]` for limit check)
- Exact placeholder names (`<ig-child-container-id-i>`, `<ig-parent-creation-id>`, `<ig-media-id>`)
- Exact stdout format (§7.2: 7 spaces before method+URL, `params: <k1=v1, k2=v2>` sorted)
- Exact JSON format (sort_keys, indent=2, payload null for IG)

Section 8 provides mock response shapes for each call, marked "documented assumptions" with live-pending flag—appropriate since real credentials don't exist yet.

### 3. All Behaviors Defined
**Happy path:** 3-image carousel → 8 steps (limit check, 3× child container, parent container, poll, publish, permalink fetch).
**Single-image degrade:** 6 steps (no carousel branch).
**Error paths:**
- Container `status_code == ERROR/EXPIRED` or poll-exhausted → `AdapterRefusal` (exit 1)
- Rate limit exceeded (`quota_usage >= quota_total`) → `AdapterRefusal` before any POST (exit 1)
- 0 or >10 attachments → `AdapterUsageError` (exit 2, no plan written)

**Live no-op (this sprint):** `--live` with instagram row passes gate, emits notice "instagram adapter ready; … Sprint 006; nothing posted", makes zero network calls, writes no queue, exits 0. Gate clause 6 verifies this.

### 4. All States Specified (§10, §6 spec conformance)
- Empty: no queued rows → exit 0, clear message
- Success (dry-run): full plan to stdout + publish-plan.json, queue untouched
- Loading: poll step rendered as discrete step (§4.3, one representative)
- Error — container: cited refusal (exit 1)
- Error — rate limit: cited refusal (exit 1)
- Invalid input: 0/>10 attachments, exit 2, cited, no plan write
- Live gate denied: missing tokens/base-URL/ack flag → exit 2, cited
- Feature-flag off: N/A this sprint (Facebook is 005)
- No-network proof: dry-run with raising transport still exits 0 with full plan

### 5. Real Data + Determinism
- Real asset: `content/2026-07-09-anarock-vs-propequity/` (3 attachments)
- Determinism proof in gate 4: byte-identical `publish-plan.json` on repeat runs
- No wall-clock anywhere (only `--week`/`--date` args)
- Bounded poll (MAX_POLL_ATTEMPTS constant, no time-bounded loop)
- Inter-poll delay (if used) injectable and no-op in tests

### 6. Shared-Flow Guarantee (§1.1, Anti-Stub Property)
`plan_steps` and `execute` must derive from single flow definition, not hand-written fiction. Parity test (§8.3) validates: for real instagram row, `len(plan_steps) == len(transport.calls)`, same method, same URL path. This is testable and prevents stub stubs.

### 7. Sprint-002 Regression Surface (§7, Conscious Update)
Contract enumerates the regression surface:
- Instagram row `steps` length: 0 → 8
- Instagram row `note`: old "no adapter" → new specific note
- Two Sprint-002 test assertions explicitly identified (and contract says "enumerate all … do not stop at these")
- Gate clause 2 runs full test suite to catch any missed assertions
- LinkedIn row stays `steps: 0` + Sprint-004 note, byte-identical

### 8. Security + Hygiene
- Token never in stdout or publish-plan.json; always `<REDACTED>` (B17, testable in §8.9)
- Token loaded from `.env` (untracked, gitignored) into memory only
- Only writes: `publish-plan.json` (dry-run); queue unchanged (write deferred to Sprint 006)
- `.gitignore` already covers `.env` and `content/publish-plan.json`

### 9. Blacklist Guard (RESEARCH.md §9)
Binding refuted names: `…_content_publishing` (permission), `media_publishing` (endpoint).
Allowed: `media_publish` (endpoint), `content_publishing_limit` (endpoint).
Gate clause 4 includes grep check: `grep -c 'media_publishing\|content_publishing"'` must print 0.

### 10. Non-Goals Explicitly Marked
Section 14 clarifies what is deferred:
- NO LinkedIn adapter (004)
- NO Facebook adapter (005)
- NO live posting from CLI (006)
- NO queue transition / permalink recording (006)
- NO day-cap enforcement (006)
- NO `execute()` wired into live `run()` path (006)

This prevents scope creep and feature-flag confusion.

### 11. Adapter Contract (§5)
Distinct exception types map to exit codes:
- `AdapterRefusal(message)` → domain refusal (exit 1)
- `AdapterUsageError(message)` → usage/precondition (exit 2)

Caller (Sprint 006's `run()`) maps these without string-matching.

## Potential Risks (Mitigated)

### Risk: Response Shapes Are "Assumptions" (Live-Pending)
**Nature:** §6 marks response shapes (quota_usage nesting, id field location, status_code values) as documented assumptions because live verification is deferred—no founder credentials yet.

**Mitigation:**
1. Assumptions are explicitly flagged "live-pending" and isolated in helper functions
2. Canned mock responses match the documented shapes exactly
3. §8 test scenarios verify adapter parses canned responses correctly
4. If live responses differ, ONLY the parse helpers change (e.g., `resp.json()["data"][0]` vs `resp.json()["config"]`), not the flow
5. Founder will verify against live API during their SETUP-CHECKLIST completion (gate deferred to end-user test)

This is appropriate risk management for a "no credentials yet" deliverable.

### Risk: Polling Must Be Bounded and Testable
**Nature:** §4.3 specifies no wall-clock, but polling must terminate in tests without blocking.

**Mitigation:**
1. Bounded by MAX_POLL_ATTEMPTS (module constant, default 30)
2. No time-bounded loop; count-bounded only
3. If inter-poll delay exists, it's injectable and no-op in tests (standard pattern)
4. Parity test uses canonical execution returning FINISHED on first poll (1 poll call)
5. Gate clause 6 (live no-op) uses injected RaisingTransport (never polled)

Clear and testable.

### Risk: Single-Image Degrade Parallel Path
**Nature:** §4.2 specifies different call sequence for 1-image carousels.

**Mitigation:**
1. Clearly documented with 6-step sequence vs 8-step
2. Unit test §8.7 explicitly tests this path
3. Same flow generator must handle both (shared-flow guarantee)
4. Parity test verifies for 1-image fixture

No ambiguity.

## No Blockers

All requirements are:
- ✅ Specific (exact endpoints, parameters, response fields, output format)
- ✅ Testable (8 gate clauses with reproduction commands and expected outputs)
- ✅ Not vague (every undefined term is defined; every decision disclosed)
- ✅ Not gameable (each gate verifies exact behavior, not just "no error")
- ✅ Appropriately bounded (8 features, 1 adapter, deferred features marked 006)
- ✅ Secured (token redaction, gitignore, no secrets in output)
- ✅ Deterministic (no wall-clock, bounded poll, JSON sort_keys)

The response-shape assumptions are live-pending but mitigated by mocked transport testing and clear isolation points for live adjustment.

## Ready for Implementation

The Generator can implement with confidence. Every gate clause is runnable and verifiable.
