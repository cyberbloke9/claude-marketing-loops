VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Findings — Sprint 005: Scorecard compiler → `metrics/YYYY-Www.md`

Mode: EVALUATE. Verification is CLI + exit-code + byte-for-byte golden-Markdown
(no UI/Playwright — this is a headless CLI + pure library, per contract §5). Every
claim below was reproduced by the Evaluator independently of the Generator's trace.

## Verdict rationale

All 16 rows of the contract §9 attack checklist and all 8 adversarial probes were
re-run from a clean shell and passed. No blocker, no high, no medium finding. The
implementation is disciplined, deterministic, and honest about what a single-week
scorecard cannot contain (structural blanks are enumerated, never faked).

## Evidence (independently reproduced)

**Unit suite.** `python3 -m unittest discover -s tools/marketing-loops/tests -q`
→ `Ran 233 tests ... OK` (205 frozen Sprint 001–004 + 28 new). Frozen suite green,
no regression.

**Full happy path — golden byte-match.** Full run `diff`s byte-equal to
`fixtures/metrics/expected/full.md`. Hand-verified against the fixture CSVs:
WRR This-week = 347 = 200+95+52; flywheel `rera-refund-timeline: 18<br>tgrera-
enforcement-wave: 42`; 6 craft rows in `(campaign, channel)` order with decimals
correct (`29.5` kept, `24.0`→`24`); A/B instagram evening 51 (18+33), youtube
morning 30 (9+21), linkedin evening 67 (27+40), buckets read from queue slot;
Loop 2 `top hook #11 (94 clicks); retire-candidate hook #7 (54 clicks)`; 15 sorted
de-duplicated structural Missing-data bullets.

**WRR critical edge (B-A5) — no partial sum.** `wrr-partial/site.csv` → This-week
blank; `WRR component 'returning_viewers' absent` listed once; grep for forbidden
partial sums (147/252/295) across the file → none. Byte-equal `expected/wrr-partial.md`.

**Corruption never becomes a blank cell (B-A3).** `truncated / wrong-header /
wrong-colcount / non-numeric / blank-join` → each exit 2, cited stderr, no
scorecard file created even with `--out`.

**Bad queue.** nonexistent path / malformed JSON / no-`rows` object → exit 2 each,
cited, no scorecard.

**Usage.** `--out`+`--stdout` → exit 2; `--week 2026-27` / `26-W27` → exit 2. Empty
run → exit 0, full blank skeleton + full Missing data (byte-equal `expected/empty.md`).

**Blank ≠ 0 (B-A7).** zero-cell Clicks renders `0`; blank-cell renders blank +
`craft Clicks absent for … (instagram)`. Never conflated.

**Unmatched + wrong-UTM (B-A11).** unmatched craft row `… (unmatched)` + bullet
(byte-equal); wrong-UTM `wrong-UTM asset 2026-07-03-bad-utm-asset: wrong-medium`
(byte-equal). Both exit 0.

**No `--queue`.** A/B table entirely blank + single `publish queue not provided` line.

**Determinism.** Two runs + flag-reordered run → identical shasum (`106555ae…`);
exactly one trailing newline; `partial.md` golden byte-match.

**Never-invent sweep.** grep full+empty for `N/A`/`TODO`/`Lorem`/fabricated em-dash
→ clean; every number traces to an input cell.

**Hygiene.** grep `datetime.now|requests|urlopen|socket|urllib` in scorecard.py →
clean; `import scorecard` side-effect-free; real `content/` + `metrics/` untouched.

**Frozen modules untouched (§2 / §9 probe 7) — verified by mtime + symbol presence,
not test-green.** `stat` on `tools/marketing-loops/*.py`: every Sprint 001–004
module (`utm/verify_utm/gate/queue/channels/enqueue/captions/schedule/package/
mark_posted/csvspec/assetmap/ingest`) carries a 2026-07-04 mtime; only
`scorecard.py` is 2026-07-05. No frozen source was rewritten. The four symbols
`scorecard.py` imports from frozen modules —
`schedule.CANONICAL_CHANNELS/BUCKET_MORNING/BUCKET_EVENING` and `queue.load_queue`
— are all defined in the unchanged 07-04 files (grep-confirmed), so no function was
added to a frozen module to expose them. `.harness/archive/` holds only the
unrelated `run-001-renderer` snapshot.

**B-A12 SKILL.** `.claude/skills/loop-measure/SKILL.md` invokes `scorecard.py`,
states malformed-CSV(exit 2) vs missing-input(blank) distinction, never-invent rule,
WRR no-partial-sum edge, and exit taxonomy.

## Trace review

`generator_trace.log` is consistent with observed behavior — exit codes, golden
matches, WRR math, determinism shasums, frozen-suite green all reproduce. The two
disclosed known risks (flywheel `<br>` separator; Loop-2 clause appended to label)
are deterministic and template-faithful, not defects. No skipped failures, no
claim-without-artifact, no premature-completion language.

## Scoring

Functionality 5, Evidence 5, Craft 5, Design 4, Originality 4. Weighted (20% each):
(5+5+5+4+4)/5 = 4.8. Passes every gate: 0 blockers, 0 high, evidence ≥4,
functionality ≥4, weighted ≥4.

## No findings

Nothing to fix. Sprint 005 is proven.
