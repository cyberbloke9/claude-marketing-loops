VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Summary

Sprint 004's LinkedIn adapter contract is exceptionally well-specified, testable, and resistant to gaming. The contract achieves this through:

1. **Ground truth anchored:** All API facts derived from RESEARCH.md (R4-B4, R5-5/R5-6), not invented
2. **Anti-stub enforcement:** §1.1 + §8.4 require `plan_steps` and `execute` derive from a SINGLE flow definition; parity test proves both paths emit identical call sequences
3. **Exact verification commands:** §11 provides 9 gate clauses with executable steps and concrete expected outputs
4. **Determinism proven:** Byte-identical `publish-plan.json` on repeat runs (no wall-clock)
5. **Exact stdout template:** §6.1 specifies the exact 3-step document block for direct byte comparison
6. **Secrets redaction proven:** §8.9 asserts sentinel token absent from all output
7. **Conscious sprint-003 updates enumerated:** §7 lists exact line numbers and test names requiring updates; §7.1 specifies seed extension

## Strengths

**Specification clarity:**
- Exact HTTP endpoints, methods, URLs, and payload structures (§4.1–§4.3)
- All 7 steps for both flows specified in table format with exact headers/params/payloads
- Named placeholders for dependent values fully enumerated (§4.5)
- Document flow: 3 steps; MultiImage: 7 steps (for N=3)

**Testability:**
- 11 gate clauses (§11) with reproducible CLI commands and deterministic expected outputs
- Unit test scenarios detailed across §8.1–§8.11 (dry-run fidelity, execute happy paths, preconditions, regression, redaction, etc.)
- Parity test (§8.4) compares plan-steps against mock transport calls to prove shared-flow guarantee
- IG regression guard explicit (§8.7): asserts IG tests byte-identical after generalization

**Anti-gaming:**
- The shared-flow requirement (§1.1) + parity test makes stub implementations impossible (dry-run plan must be produced by exact same adapter code live execution walks)
- Stdout template byte-match (§6.1) prevents fabricated output
- Determinism requirement (B9, §9) prevents clock-based cheating
- Precondition errors specified to exact messages (§3.1, exit 2 cited)

**Safety and non-goals:**
- Clear statement of what is NOT in this sprint (§14): no live posting, no Facebook, no carousel post type, no company-page posting
- Live no-op honest (§1.2): `--live` linkedin row makes ZERO network calls, invents no permalink, writes no queue
- `_drive_execute` generalization (§5.3) specified with regression guard: IG tests must remain byte-identical

**Edge cases and error handling:**
- Missing/unreadable manifest → exit 2, cited (§3.1)
- Missing pdf field in manifest → exit 2, cited
- 0 attachments (MultiImage) → exit 2, cited
- >20 attachments → exit 2, cited (LinkedIn's API limit)
- Unexpected response shape (missing uploadUrl/URN) → `AdapterRefusal` exit 1, cited (§5.1)
- Empty response body on PUT upload → tolerated, fed {} to generator (§5.3)

**Determinism and secrets:**
- No wall-clock reads; all dates from `--week`/`--date` args (§9)
- `LinkedIn-Version` a FIXED constant "202506", never wall-clock-derived (§4.4)
- Access token NEVER in stdout/JSON; Bearer <REDACTED> at every site (§8.9 proves)
- Person URN `<LI_PERSON_URN>` rendered as placeholder in dry-run (no .env loaded) (§9)

## Acceptance Criteria Met

**§15 Acceptance summary — all 7 conditions specified and testable:**

1. Dry-run document flow: 3-step sequence with versioned headers, payload, dependent-value placeholders, redacted token, constructed permalink (no 4th fetch call). Stdout matches §6.1 byte-for-byte. Machine JSON deterministic. Queue unchanged. Zero network. ✓

2. MultiImage flow: 7 steps, exactly one flow per row, no cross-contamination, never a carousel post type. ✓

3. Execute shared flow: both happy paths return constructed permalink; unexpected response → AdapterRefusal (exit 1); precondition failures → AdapterUsageError (exit 2); parity test proves identical call sequences. ✓

4. Driver generalization: sends real bodies (JSON/file bytes), tolerates empty upload responses, IG execute + all IG tests byte-identical. Conditional headers/payload render leaves IG stdout block unchanged. ✓

5. Live no-op: exit 0, honest "nothing posted" notice, no fake permalink, queue unchanged, no secrets echoed. ✓

6. Secrets: no token value in output; `Bearer <REDACTED>` at render sites; person URN as placeholder. Determinism: no wall-clock; version fixed. ✓

7. Both full suites GREEN; Sprint-003 linkedin assertions consciously updated (enumerated in §7); facebook row preserved; transport seam unchanged (1 urlopen). ✓

## No Vagueness or Ambiguity

**Resolved potential concerns:**

- **"Live-pending" fields (§4.3):** Marked as unverified but included for fidelity. Tests do NOT hard-assert exact structure beyond presence, allowing founder correction without breaking determinism. Documented as RISK §10.1. ✓

- **Manifest and attachment file existence:** Gate clause 0 (precondition check in §11) skips gates 3–6 if carousel.pdf or manifest missing. Reasonable fallback; contract acknowledges. ✓

- **Payload rendering with non-ASCII (em-dash):** Handled explicitly (§6, BUILD assertion): use `json.dumps(..., ensure_ascii=True)` which encodes em-dash as `\uXXXX` both in stdout and machine JSON. Tests must produce expected string via identical `json.dumps` call, not hand-typed. Clear and prevents typos. ✓

- **Seeded attachment filenames:** Not explicitly listed, but contract says "read the existing IG fixtures" pattern. The real asset `2026-07-09-anarock-vs-propequity` defines the attachments; tests seed matching files. Implicit but testable. ✓

- **The six 4.4/RISK assumptions:** LinkedIn-Version pinned to "202506" is a fixed assumption (documented RISK). LinkedIn requires YYYYMM format; exact accepted value is a founder/live concern only. Determinism is maintained by fixing the constant. Mitigated. ✓

## Regression Surface Clear

§7 enumerate all known breakage sites:
1. Two-row plan assertion: instagram unchanged, linkedin tuple updates from (slug, "linkedin", 0) → (slug, "linkedin", 3)
2. Stdout template: instagram block byte-identical, linkedin block becomes exact §6.1
3. Other linkedin assertions around L698–700

No ambiguity; tests are explicit.

## No Missing Sections

- Routes/endpoints: fully specified (§4.1–§4.3, absolute URLs)
- Click paths: N/A — no browser surface (§13); CLI only
- Pass/fail conditions: exit codes mapped (0/1/2), expected messages cited
- Empty/loading/error/invalid states: §10 (States that must exist) + §3.1 (Preconditions)
- Keyboard/focus/ARIA: N/A — no UI (§13)
- Responsive: N/A — CLI + JSON output
- Real data: uses real frozen asset `2026-07-09-anarock-vs-propequity`
- Verification commands: §11 provides 9 executable gate clauses
- Explicit non-goals: §14 lists 10 items not in this sprint

## Security and Process

- `.env` stays gitignored; never written to tracked files (§12)
- No tokens in stdout/JSON (§8.9 proves)
- Only write is `content/publish-plan.json` (dry-run); queue not written (§12)
- File hygiene checked: git status must show only modified .py files + untracked plan.json (§11 gate 9)

## Backward Compatibility

- `run()`/`main()` gain only `--linkedin-version` keyword (default "202506") — backward-compatible ✓
- `Transport`/`Response`/`RecordingTransport`/`RaisingTransport`/plan-envelope/7-step-key unchanged (§14 ✗ bullet 9) ✓
- `_drive_execute` generalized safely: IG steps have `upload_path=None`, `payload=None` → no body sent, no empty-response branch taken; IG behavior unchanged (§5.3) ✓

## Conclusion

This contract is **ready to build.** It specifies the LinkedIn adapter with sufficient precision, fidelity to verified API docs, test scenarios, regression guards, and executable verification that a builder cannot accidentally pass without implementing the actual two flows faithfully.

The use of ground-truth anchoring (RESEARCH.md), anti-stub enforcement (parity test), and exact determinism (byte-identical JSON, no wall-clock) makes the contract resistant to gaming while remaining clear and testable.

**ACCEPT as written.**
