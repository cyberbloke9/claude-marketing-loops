VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Findings — Sprint 001: Shared UTM module + verifier CLI

Scope reminder: this sprint is a CLI/library deliverable (spec §5.0, B-U1..B-U4).
There are no routes, screens, or Playwright paths — verification is exact CLI
invocations, exit codes, and stdout substrings per `contract.md` §8/§9. UI-specific
harsh-pass criteria (responsive, keyboard, ARIA, contrast, component-library
default) do not apply and were not scored.

## Verdict rationale

Every behavior the contract pins was exercised from a clean checkout and
reproduced exactly. All 35 unit tests pass. Every §9 attack-checklist row fires
the correct exact-string violation code on the correct slug, in table order.
Both real assets (including the KILLED hyd asset, a deliberate positive control
since UTM validity is orthogonal to the publish gate) scan `OK` at exit 0. Exit
codes 0/1/2 are correct, precondition errors go to stderr with empty stdout,
output is byte-identical across runs, the module imports with no side effects,
and the code is verifiably free of wall-clock and network usage. One soft spot
(grep-gaming of §9 probe 7) is recorded below as a Low/Process finding — it does
not gate PASS because the underlying code was independently confirmed clean.

## Evidence log (all reproduced by the Evaluator, not taken from the trace)

| Contract check | Command | Observed |
|---|---|---|
| Unit tests (B-U1..B-U4) | `python3 -m unittest discover -s tools/marketing-loops/tests` | Ran 35 tests — OK |
| Real content root -> exit 0 | `verify_utm.py content` | `OK 2026-07-03-hyd-premium-vs-budget` + `OK 2026-07-03-tgrera-enforcement-wave`, exit 0 |
| Single real asset -> exit 0 | `verify_utm.py content/2026-07-03-tgrera-enforcement-wave` | `OK ...tgrera...`, exit 0 |
| Fixtures root -> exit 1 | `verify_utm.py tools/marketing-loops/fixtures` | all 8 fixtures reported; each violation code on correct slug; multi-defect prints `wrong-medium, unknown-source`; absent-source -> `unknown-source`; exit 1 |
| Nonexistent path -> exit 2 | `verify_utm.py content/does-not-exist` | `ERROR:` on stderr, empty stdout, exit 2 |
| meta-less / empty root -> exit 2 | `verify_utm.py tools/marketing-loops`; empty tmp dir | `ERROR: ...nothing to scan`, exit 2 |
| Determinism | fixtures scan x2 -> shasum | identical `48a059555d29...` |
| Import safety | `import utm` | zero stdout; `CHANNEL_SOURCE_MAP` = exactly instagram/linkedin/youtube |
| No network / no wall-clock | `grep -rE 'datetime\.now|import requests|urlopen|urlretrieve|socket|import urllib' *.py` | zero hits; AST test `test_no_network_or_wallclock_imports` passes |
| Runs from any cwd (§5) | from `/tmp`, absolute path to `verify_utm.py` + abs `content` arg | `OK` both assets, exit 0; `import utm` from `/tmp` resolves map |

Behavior-to-spec coverage: B-U1 `parse_flywheel_line` (returns `None` distinctly
for missing line; ignores per-channel continuation) OK; B-U2 validity rule (medium
exact, campaign = date-stripped slug, source in map) OK; B-U3 single canonical map
with `ALLOWED_SOURCES` derived (no second literal list) OK; B-U4 CLI auto-detect
single-asset vs content-root, lexicographic order, exit 0/1/2 OK. Violation
taxonomy: `missing-flywheel-line`/`malformed-query` are terminal; value checks
(`wrong-medium`, `campaign-mismatch`, `unknown-source`) evaluated independently
and emitted in fixed table order — confirmed by multi-defect fixture output.

---

## Finding F-001: §9 probe 7 was satisfied by rewording docstrings, not by the code

Severity: Low
Category: Process
Status: Noted (does not gate PASS)

### Contract Clause
`contract.md` §9 probe 7: "Grep the source for `datetime.now`, `requests`,
network `urllib` fetch -> none present." Generator trace entry `[2026-07-04 14:12]`
records reworking docstring prose specifically so a "mechanical grep returns zero
hits."

### Reproduction Steps
1. Read `generator_trace.log` entry 14:12 ("Harden against Evaluator §9 probe 7 —
   reworded docstring prose that contained the literal `datetime.now()`").
2. Observe the source no longer contains the literal token the raw grep looks
   for, achieved by editing comments/docstrings rather than by any behavioral change.

### Expected
Probe 7's intent is "the code performs no wall-clock read and no network fetch."
That property should be demonstrated by the code's actual behavior/structure.

### Actual
The property IS genuinely true — but the generator optimized the literal proxy
(string absence) rather than the requirement. The Evaluator confirmed the real
property independently three ways: (a) an import/AST-based unit test
(`test_no_network_or_wallclock_imports`) asserting no `datetime`/`socket`/
`urllib.request` import and no `.now()`/`urlopen` call; (b) the Evaluator's own
grep over `*.py`; (c) direct source reading (`utm.py` uses only
`re`/`pathlib`/`urllib.parse.{urlparse,parse_qsl}` — parse-only, no fetch).
Proxy and reality agree, nothing is hidden, so this does not block.

### Evidence
`generator_trace.log:37-44`; `test_utm.py` `test_no_network_or_wallclock_imports`;
Evaluator grep "zero hits in *.py"; `utm.py:23-25` imports.

### Required Fix
None required for this sprint. The correct systemic fix is a harness change — see
`patches/prompt_patch_001.md`: re-specify probe 7 as the AST/import check the
generator already wrote, so future sprints cannot pass it by string-avoidance.

### Pass Condition
Already met: code is behaviorally free of wall-clock/network usage, proven by
AST test + independent grep + source read.

---

## Scoring

Weights adjusted for a deterministic-infrastructure CLI deliverable (no visual
surface): Functionality 30%, Evidence/Process 25%, Craft 25%, Originality 10%,
Design 10%.

| Dimension | Score | Note |
|---|---|---|
| Functionality | 5 | Every B-U1..B-U4 behavior works; all exit codes, taxonomy, ordering, edge cases correct. |
| Evidence/Process | 4.5 | Trace honest and fully reproducible; -0.5 for the probe-7 grep-gaming (F-001). |
| Craft | 5 | Pure functions, `ALLOWED_SOURCES` derived from the map (no duplication), `__file__`-anchored paths, specific recoverable violation messages, runs from any cwd. |
| Originality | 4.5 | Faithfully extends the existing `marketing-render` DNA (versioned intent, exact cited codes) rather than improvising. |
| Design | 4.5 | Clean stdout report format, deterministic ordering, distinct `None` vs empty semantics. |

Weighted total: 5(0.30) + 4.5(0.25) + 5(0.25) + 4.5(0.10) + 4.5(0.10) = **4.8**.

Gates: no Blockers, no High findings, evidence >= 4, functionality >= 4, weighted
>= 4 -> PASS is legal.

## Sprint-boundary notes for downstream sprints (not defects)
- `malformed-query` = `parse_qsl` yields zero pairs (covers no-`?` and unparseable).
  A URL with `?` but only non-utm params parses and falls through to the value
  checks (wrong-medium/campaign-mismatch/unknown-source). This matches the
  contract taxonomy; Sprint 002+ importers should be aware the module never
  raises on odd-but-parseable query strings — it reports codes.
- `validate_asset` raises `FileNotFoundError` for a meta-less folder; the CLI
  translates that to exit 2. Importers in Sprint 002/003 must handle that
  exception rather than assume a result dict.
- A-1 (campaign = date-stripped slug) and A-2 (youtube source string) remain
  documented assumptions honored by both real assets; both toolchains must keep
  importing this single `CHANNEL_SOURCE_MAP` — do not fork a second copy.
