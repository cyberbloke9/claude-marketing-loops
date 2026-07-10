VERDICT: PASS
SCORE: 4.7
BLOCKERS: 0
HIGH: 0

## Summary

Sprint 006 turns the previously CLI-unreachable adapter `execute()` flows into a
real `--live` path and makes the queue transition real, reusing the frozen
`mark_posted.transition`. Verified behavior, not claims: full suite green (386
tests, 0 skips), the real-asset CLI dry-run reproduces the promised 2-row fidelity,
and the live path is exercised via injected mock/recording transports whose
assertions touch on-disk queue state (not just exit codes).

Playwright: N/A - stdlib CLI + JSON tool, no browser surface (contract 13, spec 13).
Verification vehicle is unittest + CLI probes (11).

### Evidence - reproduced independently

- Gate 1 (regression): `unittest discover -s tools/marketing-loops/tests` -> Ran 386
  tests OK, 0 failures / 0 errors / 0 skips.
- Gate 7 (real-asset dry-run, DEFAULT): `publish_api.py --week 2026-W28` -> exit 0;
  publish-plan.json mode dry-run, exactly 2 rows for 2026-07-09-anarock-vs-propequity
  in (slug, channel) order - instagram 8 steps, linkedin 3 steps. Empty stderr.
- Gate 8 (determinism): two consecutive dry-runs -> publish-plan.json BYTE-IDENTICAL.
- Queue untouched by dry-run: both W28 rows remain queued after all probes.
- Secrets: no non-redacted access_token/Bearer value in the plan; .env and
  content/publish-plan.json both gitignored; no .env present on disk.
- Single seam (B38): urllib.request.urlopen at exactly one call site (Transport.request).
- Gate 10 (live gate exit 2): `--live --week 2026-W28 --date 2026-07-09` no creds ->
  exit 2, all three preconditions cited independently; queue unchanged.
- Malformed --week -> exit 2 cited; empty scope (2026-W01) -> exit 0 "nothing queued".

### Live path is real, not a stub (code inspection + tests)

- _run_live (publish_api.py:1308) calls adapter.execute(row, package, ctx, transport)
  against the injected transport, transitions via the imported frozen
  mark_posted.transition (line 1363; NOT reimplemented), and writes the queue
  INCREMENTALLY per successful row (queue.write_queue, line 1373). The Sprint-005
  honest no-op live branch is gone.
- Day-cap (B16): single baseline (posted rows with posted_date == --date) + run
  counter; breaching row refused exit 1 cited (day-cap); processing stops.
- Targeted already-posted refusal (4.1) fires only when BOTH --slug and --channel
  pin one posted row (line 1483) - the discriminator reconciling Gate 3 (exit 1)
  with Gate 4 (broad re-run exit 0).

### Test quality - substantive, not hollow

All 19 section-12 scenarios exist by name (grep count = 19), including the
previously-contested discriminator test_live_rerun_fully_posted_week_exit0 (12.1b,
line 1904). The two subtlest "prior posts stand" laws are pinned by tests that
re-read the queue file from disk:
- test_live_daycap_breach_refusal_prior_stand (line 1993-1995): IG posted + LI
  queued on disk + only 8 wire calls.
- test_live_incremental_write_prior_posts_persist (line 2076-2077): row-2 refusal
  leaves row-1 posted on disk, row-2 queued.
- Happy path (line 1942-1954): both rows flip to posted with posted_date + platform
  permalink, exact transport call order, no publish-plan.json written.

Live-path evidence is honestly "test suite + code inspection" - a full live CLI run
would require a real socket, and main() deliberately never injects a transport
(contract 9), so a mock-transport test through run() is the correct, complete vehicle.

## Finding F-001: Multi-image live path resolves attachment paths against CWD

Severity: Low
Category: Process
Status: Informational (does not block)

### Contract Clause
4.4 / disclosed risk (trace 2026-07-10 00:05): _required_upload_paths returns
package["attachments"] verbatim for the LinkedIn MultiImage live path; those are
repo-relative, so a multi-image live run via run() resolves them against CWD.

### Reproduction Steps
Not reachable by any Sprint-006 gate. LinkedIn default post-type is document
(absolute PDF via render/manifest.json), which every test and Gate 7 exercise. No
gate runs multi-image live.

### Expected / Actual
Expected: documented for the future. Actual: correctly disclosed by the Generator;
no in-scope behavior depends on it.

### Required Fix
None this sprint. Flag for Sprint 007+ if multi-image live is wired to the CLI as a
default (resolve attachment paths relative to repo root / package dir, not CWD).

### Pass Condition
Already satisfied - informational; recorded so it is not silently dropped.

## Scoring

- Functionality: 5 - all gates, exit-code mapping (0/1/2), transition, day-cap,
  incremental persistence, FB gating verified.
- Evidence/process: 5 - CLI probes reproduce claims; disk-state assertions; no
  skips; no stubs; frozen mark_posted.transition genuinely reused.
- Craft: 5 - single urlopen seam; incremental write-before-advance; no wall-clock;
  deterministic serialization.
- Design (output legibility/safety): 4.5 - faithful inspectable plan; cited
  refusals; visible redaction.
- Originality (faithful API transcript vs slop): 4.5 - no invented endpoints.

Weights (systems/infra CLI): Functionality 25%, Evidence 25%, Craft 20%, Design 15%,
Originality 15%. Weighted total ~= 4.7. No blockers, no high; evidence >= 4,
functionality >= 4.
