VERDICT: PASS
SCORE: 4.8
BLOCKERS: 0
HIGH: 0

# Findings — Sprint 004: Analytics CSV ingestion → validated INGEST structure

Mode: EVALUATE. Headless CLI + importable-library deliverable (no routes, screens, or
Playwright surface). Verification = exact CLI invocations + exit codes + stderr
substrings + on-disk/stdout JSON assertions, per contract §9 and spec §5.2.

## Verdict

PASS. Every behavior the contract pins is implemented and independently reproduced. All
205 unit tests (Sprint 001+002+003+004) pass. All 12 fixture rows in the §9 attack table
behave exactly as specified. All five B-A3 corruption paths reject with a cited message,
exit 2, empty stdout. The B-A4 blank-vs-zero distinction, the absent-source-vs-bad-path
distinction, and the partial-WRR-component signal are correct. Output is byte-identical
across runs, has no wall-clock, imports no network module. No frozen Sprint 001–003
module regressed. No write leaked into real content/ or metrics/.

## Evidence (reproduced by the Evaluator, not taken from the trace)

### Unit suite
python3 -m unittest discover -s tools/marketing-loops/tests -> Ran 205 tests — OK.
Test files substantial (test_csvspec 159 / test_assetmap 89 / test_ingest 272 lines).

### Full happy path (B-A1/B-A2/B-A6/B-A7 + WRR components)
4 sources on full/ -> exit 0. Craft rows joined with correct slug+hook# (tgrera->#11,
rera->#7) per channel; flywheel grouped {rera:18, tgrera:42}; three WRR components
present with correct sums (returning_viewers=200 unfiltered, digest_opens=95 unfiltered,
returning_visitors_social=52 social-filtered — organic google row correctly excluded
from comp3 only); absences []; schema_version "1"; sources_provided all true. Ordering:
assets by slug, craft by (campaign,channel), flywheel by campaign — as pinned.

### B-A3 corruption suite (each: exit 2, cited, 0 stdout bytes)
- truncated/site.csv -> "row 2 has 5 columns, expected 7" (od confirms file ends mid-row).
- wrong-header/site.csv -> "missing required header(s): digest_opens".
- wrong-colcount/ig.csv -> "row 1 has 6 columns, expected 5".
- non-numeric/ig.csv -> "row 2 column 'shares': non-blank value 'x' is not an integer".
- blank-join/site.csv -> "row 1 column 'utm_campaign': blank join value (row cannot join)".
- Beyond fixtures: NUL byte -> "not parseable as CSV (line contains NUL)" exit 2;
  unterminated quote -> exit 2. Corruption never silently becomes a blank cell.

### B-A4 blank-vs-zero (never conflated)
blank-cell/ig.csv -> craft clicks: null (absent). zero-cell/ig.csv -> craft clicks: 0
(present). Distinct, exit 0 both.

### Absent-source vs bad-path (two distinct states)
Omit --youtube -> exit 0, sources_provided.youtube=false, a source absence.
--youtube /no/such/file.csv -> exit 2 "--youtube file not found".

### WRR component presence (Sprint-005 B-A5 signal, correctly deferred)
Blank only digest_opens column (other two populated) -> digest_opens
{present:false,value:null}, other two present:true with correct sums, plus a
wrr-component absence for digest_opens only. Sprint 004 emits NO summed WRR anywhere —
the no-partial-sum decision is correctly left to Sprint 005.

### Flags, not rejections (B-A11)
unmatched/ig.csv -> craft slug=null, hook_number=null, an unmatched-campaign absence,
exit 0. wrong-utm/content/ (meta.md utm_medium=organic) -> asset utm_valid=false,
utm_violations=['wrong-medium'], a wrong-utm absence, exit 0.

### Empty + header-only states
No sources -> all-absent INGEST, exactly 4 source absences (the earlier over-count to 7
was repaired per trace 16:44 and is confirmed fixed), exit 0. header-only/site.csv ->
site present:true, flywheel [], WRR components all absent + three wrr-component absences,
exit 0 (present-but-empty != corrupt).

### Determinism / hygiene
Two identical runs -> shasum byte-identical (16e39d1d...). --out NOT written on corrupt
input (exit 2, file absent); written on success with empty stdout. import csvspec,
assetmap, ingest prints only ok (import-safe). grep -E
"datetime.now|requests|urlopen|socket|urllib" over the three new sources -> clean. Bad
--week (2026-27, 2026-W5) -> exit 2, no JSON.

### No regression / no leak
205-test suite (incl. all frozen Sprint 001–003 tests) passes; frozen module mtimes
predate Sprint 004. Real content/ still holds only the two real assets + TEMPLATE.md +
the Sprint-003 captions.md; no publish-queue.json and no metrics/*.md leaked.

## Non-blocking observations (no action required this sprint)

- O-1 (Low, Process): In ingest.run() the asset-map build (which can raise a
  campaign-collision ValueError->exit 2) runs after CSV parsing, whereas contract §3.4
  lists content-dir/asset-map (step 4) before CSV parse (step 5). Both outcomes are exit
  2 with no output, and no fixture combines a collision with a corrupt CSV, so the
  observable contract is unaffected. Cosmetic ordering only.
- O-2 (Low, Craft): WRR comp1/comp2 are unfiltered column sums while comp3 is
  social-filtered. Matches contract §3.4 step 6 exactly (only comp3 scoped to social);
  the full fixture's organic row carries 0,0 so it is not value-changing. Correct — noted
  so Sprint 005 keeps the same filtering. PROVEN behaviorally (advisor-flagged gap closed): a discriminating site.csv with a nonzero organic row (google,organic,tgrera,7,50,50,50) -> returning_viewers=250 & digest_opens=145 (unfiltered, organic INCLUDED) while returning_visitors_social=52 (social-filtered, organic EXCLUDED) and flywheel tgrera=42 (organic clicks excluded). A wrong social-filter on comp1/comp2 would have yielded 200/95; it did not.

## Scoring

Weights adjusted for systems/infrastructure (Functionality + Evidence up, Design +
Originality down; no UI, no auth/money/PII so Security stays baseline): Functionality
30%, Evidence/process 30%, Craft 20%, Design 10%, Originality 10%.

- Functionality: 5 — every contract behavior + every edge (blank/zero, absent/bad-path,
  partial WRR, NUL, unterminated quote, unmatched, wrong-UTM) verified.
- Evidence/process: 5 — 205 tests, cited errors, byte-identical determinism, grep-clean,
  independently reproduced; trace claims held under attack.
- Craft: 5 — pure modules, cited recoverable messages, deterministic ordering, single
  source of truth (reuses frozen utm, no forked map/regex), no import side effects.
- Design: 4 — versioned schemas, clean INGEST seam, exit-code taxonomy consistent with
  render/Sprint 001–003.
- Originality: 4 — competent, idiomatic; N/A dimension for a headless ingestion CLI.

Weighted total = 5(.30) + 5(.30) + 5(.20) + 4(.10) + 4(.10) = 4.8.
Passing bar met: 0 blockers, 0 high, Evidence >=4, Functionality >=4, weighted >=4.
