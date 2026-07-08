VERDICT: PASS
SCORE: 4.7
BLOCKERS: 0
HIGH: 0

# Findings — Sprint 002: Publish gate + QUEUE schema + idempotent enqueue

Non-UI CLI/library deliverable. Verification is exact CLI invocations, exit codes,
stderr/stdout substrings, and on-disk JSON assertions (no Playwright). The
Evaluator independently reproduced every contract behavior against the live CLI.

## Result summary

All ten §9 adversarial probes and all ten §9 fixture-table rows reproduce the
contract's pinned behavior exactly. 95 unit tests pass (35 Sprint-001 + 60
Sprint-002; 60 test methods across the four Sprint-002 test files). No Blocker,
High, Medium, or Low findings affecting the sprint's Definition of Done.

## Evidence (independently reproduced by the Evaluator)

- Unit tests: `python3 -m unittest discover -s tools/marketing-loops/tests` ->
  Ran 95 tests ... OK.
- Probe 1 (real tgrera): exit 0; exactly 3 rows {instagram, linkedin, youtube},
  every row state=queued, schedule_slot/package_path/posted_date/permalink all
  null, schema_version "1", keys sorted, rows sorted by (slug, channel).
- Probe 2 (idempotency): re-run -> shasum byte-identical (a4b3e09b... twice).
- Probe 3 (no-regress): pre-seeded posted (tgrera, instagram) row with
  posted_date/permalink survives re-enqueue unchanged (state=posted, 2026-07-01,
  https://instagram.com/p/abc); action "kept-posted"; other two channels added as
  queued; 3 rows total.
- Probe 4 (real hyd refusal): exit 1; stderr cites [missing-verdict] then [killed]
  in order; the fresh --queue target file was NOT created (asserted absent).
- Probe 8 (cross-order determinism): two assets enqueued in opposite order into
  two queues -> byte-identical files (163668b2... both).
- Probe 10 (no network / no wall-clock): gate.py, queue.py, channels.py,
  enqueue.py grep-clean for datetime, requests, urlopen, socket, urllib. The only
  urllib hit in the package is urllib.parse in read-only Sprint-001 utm.py (pure
  query-string parsing, no network).
- Fixture table: missing-verdict->[missing-verdict] exit1; unparseable-verdict->
  [missing-verdict] exit1; verdict-fail->[verdict-not-pass] exit1;
  failed-checks-nonempty->[failed-checks-nonempty] exit1 (fixture has
  verdict "PASS" + one real FAIL entry, proving BOTH halves of FAIL-free PASS are
  enforced); killed->[killed] exit1; missing-verdict-and-killed->
  [missing-verdict, killed] in order exit1; unmapped-channel (Twitter)->exit2;
  no-channel (Channels: only format words)->exit2; pass-one-channel->exit0 (1 row);
  pass-three-channels->exit0 (3 rows). Every refusal/usage case wrote nothing.
- Usage errors: nonexistent asset -> exit2; malformed --week 2026-Q3 -> exit2;
  both stderr-only, no write.
- Import safety: import gate, queue, channels prints nothing;
  queue.SCHEMA_VERSION == "1"; channel set is the imported Sprint-001
  CHANNEL_SOURCE_MAP keys {instagram, linkedin, youtube} -- no forked copy.
- Default-path hygiene: content/publish-queue.json absent after all probes.

## Non-blocking observations (recorded, not findings -- no fix required)

1. Check ordering vs §3.3 "Gate first" (Process, informational). enqueue.py
   validates --week format and asset-existence (both exit-2 preconditions) before
   running the gate. Consistent with §3.1 (asset precondition is exit 2, distinct
   from a domain refusal) and §3.6 (malformed --week is an unconditional exit-2
   usage error). The gate still precedes channel-parsing and any queue write.
   Consequence: a KILLED asset with a malformed --week returns exit 2 (week), not
   exit 1 (gate). No §9 probe combines these; the contract does not pin the
   precondition-vs-gate order. Defensible, disclosed -- not a defect.

2. queue.py shadows stdlib queue (Craft, informational). Module name matches
   stdlib queue, resolved via sys.path.insert(0, _HERE). It is the name the
   contract suggested (§2); no code in the package uses stdlib queue, so no real
   collision. Cosmetic risk only.

3. Connector-word strictness (Craft, informational). A hypothetical
   "Channels: IG and LinkedIn" would surface "and" as unmapped -> exit 2, since
   §3.5 pins the format-word set and gives no rule for arbitrary non-platform
   tokens. This is the conservative, spec-aligned choice ("surfaced, not guessed",
   A-7) and never silently drops a token. Real assets and all fixtures use only
   aliases/format-words/punctuation, so this path is untriggered by real content.

None rise to a Low finding; each is contract-sanctioned or has zero effect on real
assets and the Definition of Done.

## Trace review

generator_trace.log is thorough and honest: it logs the exact verification
commands, before/after shasum for idempotency, the [missing-verdict, killed]
ordering for real hyd, the no-write-on-refusal confirmation (including the
"not created" half against a non-existent --queue path), and pre-discloses the
three observations above as resolved ambiguities. No skipped failures, no claims
without artifacts, no broad rewrites after small findings.

## Scoring (infrastructure weighting -- Functionality + Evidence emphasized)

- Functionality: 5 -- every gate condition, exit code, idempotency, and no-regress
  behavior works exactly as pinned.
- Evidence/process: 5 -- every claim independently reproduced via the live CLI,
  not just the test suite; byte-identical shasums verified.
- Craft: 5 -- pure functions, deterministic serialization (sort_keys, indent=2,
  single trailing newline), single-source-of-truth channel map, no import side
  effects, untrusted-input hardening (corrupt verdict -> refusal, never a crash).
- Design (schema/seam): 5 -- versioned QUEUE with a documented {queued, posted}
  API seam and nullable lifecycle fields whose deferral is explicitly justified.
- Originality: 4 -- infra sprint; the state-machine seam design is thoughtful.

Weighted total ~= 4.7. No blockers, no high findings, evidence >= 4,
functionality >= 4, weighted >= 4 -> PASS.

## Definition of Done -- verified

- gate_asset() importable, pure, four exact reason codes, terminal/independent
  structure, no import side effects -- VERIFIED.
- queue.py versioned schema, deterministic ordering + serialization,
  SCHEMA_VERSION declared once -- VERIFIED.
- channels.py alias table, dedup, format-word tolerance, unmapped-token surfacing,
  empty->exit-2 -- VERIFIED.
- enqueue.py gate->refuse(1)/usage(2)/enqueue(0), idempotent + no-regress,
  deterministic JSON -- VERIFIED.
- Fixtures for every §9 row shipped under fixtures/publish/ -- VERIFIED.
- Unit tests prove each reason code, multi-reason order, channel parsing
  (tgrera->3), idempotency, no-regress, three exit codes; all 95 pass -- VERIFIED.
- Real tgrera enqueues exit 0 with 3 correct rows; real hyd refused exit 1 with
  [missing-verdict, killed] and no write -- VERIFIED.
- Evidence logged in generator_trace.log -- VERIFIED.
