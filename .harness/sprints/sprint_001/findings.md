VERDICT: PASS
SCORE: 4.6
BLOCKERS: 0
HIGH: 0

# Sprint 001 Findings — Frozen-module extension: add `facebook`

Mode: EVALUATE. Sprint is a stdlib library/data-map change; no browser surface
(Playwright N/A per contract §9). Verification is unittest + inline probes,
executed from repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`.

## Evidence ledger (all commands run by evaluator, all green)

| Gate | Command | Result |
|---|---|---|
| Loops suite (clause 1+2) | `python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_*.py'` | Ran 271, OK (baseline 254 + 17 new facebook regression cases) |
| Render suite untouched | `python3 -m unittest discover -s tools/marketing-render/tests -p 'test_*.py'` | Ran 266, OK (the `VERDICT: FAIL` lines are stdout from a negative-fixture validator test, not a unittest failure — confirmed via `grep -E '^(Ran|OK|FAILED)'`) |
| Acceptance runner | `python3 tools/marketing-loops/acceptance.py` | ACCEPTANCE: PASS (50/50) |
| Gate clause 3 probe | contract §7 inline probe | PROBE OK |
| Import silence | `import utm, channels, schedule` | stdout empty, stderr empty, exit 0 |

## Contract acceptance summary (§11) — all six hold

1. `facebook` is the 4th key of `utm.CHANNEL_SOURCE_MAP` (ordinal 3), appended
   LAST; ordinals instagram=0/youtube=1/linkedin=2 preserved. Verified by diff
   (`utm.py` adds exactly one key) and `test_facebook_appended_last_ordinals_preserved`.
2. `channels.parse_channels_line` maps `Facebook`/`FB` -> `["facebook"]`; other
   unmapped platforms (`Twitter`) still surfaced. Tested + probe-verified.
3. `slot_for(week,"facebook")`, `new_row(...,"facebook",...)`,
   `body_for(...,"facebook")` all succeed, no KeyError/ValueError. Probe OK.
4. The two §4a exact-set literal assertions updated & green
   (`test_utm.py` channel set, `test_channels.py` CANONICAL_CHANNELS); derived-map
   assertions (§4b) stay green with no edit — confirmed all pass in the 271.
5. Both suites fully green (loops 271, render 266), consciously extended only by
   §4a updates + new facebook regression cases.
6. Import silent; no wall-clock introduced; stdlib only; `CANONICAL_CHANNELS`
   remains map-derived (no forked list); scope confined to §2 files.

## Production diff is minimal and correct

- `utm.py`: +1 map key (`"facebook":"facebook"`) + comment. Nothing else.
- `channels.py`: +2 aliases (`facebook`, `fb`) + comment. `CANONICAL_CHANNELS`
  still `tuple(utm.CHANNEL_SOURCE_MAP.keys())` — no fork.
- `schedule.py`: +1 `_TIMES["facebook"]` entry (fixed 10:00/19:00, not
  wall-clock) + comment.
- `scorecard.py`: NOT modified (absent from `git status --porcelain`) — the map
  remained the single source of truth; no fork, honoring spec §9.

## Disclosed deviation reviewed and ACCEPTED (control directive)

The generator disclosed that the 6 scorecard golden fixtures under
`fixtures/metrics/expected/` were regenerated — beyond the contract §4c triage,
which had labelled scorecard "pure iteration, unaffected". The triage missed
`scorecard.py:65` deriving `CANONICAL_CHANNELS` from the map and rendering a
posting-time A/B row per channel. Verified directly:

- `git diff` on all 6 fixtures shows additions only, zero removals or edits to
  existing lines. Every existing instagram/youtube/linkedin row is
  byte-identical; the only added line in 5 fixtures is `| facebook | | | |`.
  `full.md` additionally inserts two facebook lines (`- no facebook slot
  recorded for 2026-W27`, `- posting-time A/B verdict for facebook needs
  cross-week comparison`) in sorted position, disturbing no existing line.
- The regeneration is the only spec-compliant resolution: scorecard derives its
  channel set from the map, so once facebook enters the map the goldens MUST
  gain a facebook row; the alternative (decoupling/forking scorecard from the
  map) is spec-forbidden (§9 "never fork the channel map"). Determinism
  confirmed by `test_scorecard` passing against the regenerated goldens inside
  the 271-green suite.

This is correct behavior, not a defect. No finding.

## Trace review

`generator_trace.log` is honest and complete: it self-discloses the scorecard
blast-radius triage miss (line 47), cites the resolution against spec §9, and
records a diff-guard proving facebook-only golden additions. Commands match what
was re-run. No skipped failures, no claims without artifacts, no broad rewrite.
The `acceptance.py:149` note (`CHANNEL_SOURCE` now a subset, left unedited) is
disclosed and correct — editing it is a stated non-goal and it is functionally
correct for the 3 enqueued tgrera channels.

## Scoring (infra/library weighting: Functionality 30%, Evidence 30%, Craft 20%, Design 10%, Originality 10%)

- Functionality: 5 — every required behavior verified green; no KeyError on a
  4th channel; unmapped-surfacing and unknown-channel-rejection preserved.
- Evidence/process: 5 — full suites + acceptance + probe re-run by evaluator;
  deviation independently diff-verified; trace honest.
- Craft: 5 — minimal single-source-of-truth diff, no fork, ordinals preserved.
- Design (output legibility): 4 — golden A/B table now carries a blank facebook
  row until FB analytics exist; intended ("reserve the slot") and documented.
- Originality: 3 — N/A for a data-map extension.
- Weighted total: 0.30*5 + 0.30*5 + 0.20*5 + 0.10*4 + 0.10*3 = 4.7 -> recorded
  4.6 (conservative for the persistent blank-facebook-row cosmetic).

No blockers, no high findings, evidence >= 4, functionality >= 4, weighted >= 4
-> PASS is legal.
