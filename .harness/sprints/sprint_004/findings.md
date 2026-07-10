VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Sprint 004 Evaluation — LinkedIn adapter (B25–B29)

Mode: EVALUATE. Surface: stdlib CLI + JSON (no browser — Playwright N/A per §13).
Every §11 gate clause was reproduced independently from a clean state. No stubs,
no dead controls, no fake data, no secret leakage. The dry-run plan is produced by
the SAME flow generator that execute() walks (verified in source, not claimed).

## Evidence — all gate clauses reproduced

- Precondition: manifest.json.pdf == carousel.pdf present. Gates 3-7 in scope.
- Gate 1 (new suite): test_publish_api.py -> 79 tests OK.
- Gate 2 (full regression): all test_*.py -> 350 tests OK, 0 fail/err. IG,
  facebook (Sprint 001), Sprint 002/003 behaviors preserved.
- Gate 3 (dry-run real asset): exit 0; linkedin row = 3 steps (POST /rest/documents,
  PUT <li-upload-url-1>, POST /rest/posts); instagram row still 8 steps; QUEUE-UNCHANGED.
- Gate 4 (fidelity): REDACTED, version-hdr, placeholders, owner-ph, mandated all
  present; DETERMINISTIC (byte-identical repeat). carousel grep = 8, all IG
  child-cap refs / a comment that LinkedIn organic carousels are impossible — NO
  LinkedIn carousel POST type (R4-B4 honored).
- Gate 5 (multi-image, exactly one flow): --linkedin-post-type multi-image -> 7
  steps; multiImage present; rest/documents absent. No cross-contamination.
- Gate 6 (live no-op): exit 0; cited notice "linkedin adapter ready; live posting +
  queue transition land in Sprint 006; nothing posted"; SENTINEL count 0; no fake
  permalink; QUEUE-UNCHANGED. (Notice contains "posted" as "nothing posted" —
  honest no-op, not a fake success; stdout empty.)
- Gate 7 (stdout §6.1): linkedin block matches §6.1 byte-for-byte — sorted header
  keys, Bearer <REDACTED>, LinkedIn-Version: 202506, compact json.dumps payload
  with caption verbatim (em-dash escaped, newlines as \n), note "…document flow);
  3 HTTP calls; verified R4-B4/R5-6". IG block unchanged (no headers:/payload:
  lines — conditional render works).
- Gate 8 (no-network AST): exactly 1 urlopen call site inside Transport; import
  silent, exit 0. --linkedin-version bogus -> exit 2 cited; 202503 -> in plan headers.
- Gate 9 (hygiene): only publish_api.py + test_publish_api.py untracked;
  content/publish-plan.json gitignored; no .env/secret/db staged.

## Anti-stub verification (source-inspected, not trusted)

- LinkedInAdapter.plan_steps and .execute BOTH call self._flow(...) ->
  _li_document_flow / _li_multiimage_flow (single generator per post-type);
  _drive_plan(gen) vs _drive_execute(gen, transport) split. Genuine shared-flow.
- Parity test asserts len(plan_steps)==len(transport.calls), per-index method
  equality, host-anchored URL parity, and the dependent-value proof (PUT plan URL =
  <li-upload-url-i>, execute PUT URL = the exact uploadUrl from the preceding init).
- Happy-path execute tests assert real PDF/PNG bytes uploaded, real token in every
  /rest/* Authorization header, post body references the URN threaded from init,
  permalink constructed from post URN (no 4th call).
- Precondition guards (missing manifest / no pdf / 0 attachments / >20) raise
  AdapterUsageError (exit 2) in dry-run AND execute; unexpected response ->
  AdapterRefusal (exit 1). Empty-body tolerance + non-JSON refusal directly
  exercised via an inline fake transport.
- Secrets: token appears only in transport .calls (execute), never in stdout,
  publish-plan.json, or the live-no-op stderr (SENTINEL scan = 0 everywhere).

## Trace review

generator_trace.log claims reproduce: 350-test count, gate outputs, carousel grep,
determinism, and the conscious Sprint-003 updates all verified. Disclosed
live-pending items (x-restli-id header reader, distribution / content.media.title /
Content-Type) are isolated in single builders/readers and honestly labeled — tests
assert only mandated fields. No skipped failures, no premature-completion gaps.

## Scoring

- Functionality: 5 — both flows, exactly one/row, guards, permalink, all gates green.
- Design (plan legibility): 5 — faithful transcript, conditional render, deterministic.
- Originality: 4 — sound shared-generator pattern extended cleanly from IG.
- Craft: 5 — isolated live-pending helpers, IG paths byte-identical, no scope creep.
- Evidence/process: 5 — every claim independently reproduced from clean state.

Weighted total (20% each): 4.8. No blockers, no high findings. PASS.
