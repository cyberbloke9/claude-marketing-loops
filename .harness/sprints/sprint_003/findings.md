VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Sprint 003 Findings — Instagram adapter (B19–B24)

Mode: EVALUATE. All verification run from repo root against the real asset
`2026-07-09-anarock-vs-propequity` (3 attachments confirmed). Behavior was
exercised, not claimed. No browser surface (stdlib CLI + JSON — Playwright N/A per
contract §13); verification is `unittest` + the §11 CLI probes.

## Verdict rationale — every §15 acceptance clause proven behaviorally

- **Gate 1 — new suite green:** `test_publish_api.py` → `Ran 58 tests … OK`.
- **Gate 2 — full regression green:** all suites → `Ran 329 tests … OK`. Zero failures/errors.
- **Gate 3 — dry-run real asset, 8-step IG plan:** exit 0; instagram row `steps 8`
  in the EXACT §4 order (GET content_publishing_limit; 3× POST /media child; POST
  /media parent CAROUSEL; GET /<ig-parent-creation-id>; POST /media_publish; GET
  /<ig-media-id>). `QUEUE-UNCHANGED`. Stdout byte-matches the §7.2 frozen template
  (indentation, sorted params, note line). Caption `\n`-escaped in stdout, verbatim
  in JSON.
- **Gate 4 — fidelity/secrets/determinism:** REDACTED-only-token, has-placeholders,
  base-placeholder; DETERMINISTIC (byte-identical on repeat); blacklist grep
  `media_publishing|content_publishing"` → 0; `media_publish` +
  `content_publishing_limit` present. `headers {}`, `payload null` on every IG step.
  No wall-clock (`time.time`/`datetime.now` absent; only an injectable `sleep` seam,
  never entered in dry-run).
- **Gate 5 — concrete base-url join:** →
  `https://assets.example/social-assets/2026-07-09-anarock-vs-propequity/format-01.png`.
- **Gate 6 — live no-op is HONEST:** `--live --channel instagram`, gate passing →
  exit 0; stdout 0 bytes; stderr cited notice "instagram adapter ready; … Sprint
  006; nothing posted"; SENTINEL count 0 (no secret echoed); QUEUE-UNCHANGED; no
  fabricated permalink. Posting genuinely deferred, not faked.
- **Gate 7 — no-network proof:** exactly 1 `urlopen` call site inside `Transport`;
  import silent; dry-run invokes transport zero times.
- **Gate 8 — hygiene:** `content/publish-plan.json` gitignored; no secret/artifact
  staged; new production file `publish_api.py` untracked; other modified files are
  pre-existing Sprint-001 scope.

**Shared-flow / anti-stub property (§1.1):** `plan_steps` and `execute` both derive
from the single `_ig_flow` generator. Parity + happy-carousel tests pass: 8 plan
steps == 8 transport calls, same methods/URLs; child ids threaded into parent
`children`, parent id into poll URL + `creation_id`. Container ERROR/EXPIRED and
poll-exhausted → AdapterRefusal (exit 1); rate-limit → refusal before any /media;
0/>10 attachments → AdapterUsageError (exit 2) in dry-run AND execute. All
mock-transport; no socket opened.

## Adjudication — disclosed contract-text conflict (single-image degrade)

Contract §4.2 enumerates 5 stages (`limit → create container → poll → publish →
permalink`) with an explicit "NO separate parent step", yet the parenthetical says
"(6 steps)".

**Ruling: the 5-step implementation is CORRECT; "(6 steps)" is a contract-text
arithmetic slip, not a code defect.** The prose enumerates exactly five stages and
explicitly forbids the parent for a single image. Six would require restoring the
parent (contradicts the explicit prose) or inventing a phantom call (violates spec
§7 "no invented endpoints"). Carousel = N+5 (=8 for N=3, locked by the §7.2
template); dropping the parent yields N+4 = 5. Verified: the build renders exactly
`limit → create media container → poll → publish → fetch permalink` (no
is_carousel_item, no media_type=CAROUSEL, no parent); the test asserts that exact
5-label sequence and 5 transport calls. This is the only faithful reading — no
finding raised. Contract wording should read `(5 steps)` in a future revision (see
prompt_patch_003.md) — a spec-hygiene note, not a blocker.

## Trace review

`generator_trace.log` is complete and honest: records the BUILD command, the
329/58 test counts, each gate's observed output, and proactively disclosed BOTH the
Gate-6 grep semantics (the "nothing posted" substring is the mandated stderr no-op
notice, not a fake stdout success — independently re-verified: stdout 0 bytes) AND
the single-image conflict with a reasoned justification rather than silently
picking. Response-shape parses flagged as documented live-pending assumptions
isolated in `_read_*` helpers. No skipped failures, no broad rewrite after a small
finding, no premature-completion language. Disclosures matched what I reproduced.

## Scoring

- Functionality: 5 — every §15 clause reproduced; all 8 gates green.
- Design (plan legibility/fidelity): 5 — faithful diffable transcript; §7.2 matched
  byte-for-byte; visible redaction.
- Craft: 5 — single shared `_ig_flow` generator (genuine anti-stub), typed
  exceptions, count-bounded poll, injectable sleep, determinism.
- Originality: 4 — infrastructure tool; correctness over novelty, appropriately.
- Evidence/process: 5 — thorough, honest trace; conflicts surfaced not buried.

Weighted total: **4.8**. No blockers, no high findings, evidence ≥ 4,
functionality ≥ 4, weighted ≥ 4 — PASS bar met.

## Non-goals correctly held

LinkedIn row still `steps: 0` + Sprint-004 note (byte-identical to Sprint 002);
Facebook untouched; no live posting / queue transition / write_queue / day-cap —
all correctly deferred to Sprint 006. Frozen run()/main()/Transport/Response shapes
unchanged.
