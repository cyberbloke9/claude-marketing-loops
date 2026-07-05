# Product Spec — TERREM Marketing Loops: Publish Layer (Gap 2) + Analytics Plumbing (Gap 3)

> Scope note for downstream agents: this spec closes two roadmap gaps in an existing repo.
> It is written to the same "explicit named schema + deterministic CLI + adversarial fixtures"
> DNA already established by `tools/marketing-render/` (renderer → `manifest.json` →
> `validate.py` → `qa-verdict.json`). Read §9 for the non-negotiable house style before coding.

## 1. Original Request

Verbatim:

> Close Gap 2 (the publish layer) and Gap 3 (analytics plumbing) of the TERREM marketing-loop system, in the existing repo at /Users/prithviputta/Downloads/terrem-marketing-loops, in sprint format with adversarial evaluation.
>
> **Gap 3 — analytics plumbing** (the last unchecked Phase 0 box): build ingestion tooling that turns platform analytics exports (Instagram/YouTube/LinkedIn CSV exports plus site analytics with UTM filtering) into the weekly scorecard `metrics/YYYY-Www.md` following `metrics/TEMPLATE.md` exactly — the retention-first KPI stack (WRR north star computed from provided inputs), flywheel clicks by UTM campaign, per-asset craft diagnostics (3s-hold, swipe-through, shares, clicks) tied to hook-bank numbers, the posting-time A/B table for weeks 1-8, and the decisions-fed-back section. Hard rule from the existing template: if an input is missing, leave the cell blank and list it under "Missing data" — never estimate or invent numbers. The tooling must verify UTM links in asset `meta.md` files follow the documented scheme (`utm_source=<channel>&utm_medium=social&utm_campaign=<slug>`).
>
> **Gap 2 — publish layer up to the API boundary** (no live posting APIs; no platform credentials exist): from a content asset folder that has `qa-verdict.json` verdict=PASS, generate per-channel publish packages — final caption text per channel (Instagram/LinkedIn/YouTube community) with the correct per-channel UTM link, the rendered PNG paths to attach, and a schedule slot — plus a machine-readable publish queue (single file tracking asset → channel → state: queued/posted, with posted date and permalink recorded when a human posts). A `/loop-publish` skill consumes the queue. The gate must be respected: refuse to queue any asset whose `qa-verdict.json` is missing or verdict!=FAIL-free PASS, or whose `meta.md` contains a KILLED marker. Design the seam (queue schema) so real posting APIs can plug in later without reworking the format.
>
> Constraints: Python matching the existing `tools/marketing-render/` toolchain (stdlib + already-present deps only), tested, deterministic where applicable, everything in-repo, no network calls, no fabricated metrics anywhere. Verification standard: evaluator attacks with fixtures — malformed/truncated CSV exports, a metrics run with missing inputs must produce blanks + Missing-data listing (never invented numbers), a non-PASS asset and a KILLED asset must be refused by the publish queue, wrong-UTM assets flagged. npm package `pmp-gywd@5.0.0` is installed globally on this machine if any sprint finds it useful, but nothing may depend on network access.

## 2. Product Goal

Give the TERREM marketing operator two deterministic, no-network CLI toolchains: one that assembles a QA-passed content asset into per-channel publish packages and tracks them in a machine-readable queue up to (but not across) the live-posting-API boundary; and one that ingests channel + site analytics CSV exports into the exact weekly scorecard the template mandates, blanking-and-listing any missing input rather than inventing it.

## 3. Target User

The 2-person TERREM marketing team, operating from Claude Code in this repo. They already know: the five-loop system (`PLAN.md`), the asset folder format (`content/TEMPLATE.md`), the QA gate (`tools/marketing-render/`, `qa-verdict.json`), the scorecard template (`metrics/TEMPLATE.md`), and the UTM scheme. They should NOT need to: hand-write scorecard tables, hand-compute WRR, hand-check UTM strings, remember which assets are KILLED, or touch any social-platform API (none exists; no credentials exist). They post manually on each platform and record the permalink back into the queue.

## 4. Core User Stories

1. **Verify UTM hygiene.** As the operator, I run one command to scan every `content/*/meta.md` and get a pass/fail report of which assets have UTM links that violate the documented scheme, so a wrong-UTM asset never ships.
2. **Enqueue a publishable asset.** As the operator, given an asset whose `qa-verdict.json` is a FAIL-free PASS and whose `meta.md` is not KILLED, I run one command that generates per-channel publish packages and appends the asset's channels to the publish queue in state `queued`.
3. **Be refused when the gate says no.** As the operator, when I try to enqueue an asset that is missing its verdict, has a non-PASS verdict, has any failed check, or is KILLED, the tool refuses with a nonzero exit and a cited reason, and writes nothing to the queue.
4. **Read a publish package.** As the operator, I open a generated per-channel package and see the final caption text (with the correct per-channel UTM link), the exact rendered PNG paths to attach, and the assigned schedule slot — everything I need to post by hand.
5. **Record a manual post.** As the operator, after I post on a platform, I run one command (or the `/loop-publish` skill) that transitions that asset→channel row from `queued` to `posted` and records the posted date and the permalink.
6. **Ingest analytics into the scorecard.** As the operator, at week's end I point the tool at the platform CSV exports + the site-analytics CSV for a given ISO week, and it produces `metrics/YYYY-Www.md` filled to the template, with WRR computed from the provided inputs and every absent input blanked + listed under "Missing data".
7. **Be protected from corrupt exports.** As the operator, when a CSV export is malformed or truncated, the tool rejects it with a nonzero exit and produces no scorecard — corruption never silently becomes a blank cell.

## 5. Required Behaviors

Atomic, testable behaviors. Grouped by the two gaps plus the shared foundation.

### 5.0 Shared — UTM scheme (foundation)

- B-U1. A UTM module parses the `Flywheel target:` line of a `content/<slug>/meta.md` and extracts `utm_source`, `utm_medium`, `utm_campaign`.
- B-U2. The documented scheme is `utm_source=<channel>&utm_medium=social&utm_campaign=<slug>`. A link is **valid** iff: `utm_medium == "social"` exactly; `utm_campaign` equals the asset's folder slug with the leading `YYYY-MM-DD-` date prefix removed (e.g. folder `2026-07-03-hyd-premium-vs-budget` → campaign `hyd-premium-vs-budget`); and `utm_source` is one of the allowed per-channel values in B-U3. (Assumption A-1: campaign = date-stripped slug. See §10; it matches the one real asset, `meta.md` line 9 vs folder name.)
- B-U3. Allowed `utm_source` values, and the canonical channel↔source map used by BOTH toolchains (they MUST agree):
  | Channel | utm_source string |
  |---|---|
  | Instagram | `instagram` |
  | YouTube (community) | `youtube` |
  | LinkedIn | `linkedin` |
  (Assumption A-2: "YouTube community" uses `utm_source=youtube`, matching `meta.md` line 10 "utm_source=youtube". See §10.)
- B-U4. A verifier CLI scans one asset folder OR all of `content/*/`, and reports per asset: `OK` or the specific violation (missing flywheel line, wrong medium, campaign≠slug, unknown source, malformed query string). Exit `0` iff all scanned assets are valid; exit `1` if any asset is flagged; exit `2` on usage error (path not found).

### 5.1 Gap 2 — Publish layer

- B-P1. **The gate — four refusal conditions.** An asset is refused from queuing if ANY of: (a) `content/<slug>/render/qa-verdict.json` is absent; (b) its `verdict` field is not exactly `"PASS"`; (c) its `failed_checks` array is non-empty (the "FAIL-free" half — both fields are checked); (d) the asset's `meta.md` contains the KILLED marker. Refusal = nonzero exit + cited reason + **no write** to the queue or packages.
- B-P2. **KILLED marker match.** The marker is a `meta.md` line whose `QA:` field begins with `KILLED` (real form observed: `QA: **KILLED 2026-07-03** — ...`, `meta.md` line 14). Match: a line matching `QA:\s*\*{0,2}KILLED` (case-sensitive `KILLED`). Presence anywhere in `meta.md` triggers refusal.
- B-P3. **Enqueue.** On a passing asset, for each channel declared for the asset, append (or idempotently update) a row in the single publish-queue file (schema §5.4 QUEUE) with state `queued`. Re-running on an already-queued asset must not duplicate rows and must not regress a `posted` row back to `queued`.
- B-P4. **Publish package generation.** For each channel, write a per-channel publish package (schema §5.4 PACKAGE) containing: the final caption text for that channel with the correct per-channel UTM link appended/substituted; the ordered list of rendered PNG paths to attach (read from `content/<slug>/render/manifest.json` `surfaces[].png`, resolved to repo-relative paths); and an assigned schedule slot.
- B-P5. **Caption source is deterministic assembly, not generation.** Caption body text comes from an authored source field (Assumption A-3, §10: a `Caption:` block added to the asset — the generator defines and documents the field; if absent, the tool errors and lists it, it does NOT invent copy). The tool appends the per-channel UTM link; it never writes marketing prose itself. Same authored body + same channel → byte-identical caption every run.
- B-P6. **Schedule slot origin.** The slot is deterministic: derived from a required `--week` (ISO `YYYY-Www`) argument + a fixed, documented per-channel default time (posting-time A/B is still open per `PLAN.md` §Loop 5, so the tool assigns a morning/evening A/B bucket deterministically, not wall-clock). No `datetime.now()` in any output. (Assumption A-4, §10.)
- B-P7. **Mark posted (human-in-the-loop transition).** A command transitions one asset→channel row from `queued` to `posted`, recording `posted_date` (`--posted-on YYYY-MM-DD`, required) and `permalink` (`--permalink URL`, required). Refuse to mark `posted` a row that is not currently `queued`, or a permalink that is empty.
- B-P8. **API seam.** The QUEUE schema carries `state` from a fixed enum `{queued, posted}` and per-row nullable `posted_date`/`permalink`, plus a top-level `schema_version`, so a future live-posting adapter can flip state and fill fields without reshaping the file. No posting-API field names are invented now; the seam is the state machine, documented in the schema.
- B-P9. **`/loop-publish` skill.** A `.claude/skills/loop-publish/SKILL.md` documents the operator flow: run the gate+enqueue on a `content/<slug>`, read the generated packages, post manually, then mark-posted. The skill invokes the CLIs; it adds no taste judgement and never bypasses the gate (mirrors `/loop-qa`).

### 5.2 Gap 3 — Analytics plumbing

- B-A1. **CSV ingestion, per source.** The tool accepts four input CSV kinds, each with an authored, documented column contract (schema §5.4 CSV-INPUTS): Instagram export, YouTube export, LinkedIn export, and site-analytics export. Since no real platform export format is verifiable from here, these column schemas are an authored internal contract (Assumption A-5, §10); fixtures conform to them. Do NOT attempt to reproduce a specific real platform's export layout.
- B-A2. **Join key.** A CSV metrics row ties to an asset by `utm_campaign == <date-stripped slug>` (the same key as B-U2). Through the asset's `meta.md` this also resolves the asset's hook number for the craft-diagnostics table.
- B-A3. **Malformed/truncated CSV → reject, no scorecard.** If any provided CSV is unparseable, has a missing required header, has a row with the wrong column count, or is truncated mid-row, the tool exits nonzero with the offending file + reason and writes NO scorecard. (This is distinct from B-A4.)
- B-A4. **Absent input → blank + Missing data.** If a whole input source is not provided, or a required value for a cell is absent from otherwise-valid CSVs, the corresponding scorecard cell is left blank and the input is enumerated under a "Missing data" section. The tool never estimates, interpolates, or defaults a metric value.
- B-A5. **WRR (north star) formula, pinned.** WRR = (returning viewers) + (digest/email open-streak count) + (returning site visitors from social), read from named input columns (defined in §5.4 CSV-INPUTS). **Critical edge:** if ANY of the three component inputs is absent, WRR is left **blank** and each missing component is listed under "Missing data". A partial sum is forbidden — it is an invented number. WRR is filled only when all three components are present.
- B-A6. **Flywheel clicks by UTM campaign.** From the site-analytics CSV filtered to `utm_medium=social`, aggregate clicks to `intel.terrem.in` grouped by `utm_campaign`, and fill the Flywheel table. Rows with no data → blank + Missing data.
- B-A7. **Per-asset craft diagnostics.** For each asset published in the target week, emit a row: Asset, Channel, 3s-hold %, completion/swipe-through %, Shares, Clicks, Hook #. Each metric drawn from the matching per-channel CSV by join key; the Hook # read from the asset's `meta.md`. Absent metric → blank cell (not zero).
- B-A8. **Posting-time A/B table (weeks 1–8).** Populate the morning-vs-evening A/B table per channel from the schedule slot recorded (Gap-2 queue / packages) crossed with the week's performance. Weeks beyond 8, or with no data, produce blanks + Missing data; the tool never fabricates a verdict.
- B-A9. **Decisions fed back.** Reproduce the template's "Decisions fed back" section structure. The tool fills only what the data supports (e.g. top/bottom hook by measured performance) and blanks the rest; it does not invent qualitative decisions.
- B-A10. **Output fidelity.** The produced `metrics/YYYY-Www.md` matches `metrics/TEMPLATE.md` section-for-section, heading-for-heading (North star, Flywheel, Craft diagnostics, Posting-time A/B, Vanity, Decisions fed back), plus an appended "Missing data" section listing every blanked input. Filename week comes from a required `--week YYYY-Www` argument (deterministic, never wall-clock).
- B-A11. **UTM verification is invoked here too.** The scorecard run verifies (via the §5.0 module) that each published asset's `meta.md` UTM link is scheme-valid, and flags violators in the Missing-data/notes section (a wrong-UTM asset cannot be silently attributed).
- B-A12. **`loop-measure` skill wiring.** The existing `.claude/skills/loop-measure/SKILL.md` is updated to invoke the new analytics CLI (it currently describes the process narratively). The skill states the malformed-CSV vs missing-input distinction and the "never invent" rule.

## 6. States That Must Exist

- **Empty:** no assets queued yet → queue file is a valid, empty-rows document (not a missing file); scorecard run with zero published assets → template with all-blank tables + full Missing-data listing.
- **Success (publish):** gate passes → packages written + queue rows in `queued`; mark-posted → rows in `posted` with date + permalink.
- **Success (analytics):** all inputs present → fully-filled scorecard, empty (or minimal) Missing-data section.
- **Partial input (analytics):** some inputs present → mix of filled + blank cells, every blank enumerated under Missing data; exit `0` (valid partial scorecard is a success, not an error).
- **Invalid input:** malformed/truncated CSV → nonzero exit, no scorecard (B-A3); wrong-UTM asset → flagged (B-U4 / B-A11).
- **Gate refusal (publish):** missing verdict / non-PASS / failed_checks non-empty / KILLED → nonzero exit, cited reason, no write (B-P1).
- **Idempotency:** re-running enqueue or scorecard on the same inputs → identical output, no duplicate queue rows, no regressed states (B-P3).
- **Offline/network:** every command runs with no network; there is no online state. Any attempted network call is a defect.

## 7. Design Direction

- Match `tools/marketing-render/` exactly: module-level docstring naming the sprint + the seam it consumes/produces; `argparse` CLI; exit codes `0` success / `1` domain failure / `2` usage-or-precondition error; paths resolved from `__file__` so tools run from any cwd; stdlib + Pillow only (Pillow not needed here — prefer pure stdlib: `csv`, `json`, `pathlib`, `argparse`, `re`).
- **Explicit named schemas, not prose.** Every machine artifact (publish queue, publish package, CSV input contracts, any intermediate metrics blob) is a documented schema with a `schema_version` field, exactly like `manifest.json`/`qa-verdict.json`. This is the codebase's DNA and is what lets the Evaluator's fixtures meet the Generator's output.
- **Anti-patterns (forbidden):** `datetime.now()` or any wall-clock in output; estimating/defaulting/zero-filling a missing metric; generating marketing copy; any network import (`requests`, `urllib` fetch, etc.); depending on the globally-installed `pmp-gywd@5.0.0` npm package or any npm/network resource; silently overwriting an existing render or an existing `posted` queue row.
- **Tone in generated docs:** the scorecard's prose obeys `RESEARCH.md` refuted-stats blacklist and the Candid-Analyst register only insofar as it reproduces the template; the tool adds no editorial numbers.
- **Determinism:** same inputs → byte-identical outputs (JSON with sorted keys / stable ordering; Markdown with stable row ordering, e.g. assets by slug, campaigns lexicographic).

## 8. Non-Goals

- No live posting to Instagram/YouTube/LinkedIn; no API clients; no credential handling; no OAuth. The publish layer stops at the API boundary.
- No scraping or fetching of analytics from any platform; inputs are operator-provided CSV files only.
- No new rendering, no changes to `render.py`/`validate.py`/`measure.py`/`acceptance.py` behavior (they may be imported read-only; do not modify their contracts).
- No revival of DB-derived price-trend content (still BLOCKED per `PLAN.md` §2 / provenance gate) — out of scope.
- No dashboards, web UI, or charts of the metrics; the deliverable is the Markdown scorecard + machine artifacts.
- No dependency on `pmp-gywd@5.0.0` (it is mentioned as available but must not be used, since nothing may require network access).

## 9. Technical Constraints

- **Language/runtime:** Python 3.9.6 (confirmed on machine). Stdlib only (`csv`, `json`, `argparse`, `pathlib`, `re`, `datetime` for parsing supplied dates only — never for "now"). Pillow 11.3.0 is available but not expected to be needed.
- **Location:** everything in-repo. New CLIs live under `tools/` following the `tools/marketing-render/` pattern (suggested: `tools/marketing-publish/` for Gap 2, `tools/marketing-metrics/` for Gap 3, or a shared `tools/marketing-loops/` with `utm.py` shared — Generator chooses, but the shared UTM module must be importable by both). Tests under each tool's `tests/`, fixtures under each tool's `fixtures/`, mirroring the existing layout.
- **Persistence:** flat files only. Single publish-queue file at a fixed documented path (suggested `content/publish-queue.json`). Per-channel packages written under the asset folder (suggested `content/<slug>/publish/<channel>.json` or `.md`). Scorecards at `metrics/YYYY-Www.md`.
- **Security/privacy:** no network. No secrets. No personal data written (aligns with `PLAN.md` DPDP posture). CSV inputs are treated as untrusted (robust parsing per B-A3).
- **Existing seams consumed (read-only, do not change):** `content/<slug>/render/qa-verdict.json` (`verdict`, `failed_checks`); `content/<slug>/render/manifest.json` (`surfaces[].png`); `content/<slug>/meta.md` (`Flywheel target:`, `Hook:`, `Channels:`, `QA:` lines); `metrics/TEMPLATE.md`; `content/TEMPLATE.md`.
- **Testing:** `python3 -m unittest discover` per tool (existing convention); an `acceptance.py`-style end-to-end runner that exercises the CLIs as subprocesses and exits `0` iff the whole contract holds — mirroring `tools/marketing-render/acceptance.py`.

## 10. Risks and Ambiguities

- **A-1 (campaign=slug):** UTM `utm_campaign` equals the folder slug with the `YYYY-MM-DD-` prefix stripped. Evidence: real asset folder `2026-07-03-hyd-premium-vs-budget` vs its `meta.md` campaign `hyd-premium-vs-budget`. Safest default: strip the leading `\d{4}-\d{2}-\d{2}-`. If an asset's campaign legitimately differs, the verifier flags it — acceptable, since the scheme is documented.
- **A-2 (YouTube source string):** "YouTube community" maps to `utm_source=youtube`. Evidence: `meta.md` line 10 (`utm_source=youtube`). Both toolchains must use the identical string (§5.0 B-U3).
- **A-3 (caption source):** No existing field is unambiguously "the caption." Default: the Generator introduces and documents a `Caption:` authored block in the asset (or per-channel captions in `meta.md`/a `captions.md`), and the tool errors if it is absent rather than inventing copy. Downstream authors then supply it; fixtures include it.
- **A-4 (schedule slot):** Posting times are an open A/B hypothesis (`PLAN.md`). Default: assign a deterministic morning/evening A/B bucket from `--week` + channel, documented, never wall-clock. Real times are filled by the human when posting (recorded via mark-posted).
- **A-5 (CSV column contracts):** Real platform export formats are unverifiable and variable. Default: author an internal column contract per source, document it in the schema, and have fixtures conform. This is the manifest.json approach applied to inputs.
- **A-6 (WRR components):** Template defines WRR as returning viewers + digest opens + returning site visitors. If a component has no obvious single input column, the Generator names the column explicitly in the CSV contract; absence of any component → blank WRR + Missing-data entries (B-A5). No partial sums.
- **A-7 (Channels list per asset):** `meta.md` `Channels:` line is free text (e.g. "IG carousel + reel, YT short, LinkedIn PDF"). The tool maps free-text channel mentions to the canonical `{instagram, youtube, linkedin}` set; ambiguous/unmapped tokens are surfaced, not guessed. Document the mapping rules.
- **Risk — over-fitting to the one real asset.** Only one PASS asset (`2026-07-03-tgrera-enforcement-wave`) and one KILLED asset (`2026-07-03-hyd-premium-vs-budget`) exist. Build fixtures for the rest; do not hard-code the single real slug into tool logic.

## 11. Suggested Sprint Breakdown

Small, contract-testable slices. Shared UTM foundation first; the two gaps are otherwise independent; final acceptance sprint mirrors the existing `run-001` shape (5 build + 1 acceptance).

- **Sprint 001 — Shared UTM module + verifier CLI.** Parse `meta.md` flywheel line; validate against the scheme (B-U1..B-U4); per-channel source map (B-U3). Deliver an importable `utm` module + a scan CLI over `content/*/`. Tests: valid asset passes; wrong-medium, campaign≠slug, unknown-source, malformed-query, missing-line each flagged. Fixtures: at least one wrong-UTM asset.
- **Sprint 002 — Publish gate + queue schema + enqueue.** Define QUEUE schema (§5.4, `schema_version`, state enum, nullable posted fields — the API seam, B-P8). Implement the four-condition gate (B-P1/B-P2) and idempotent enqueue (B-P3). Tests/fixtures: PASS asset enqueued; missing-verdict, non-PASS, failed_checks-non-empty, and KILLED assets each refused with cited reason and no write.
- **Sprint 003 — Publish package generation + mark-posted + `/loop-publish` skill.** Per-channel packages (caption assembly B-P5, PNG paths from manifest B-P4, schedule slot B-P6); mark-posted transition (B-P7). Write `.claude/skills/loop-publish/SKILL.md` (B-P9). Tests: package bytes stable; UTM link correct per channel; mark-posted refuses non-queued rows and empty permalinks.
- **Sprint 004 — Analytics CSV ingestion (robust).** CSV input contracts (B-A1), join key (B-A2), and the malformed/truncated rejection path (B-A3) vs absent-input handling (B-A4). Deliver an ingestion module producing a validated intermediate metrics structure. Fixtures: valid exports; truncated CSV; wrong-header CSV; wrong-column-count row — each rejected with nonzero exit and no downstream output.
- **Sprint 005 — Scorecard compiler → `metrics/YYYY-Www.md`.** Consume the ingestion output; fill the template exactly (B-A5 WRR incl. no-partial-sum edge, B-A6 flywheel, B-A7 craft diagnostics + hook #, B-A8 A/B, B-A9 decisions, B-A10 fidelity, B-A11 UTM flagging). Update `loop-measure` SKILL (B-A12). Tests: full-input scorecard; missing-input scorecard produces blanks + Missing-data listing and NEVER a fabricated or partial number; determinism.
- **Sprint 006 — Acceptance runner + adversarial fixture suite.** An `acceptance.py`-style end-to-end runner over both gaps: malformed CSV rejected; missing-input run blanks + lists (no invented numbers); non-PASS and KILLED assets refused by the queue; wrong-UTM asset flagged. Exit `0` iff the entire contract holds. Update `README.md` rollout status (check the Phase-0 analytics-plumbing box) and document both toolchains.

---

### §5.4 Named schemas (author these as concrete artifacts, not prose)

The Generator must materialize each of the following as a documented, versioned schema (JSON for machine artifacts) with example fixtures. These are contracts the Evaluator's fixtures will target.

- **QUEUE** — `content/publish-queue.json`: `{ schema_version, rows: [ { slug, channel ∈ {instagram,youtube,linkedin}, state ∈ {queued,posted}, week (YYYY-Www), schedule_slot, package_path, posted_date|null, permalink|null } ] }`. Stable row ordering (slug, then channel). Single source of truth for `/loop-publish`.
- **PACKAGE** — per asset×channel: `{ schema_version, slug, channel, utm_source, utm_link, caption, attachments: [png paths], schedule_slot, week }`. `caption` = authored body + per-channel UTM link; deterministic.
- **CSV-INPUTS** — four documented column contracts (Instagram, YouTube, LinkedIn, site-analytics). Each names its required headers, the join column (`utm_campaign` for site-analytics; asset/campaign identifier for platform exports), and which columns feed which scorecard cell — explicitly the three WRR components (B-A5), 3s-hold, swipe-through/completion, shares, clicks, and flywheel clicks. Fixtures conform to these contracts.
- **Missing-data listing** — the appended scorecard section: an enumerated list of every input/cell left blank and why (source not provided / value absent / WRR component missing / wrong-UTM excluded).
