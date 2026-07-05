VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Findings — Sprint 006: Cross-gap acceptance runner + adversarial suite + README rollout

## Verdict summary

Headless CLI + fixture deliverable (contract §intro: no routes/screens/DOM/Playwright).
Verification is CLI invocation + exit codes + cited-reason substrings + byte-golden Markdown +
path-independent JSON invariants. Every contract §8 command and §9 attack was reproduced
independently by the Evaluator. The runner is a genuine adversarial gate, not a rubber stamp.

## Evidence log (all reproduced by the Evaluator, not taken from the trace)

| Check | Contract ref | Result |
|---|---|---|
| acceptance.py runs clean | §3.1 | ACCEPTANCE: PASS (50/50 expectations met), exit 0 |
| Repo not dirtied by a run | §3.2, §9.9 | git status --porcelain: no content/publish-queue.json, no real content/*/publish/, no new metrics/* |
| Full unit suite green | §8.3 | Ran 254 tests OK (contract expects > 233) |
| Renderer acceptance untouched | §8.4, §9.10 | tools/marketing-render/acceptance.py --checked-on 2026-07-04 -> ACCEPTANCE: PASS (14/14), exit 0 |
| Hygiene: no network / no wall-clock | §5, §8.5, §9.12 | grep for datetime/requests/urlopen/socket/http.client/urllib.request on acceptance.py -> clean; datetime/time. -> clean |
| Imports stdlib + one disclosed frozen read | §5 | argparse/json/shutil/subprocess/sys/tempfile/pathlib + import schedule (disclosed read-only for the seam constant) |
| Frozen integrity — no Sprint 001-005 .py edited | §2 (mtime+content) | mtime sweep: acceptance.py alone at 2026-07-05 15:45 (Sprint-006 build); all frozen modules predate it. Only acceptance.py + test_acceptance.py are new. |

### Adversarial probes (contract §9 — Evaluator-run negative controls)

- §9.1 Honest failure. Appended CORRUPTED_LINE to fixtures/metrics/expected/full.md ->
  ACCEPTANCE: FAIL (49/50) — first unmet: metrics/full — scorecard differs from golden
  (2693 vs 2709 bytes), exit 1, cited the specific row. Restored -> PASS. Not a rubber stamp.
- §9.2 Cited reason, not "some FAIL". Each refusal row met on its named substring
  (killed -> [killed], verdict-fail -> [verdict-not-pass], unknown-source -> utm_source was 'tiktok').
- §9.3 No-write on refusal. Every gate/package refusal prints no-write-on-refusal confirmed / no package written.
- §9.4 No-scorecard on corrupt CSV. truncated/wrong-header/wrong-colcount/non-numeric/blank-join -> exit 2, no scorecard.
- §9.5 No partial-sum leak. metrics/wrr-partial byte-equals its golden (Sprint-005-proven to omit 147/252/295).
- §9.6 Seam is genuine (load-bearing). Built queue+packages for real TGRERA into a temp dir, mutated the
  instagram schedule_slot from 2026-W27/evening/18:00 to 2026-W27/morning/09:00, re-ran scorecard.py;
  the A/B table moved instagram's 51 clicks from Evening to the Morning column. Scorecard genuinely
  consumes the publish layer's generated queue slot. Code path: run_chain reads ig_slot from generated
  chain-q.json (acceptance.py:619-620), asserts via seam_ab_ok (302-317), not from slot_for.
- §9.7 Idempotency + no regression. chain/idempotency — 3 rows on re-run, instagram stays posted.
- §9.8 Table coverage. Created stray fixtures/publish/stray-xyz -> ACCEPTANCE: FAIL (table coverage
  incomplete) … not named by any table row: ['stray-xyz'], exit 1. Removed -> PASS.
- §9.11 README honesty. [x] Phase 0 — analytics plumbing (UTM verifier + publish layer + weekly
  scorecard compiler); dashboards (a non-goal) NOT claimed; no production-ready language;
  documented commands reproduce (verify_utm.py content -> exit 0, OK both real assets).
- Determinism (§3.1, §5). Two full runs byte-identical (diff empty); --verbose determinism fixed in-sprint.

## Scoring (systems/infrastructure weighting: Functionality + Evidence emphasized)

- Functionality: 5 — runner + five frozen CLIs behave exactly as contracted; cross-gap seam works end-to-end.
- Evidence/process: 5 — every claim independently reproduced incl. honest-failure, seam-mutation, coverage-gap negative controls.
- Craft: 5 — pure stdlib, single disclosed read-only frozen import, deterministic, principled path-independent-vs-byte-golden split documented in module docstring.
- Design (schema/seam integrity): 5 — QUEUE-as-API-seam consumed correctly; A/B bucket driven by generated queue, not a fixture.
- Originality: 4.5 — cited-reason normative table + coverage guard + path-independence reasoning is thoughtful adversarial design.

Weighted total ~= 4.8. No blockers, no high findings. Evidence >= 4 and Functionality >= 4 satisfied.

## Notes (non-blocking, informational)

- N-1: The tools/marketing-loops/ tree is untracked in git (sprint work not committed). Did not affect
  evaluation — code present and verified on disk; frozen integrity confirmed by mtime. A commit, if the
  harness expects one, is a process step outside this sprint's contract scope, not a deliverable defect.
- N-2: Extra on-disk fixtures beyond the contract's illustrative table (blank-cell, zero-cell, header-only,
  blank-join, pkg-multi-surface, pkg-per-channel-caption) are each named by real expectation-table rows
  with genuine assertions; coverage stays exact (verified by runner + §9.8 stray-fixture probe).

## Pass condition (met)

python3 tools/marketing-loops/acceptance.py exits 0 with ACCEPTANCE: PASS (50/50); the runner honestly
fails on a corrupted golden, a wrong-reason refusal, and a stray/removed fixture; the cross-gap seam is
proven load-bearing by slot mutation; no frozen Sprint 001-005 module was edited; the 254-test suite and
renderer acceptance both stay green; the repo is not dirtied; README Phase-0 box checked without
over-claim. All satisfied.
