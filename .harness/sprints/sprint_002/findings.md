VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Sprint 002 Findings — Transport seam + dry-run plan renderer + CLI skeleton

Evaluated tools/marketing-loops/publish_api.py + tests/test_publish_api.py against
sprints/sprint_002/contract.md (14 sections, 11 gate clauses) and spec §11 Sprint
002. Stdlib CLI + JSON tool — no browser surface (contract §11 Playwright N/A).
Verification was behavioral: every gate clause was run from a clean state.

## Evidence — every gate clause reproduced

| Gate | Result | Evidence |
|---|---|---|
| 1 new suite | PASS | Ran 39 tests OK |
| 2 full suite (no regression) | PASS | Ran 310 tests OK (271 prior + 39) |
| 3 dry-run real asset | PASS | exit 0; plan mode=dry-run, 2 rows (…,instagram,0)(…,linkedin,0); QUEUE-UNCHANGED; stdout matches frozen template line-for-line |
| 4 determinism | PASS | DETERMINISTIC (byte-identical plan on repeat) |
| 5 empty scope | PASS | --week 2026-W01 -> exit 0, "nothing queued for 2026-W01", PLAN-UNCHANGED |
| 6 malformed input | PASS | bad-week / unknown-channel / both-modes / bad-date / bad-li-type / max-per-day 0 / missing-week each exit 2, all cited |
| 7 live no creds | PASS | exit 2; all four preconditions (date, env, base-url, ack) cited INDEPENDENTLY; no token echoed |
| 8 live PASS no adapter | PASS | exit 0; stdout 0 bytes; SENTINEL count 0; "nothing posted" notice on stderr only; QUEUE-UNCHANGED |
| 9 AST no-network | PASS | exactly 1 urlopen call site, inside Transport |
| 10 import silence / stdlib | PASS | import-ok-silent, stdlib only |
| 11 hygiene | PASS | .gitignore has content/publish-plan.json; git status shows only the two new files — no .env, no plan artifact staged |

## Adversarial probes (beyond the gate list)

- In-scope token gating (F-005). --channel linkedin --live with LI-only env -> exit 0
  (no spurious IG demand). --channel instagram --live with same env -> exit 2 citing
  exactly IG_ACCESS_TOKEN, IG_USER_ID. Keyed on post-filter row set, not VALID_CHANNELS.
- Empty-before-gate ordering. --week 2026-W01 --live (no creds) -> exit 0 "nothing
  queued", NOT a gate failure. Correct precedence.
- Package validation (B4, §5.1a). Nonexistent package -> exit 2 "package not found";
  malformed-JSON package -> exit 2 "is not valid JSON". Existence+parseability only.
- .env parser (frozen worked cases). FOO=bar->bar; FOO="bar baz"->bar baz;
  FOO=bar # note->bar; FOO=->""; FOO=bar baz->bar baz; no-= line -> cited ".env line 1
  is not KEY=VALUE" (no value echoed). Matches the frozen table exactly.
- Secret discipline. Sentinel token in .env, gate passed; sentinel absent from stdout,
  stderr, and publish-plan.json (count 0).

## Trace review

generator_trace.log consistent with disk. Disclosed judgment calls (empty-scope
no-write, existence-only package validation, live honest no-op, all-preconditions-
cited) match the accepted contract and were independently reproduced. Note-1
(Gate-8 "posted" substring in the no-op notice) is a non-issue: STDOUT is empty
(0 bytes); the notice is a stderr diagnostic. No skipped failures, no claims
without artifacts.

## Scoring

- Functionality 5 — all in-scope behavior works; [P] flags parsed AND validated.
- Design (legibility) 5 — stdout matches frozen template byte-for-byte; machine plan stable-sorted.
- Craft 5 — single urlopen seam (AST-proven); clean run/main split; honest no-op not fake success.
- Originality 4 — CLI skeleton; correctness/fidelity axis met.
- Evidence/process 5 — all 11 gates + 5 adversarial probes reproduced from clean state.

Weighted total ~4.8. No blockers, no High findings. Functionality and Evidence both >= 4.

## Scope boundary honored

Adapter registry ships EMPTY (steps: []); no /media, /rest/*, /photos, /feed; no live
posting / queue transition / day-cap / facebook-skip (deferred to 003-006); no frozen-
module edits, no existing-test edits. Forward-frozen run()/main() + Response/Transport
shapes in place for 003+.

PASS.
