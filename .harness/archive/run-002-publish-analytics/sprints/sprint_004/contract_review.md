VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Summary

Sprint 004 contract is exceptionally well-written. No blockers or high concerns. The scope is crystal clear, behaviors are testable, edge cases are explicitly named, and the fixture matrix + adversarial probes make the contract unfakeable.

## Analysis

### 1. Scope & Clarity (No Ambiguity)

**Entry point:** CSV ingestion layer for Gap-3 analytics toolchain (spec §5.2).

**Scope boundary (§7 "Explicit non-goals"):** Explicitly OUT of this sprint:
- No scorecard markdown / `metrics/YYYY-Www.md`
- No WRR sum or no-partial-sum blanking decision
- No Missing-data section text
- No posting-time A/B table
- No Decisions-fed-back section
- No `loop-measure` SKILL update
- No modification of Sprint-001/002/003 modules

This is remarkable clarity. A generator cannot claim "I thought X was in scope" because every non-goal is explicitly listed.

**Deliverables named:**
- `csvspec.py` — four CSV column contracts + `read_csv(path, contract)` returning validated rows or raising `CsvError`
- `assetmap.py` — scan content dir, return `campaign → asset-record` map via frozen Sprint-001 `utm` module
- `ingest.py` — CLI + `build_ingest(...)` function; validates args/CSVs, joins metrics, aggregates WRR components (does NOT sum), emits INGEST JSON (§3.5)

**Frozen dependencies:** Sprint-001 `utm.py` is imported read-only; no function is added to any frozen module, so no prior PASSED contract can regress.

### 2. Exact Behaviors & Pass/Fail Criteria

**CLI signature (§3.4):**
```
python3 tools/marketing-loops/ingest.py --week YYYY-Www \
  [--instagram FILE] [--youtube FILE] [--linkedin FILE] [--site FILE] \
  [--content-dir DIR] [--out FILE]
```

**CSV column contracts (§3.1):** Each is declared as a documented, versioned data structure with explicit required headers, types (`str` | `int` | `num`), and join columns:

| Source | Required Headers | Join Column |
|--------|---|---|
| Instagram/YouTube/LinkedIn | `utm_campaign`, `three_s_hold_pct`, `completion_pct`, `shares`, `clicks` | `utm_campaign` |
| Site-analytics | `utm_source`, `utm_medium`, `utm_campaign`, `clicks`, `returning_viewers`, `digest_opens`, `returning_visitors_social` | `utm_campaign` |

**Output schema (§3.5):** INGEST JSON with concrete example; includes `schema_version`, `week`, `sources_provided`, `assets`, `wrr_components` (three component inputs with presence flags, NOT summed), `flywheel_clicks_by_campaign`, `craft`, `absences`.

**Exit codes (§3.6):**
- `0` — success (including partial input, empty run)
- `1` — intentionally unused
- `2` — usage/precondition error (malformed week, missing path, bad content-dir, campaign collision, any B-A3 CSV rejection)

**Rejection criteria (B-A3):**
1. Unparseable / unterminated CSV
2. No header / empty file
3. Missing required header
4. Data row with wrong column count (catches truncated rows)
5. Non-numeric value in numeric column
6. Blank `utm_campaign` join column

Each rejection is exit 2 with a specific cited message naming file + row + column, and **no JSON is emitted** (this is hardened against partial output).

**Success criteria:**
- Valid INGEST JSON with sorted keys (`json.dumps(..., sort_keys=True, indent=2) + "\n"`)
- Craft rows ordered by `(campaign, channel)`
- Flywheel entries ordered by campaign (lexicographic)
- Absences by `(kind, detail)`
- Determinism: byte-identical JSON on identical inputs (testable via shasum in §8)

### 3. Edge Cases Explicitly Named & Handled

**Blank vs zero numeric cell (§3.1 "Numeric typing crux"):**
- Blank cell (`""` after strip) in numeric column → absent (`None`), not corrupt, not zero → exit 0
- Non-blank unparseable value (`abc`, `12x`) → corrupt → exit 2
- `0` or `0.0` → present value (0), distinct from absent (`None`)

The contract provides TWO separate fixtures for this (§9): `blank-cell` → cell is `null`, `zero-cell` → cell is `0`.

**Empty state:**
- No `--<source>` flags → valid all-absent INGEST, one absence per not-provided source, exit 0
- Present CSV with header + zero data rows → exit 0 (distinct from corrupt)

**Absent source vs bad path (§3.4 step 3, §4 "Absent source vs bad path"):**
- Omit `--youtube` → recorded missing, exit 0
- `--youtube /no/such.csv` → exit 2 ("file not found")
Two distinct states.

**Unmatched campaign (B-A2, §4, §9 probe 7):**
- CSV `utm_campaign` matching no content asset → craft/flywheel entry retained with `slug=null`, `hook_number=null`, `unmatched-campaign` absence recorded, exit 0 (a flag, not a rejection)

**Wrong-UTM asset (B-A11, §4, §9 probe 9):**
- Asset whose `meta.md` UTM link is scheme-invalid → `utm_valid=false`, `utm_violations` recorded in assets[], `wrong-utm` absence entry, exit 0 (flagged, not rejected)

### 4. Testability & Fixtures (Comprehensive, Adversarial)

**Verification commands (§8):** Exact CLI invocations provided for:
- Unit tests
- Full happy path (4 sources → exit 0, INGEST with craft rows, flywheel, 3 WRR components)
- Empty state (no sources → all-absent INGEST)
- Partial run (IG only → mix of present + null)
- Determinism (run twice → shasum byte-identical)
- B-A3 rejections (truncated, wrong-header, wrong-colcount, non-numeric, each exit 2, no JSON)
- Absent source vs bad path
- Bad `--week`
- Import safety
- Wall-clock / network grep check

**Fixture matrix (§9):** 12 new fixtures with explicit expected outcomes:
1. `full/` — 4 well-formed CSVs + content with ≥2 assets → exit 0, craft joined, flywheel grouped, 3 WRR components present
2. `full` present-but-header-only → exit 0, source present, values absent
3. `truncated/site.csv` — cut mid-row → exit 2, cited, no JSON
4. `wrong-header/site.csv` — missing header → exit 2, named
5. `wrong-colcount/ig.csv` — extra/missing field in data row → exit 2, row/col cited
6. `non-numeric/ig.csv` — `shares` cell `x` → exit 2, row+column cited
7. `blank-cell/ig.csv` — `clicks` cell `""` → exit 0, cell is `null`
8. `zero-cell/ig.csv` — `clicks` cell `0` → exit 0, cell is `0`
9. `unmatched/ig.csv` — campaign with no matching asset → exit 0, `slug=null`, absence
10. `wrong-utm/content/` — invalid UTM link → exit 0, `utm_valid=false`, absence
11. `blank-join/site.csv` — blank `utm_campaign` → exit 2, cited
12. `empty` (no flags) → exit 0, all-absent INGEST, one absence per source

**Adversarial probes (§9, 12 specific attack vectors):**
1. Full happy path — assert INGEST has schema_version, correct sources_provided, craft rows with RIGHT slug/hook per join, flywheel grouped, WRR components present with expected sums
2. Determinism — run twice, shasum byte-identical, stable ordering
3. B-A3 corruption suite — each exit 2, cited message, empty stdout, no `--out` file written
4. B-A4 blank-vs-zero — blank → `null`, zero → `0`, never conflated
5. Absent source vs bad path — omit → exit 0, flag with bad path → exit 2
6. Partial + empty → IG-only → exit 0 mix; no-source → exit 0 all-absent
7. Join correctness — slug + hook resolved from meta.md; unmatched → `slug=null`
8. **WRR component presence** — all three present when site provided; blank one column → that component `present:false`, others still present (value-level edge for Sprint-005 B-A5); **confirm Sprint 004 does NOT emit summed WRR anywhere**
9. Wrong-UTM flagging — `utm_valid=false`, exact violations codes, `wrong-utm` absence, exit 0
10. Bad `--week` — exit 2, no JSON
11. Import safety + no wall-clock/network — import prints nothing; grep clean
12. Frozen modules untouched — diff shows no changes; full Sprint-001+002+003 suite still passes

### 5. Security & Constraints (Verifiable)

**Stdlib only:** `csv`, `json`, `argparse`, `pathlib`, `re` (§9 Technical Constraints).

**No datetime:** `--week` is validated as a string, never parsed against wall-clock or "now".

**No network:** Grep check in §8 commands: `grep -nE "datetime\.now|requests|urlopen|socket|urllib" tools/marketing-loops/{csvspec,assetmap,ingest}.py || echo "clean"`.

**No pmp-gywd dependency:** Explicitly forbidden (spec §7 anti-patterns, contract §6 Security).

**CSV inputs untrusted:** Robust parsing required; every malformation is cited, never silently converted.

### 6. Schemas Are Concrete (Not Prose)

**INGEST schema (§3.5):** A complete JSON example with explanation of each field:
```json
{
  "schema_version": "1",
  "week": "YYYY-Www",
  "sources_provided": { "instagram": false, "youtube": false, ... },
  "assets": [ { "slug", "campaign", "hook_number", "utm_valid", "utm_violations" } ],
  "wrr_components": {
    "returning_viewers": { "present": false, "value": null, "source": "site" },
    ...
  },
  "flywheel_clicks_by_campaign": [ { "campaign", "clicks" } ],
  "craft": [ { "campaign", "channel", "slug", "hook_number", ... } ],
  "absences": [ { "kind": "source|wrr-component|unmatched-campaign|wrong-utm", "detail" } ]
}
```

**CSV contracts (§3.1):** Declared as data structures with required headers, types, and feed destinations — not prose.

**Numeric typing rule (§3.1 crux):** Explicit regex and examples.

### 7. No Vague Language

- "Must", "is", "does", "rejected" throughout
- No "should", "might", "maybe"
- Regex patterns explicit: `\d{4}-W\d{2}$`, `QA:\s*\*{0,2}KILLED`
- Numeric edge cases pinned with examples
- "Blank" vs "absent" vs "present" vs "corrupt" are distinct concepts, each with exact behavior

### 8. Determinism (Testable, Not Gameable)

**Requirement (§3.4):** "Same inputs → byte-identical INGEST JSON. Sorted keys; craft entries ordered by `(campaign, channel)`; flywheel entries by `campaign` (lexicographic); assets by `slug`; absences by `(kind, detail)`. No `datetime.now()` anywhere."

**Verification (§8):** Shasum command:
```bash
python3 tools/marketing-loops/ingest.py ... | shasum
python3 tools/marketing-loops/ingest.py ... | shasum
# Both shasums must match
```

### 9. Assumptions Documented (Spec §10 "Risks and Ambiguities")

**A-5 (CSV contracts are authored internal):** Explicitly acknowledged. Fixtures conform. This prevents claiming "we used the real platform format."

**A-6 (WRR components in site-analytics):** Justified: "Housing its three component columns in the one week/site-level export keeps WRR single-source (no 'which platform sources were provided' ambiguity)."

**Over-fitting risk:** "Only one PASS asset and one KILLED asset exist... Build fixtures for the rest; do not hard-code the single real slug into tool logic." The fixture matrix (§9) requires building fixture assets, not using the real one.

### 10. Not Gameable

**Frozen utm module import:** The join-key logic and campaign-stripping cannot be reimplemented; it must call `utm.campaign_from_slug(slug)` and `utm.validate_asset(asset_dir)` from Sprint-001. Any hardcoding of the campaign key would fail on the custom fixtures (unmatched, wrong-utm, etc.).

**Fixture matrix covers the attack surface:** Each fixture has a specific expected outcome. A generator cannot hardcode outputs because the fixtures span real asset data (tgrera style), custom test assets, and edge cases (truncated, wrong-header, blank join, etc.).

**Grep check catches network/datetime cheating:** §8 grep commands verify no `datetime.now()`, `requests`, `urlopen`, `socket`, or network `urllib`. A generator cannot add a hidden date or network call.

**Exit-code verification:** Every fixture has a specific exit code expectation. Faking success on corruption (emitting partial JSON + exit 0) would be caught by §9 probe 3 ("no partial JSON on corrupt input").

**Determinism test:** shasum forces byte-identical output. Non-deterministic generation (e.g., random ordering, timestamp in JSON) would fail.

## Conclusion

This is a contract written at the standard of production infrastructure code. The generator has no wiggle room and the evaluator has no ambiguity to exploit. Every behavior is testable, every edge case is named, and every assumption is documented.

**ACCEPT — No changes required.**
