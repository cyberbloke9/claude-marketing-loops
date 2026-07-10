# Sprint 006 Contract — Live transition, no-regress, day-cap, end-to-end

Scope: spec §11 Sprint 006 + behaviors **B14, B15, B16** (the LIVE posting path —
per-row `queued → posted` transition reusing `mark_posted` semantics, permalink +
`posted_date` recording, per-day cap enforcement), the live-reachability wiring of
the already-built adapters (B19–B24 IG, B25–B29 LI, B30–B32 FB behind
`--enable-facebook`) so their refusal paths become CLI-observable exit codes, and
the **end-to-end real-asset dry-run** verification + determinism regression gate
(B6–B11, B8, B9, B40–B42). This is the culminating integration sprint: it turns the
Sprint 003/004/005 adapters — whose `execute()` was previously CLI-unreachable
("honest no-op") — into the actual `--live` path, and makes the queue transition
real. No new adapter endpoints are invented; no API facts are re-derived.

Ground truth already locked by prior sprints (do NOT re-derive): `RESEARCH.md`
R4-B1..B5, R5-1..R5-7. This sprint adds NO new API surface — it wires existing,
verified adapter flows into the live driver and the frozen queue transition.

The queue transition MUST reuse the frozen `mark_posted.transition` (spec §11
"reusing `mark_posted` semantics"; B14/B15) — imported and called, NOT
reimplemented — so the field-setting (`state`, `posted_date`, `permalink`),
no-regress guard, and deterministic `queue.write_queue` are byte-identical to the
human-in-the-loop tool.

This is a stdlib CLI + JSON tool; there is NO browser surface (Playwright: N/A —
§13). Verification is `unittest` + CLI probes (§11). Python 3 stdlib only. No real
socket in any test or default run; `main()` never injects a transport.

---

## 1. What this sprint delivers (the testable core)

Replaces the `mode == "live"` "honest no-op" branch in `run()`
(`publish_api.py:1391–1421`) with a real live driver that, for each in-scope
`queued` row in ascending `(slug, channel)` order:

1. Builds a per-channel **execute context** (`ctx`) from the parsed `.env` +
   flags (tokens loaded to memory only, never echoed — B13/B17).
2. Enforces the **per-day cap** (B16) against a single baseline count + a run
   counter (§5).
3. Calls the correct adapter's `execute(row, package, ctx, transport)` against the
   **injected `transport`** (the real `Transport()` in the CLI; a
   `RecordingTransport` in every test — §9), collecting the returned permalink.
4. Performs the `queued → posted` transition via `mark_posted.transition` and
   writes the queue **incrementally** (after each successful row) so a later
   refusal leaves earlier posts persisted (§5, §6).

Facebook `execute` is now wired into the live path **behind `--enable-facebook`**
(its named downstream consumer per the Sprint 005 contract §1.3), keeping the
`round-5-gap` label; with the flag OFF a `facebook` row is skipped with the
existing NOTICE (unchanged from Sprint 005).

The dry-run path is UNCHANGED behaviorally; this sprint only adds the end-to-end
real-asset dry-run **regression gate** (Gate 5) + determinism gate (Gate 6) over
the real queued asset `2026-07-09-anarock-vs-propequity` (2 rows), and re-affirms
B8 (dry-run makes zero network calls, writes no queue) via the raising-transport
proof (Gate 8).

---

## 2. Routes / screens / components affected

None (CLI). Affected code, all in `tools/marketing-loops/publish_api.py`:

- **New import:** `import mark_posted` (beside-file, via the existing
  `sys.path.insert(_HERE)` pattern) — reuse `mark_posted.transition`.
- **Changed:** `_live_gate(...)` refactored to ALSO return the parsed `env` dict +
  the resolved `base` URL (so `ctx` is built without re-parsing `.env`); its
  failure semantics are UNCHANGED (same cited messages, same exit-2 gate).
- **New:** a live-driver helper (e.g. `_run_live(selected, q, queue_path, date,
  max_per_day, ctx-builder, transport, enable_facebook, ...)`) that owns the cap
  loop, execute dispatch, transition, and incremental write.
- **New:** a `ctx` builder (e.g. `_build_ctx(env, base, linkedin_post_type,
  linkedin_version)`) mapping `.env` keys → the per-adapter ctx keys the existing
  `execute` methods already consume (`ig_user_id`/`ig_access_token`,
  `li_person_urn`/`li_access_token`/`linkedin_post_type`/`linkedin_version`,
  `fb_page_id`/`fb_page_token`, `public_asset_base_url`).
- **Changed:** `run()` — the `mode == "live"` branch calls the live driver instead
  of the no-op; adds the **targeted already-posted refusal** (§4.1) and the
  **missing-local-upload precondition** (§4.4).
- **New tests** appended to `tools/marketing-loops/tests/test_publish_api.py`.

NO changes to `queue.py`, `mark_posted.py`, `utm.py`, `channels.py`,
`schedule.py`, `captions.py`, or any adapter `execute`/`plan_steps` body (they are
frozen and merely become reachable). NO change to the queue schema.

---

## 3. Data / state transitions

- **Input state:** the queue at `--queue` (default `content/publish-queue.json`),
  `.env` at `--env`, the per-row package JSON, and (for uploads) the local PNG/PDF
  bytes referenced by the package/manifest.
- **Live success transition (per row):** exactly what `mark_posted` does — that one
  `(slug, channel)` row flips `state: queued → posted`, `posted_date` ← `--date`
  (verbatim, never wall-clock), `permalink` ← the platform-returned URL from
  `execute`. Written via `queue.write_queue` (deterministic: `sort_keys`,
  `indent=2`, trailing newline). Other rows are untouched.
- **Dry-run:** NO queue transition, NO queue write; only `content/publish-plan.json`
  is written (unchanged from prior sprints).
- **No-regress invariant:** an existing `posted` row is NEVER re-posted and its
  `posted_date`/`permalink` are NEVER cleared or regressed — enforced by
  (a) selection being `state == queued` only (B2), and (b) `mark_posted.transition`
  returning `"not-queued"` as a defense-in-depth safety net at write time.

---

## 4. Preconditions, guards, and exit-code mapping (mirror the toolchain)

Exit codes (B40–B42): `0` success, `1` domain refusal (cited on stderr), `2`
usage/precondition (cited on stderr, no write, no network).

### 4.1 Targeted already-posted refusal → exit 1 (B15, mark_posted parity)

In **`--live`** only, AFTER row selection and BEFORE the empty-state message: if the
`state == queued` selection is EMPTY **but** the queue contains at least one row
matching the run scope (`week` == `--week`, and the `--slug`/`--channel` filters if
given) whose `state == "posted"`, the tool REFUSES with exit **1** and a cited
message in the `mark_posted` idiom, e.g.:
`"REFUSED (<slug>, <channel>): row is already posted; refusing to re-post (no
double-post)"`. No network, no write. (This is the no-double-post guard made
observable, exactly like `mark_posted` exit 1.)

**Filter-specificity discriminator (the exact rule the guard fires on):** This
exit-1 refusal fires ONLY when BOTH `--slug` and `--channel` are supplied, so the
run uniquely targets a single `(slug, channel)` row whose state is `posted` with no
`queued` row in scope. For any broader scope (week-only, or `--week` + `--slug`
without `--channel`, or any scope that does not pin exactly one `(slug, channel)`
row) that resolves to zero queued rows, the tool emits exit **0** `"nothing queued
for <week>"` regardless of any `posted` rows present. This makes the exit-1
condition unambiguous and consistent with BOTH Gate 3 (`--slug X --channel IG` → one
posted row → exit 1) and Gate 4 (`--week W` → all rows posted → exit 0).

Rationale / reconciliation with B16 (documented, §10): B16 REQUIRES existing posted
rows to *coexist and be counted* toward the day-cap in a broad run — so an
already-posted row can NOT abort a partially-posted week. Therefore the exit-1
refusal fires ONLY under the filter-specificity discriminator above — BOTH `--slug`
and `--channel` supplied, pinning one `posted` `(slug, channel)` row with no queued
row in scope (the operator explicitly re-targeted an already-done row). When the
scope also contains `queued` rows, those process and the posted rows are silently
out-of-scope-for-processing but COUNTED for the cap (§5). Dry-run keeps its
existing behavior (posted-only scope → "nothing queued" exit 0; no posting occurs
in dry-run so no double-post risk).

### 4.2 Adapter domain refusals surfaced in live → exit 1

The already-built adapter refusal paths now become CLI-reachable. Any
`AdapterRefusal` raised by `execute` (IG container `status_code == ERROR/EXPIRED`,
B22; IG rate-limit `quota_usage >= quota_total`, B19; unexpected IG/LI/FB response
shape) → the offending row is REFUSED with exit **1**, a cited stderr line naming
the row + reason; **processing stops**; rows already posted earlier in THIS run
stand (their queue writes persisted). No further rows are attempted.

### 4.3 Adapter usage errors + live pre-validation → exit 2

Before ANY live post, the tool pre-validates every in-scope row by building the
plan IN MEMORY (calling `_build_plan(...)`, the SAME adapter validation dry-run
uses — >10 carousel children B2, 0 attachments) with the live flags. Any
`AdapterUsageError` → exit **2**, cited, NO network, NO queue write, NOTHING
posted. (The in-memory plan is DISCARDED — live must NOT write
`publish-plan.json`, §7.)

### 4.4 Missing local upload bytes → exit 2 (precondition)

Dry-run does "no byte read", so `_build_plan` cannot catch a missing local upload
file; `execute` reads it mid-flow (`step.execute_body()` — LinkedIn PDF/PNG bytes).
Define: in live, if an adapter's required local upload file (LinkedIn Document PDF
from `render/manifest.json`; LinkedIn MultiImage / any byte-upload attachment) is
missing/unreadable on disk, the tool raises a cited **exit 2** precondition for
that row; rows posted earlier in this run stand. Preferably checked up-front in the
pre-validation pass (§4.3) so nothing posts when a later row's bytes are missing;
if surfaced mid-flow it is still exit 2 with prior siblings persisted. (Instagram
uploads by URL, not bytes — no local-byte precondition for IG.)

### 4.5 Live gate (B12, unchanged) → exit 2

`_live_gate` still checks all three preconditions (env tokens for in-scope
channels, `PUBLIC_ASSET_BASE_URL`, `--i-have-verified-dry-run`) + `--date`, each
cited, exit **2**, no network, no write. Refactor returns `(failures, env, base)`;
FAILURE MESSAGES AND GATE BEHAVIOR ARE BYTE-IDENTICAL to Sprint 002/005. Facebook
tokens are required by the gate only when `--enable-facebook` is ON (unchanged).

---

## 5. Per-day cap enforcement (B16) — exact counting semantics

The cap is keyed on `--date`. **Single baseline + run counter** (do NOT re-scan
disk after each write, or posts double-count):

- `baseline = ` number of rows in the LOADED queue with `state == "posted"` AND
  `posted_date == --date` (computed ONCE, before the loop).
- `made = 0` (posts made so far in THIS run).
- For each selected `queued` row in `(slug, channel)` order:
  - If `baseline + made >= max_per_day` → REFUSE this row with exit **1**, cited
    `"REFUSED (<slug>, <channel>): would exceed the per-day cap of <N> post(s) for
    <date> (day-cap)"`; **processing stops**; rows posted earlier in this run stand.
  - Else: `execute` → transition → `write_queue` → `made += 1`.

`--max-per-day N` (default 3) overrides; already validated as int ≥ 1 (exit 2
otherwise). Facebook rows skipped for the disabled flag do NOT count against the
cap (they never post). This counting rule is the documented §10 assumption.

---

## 6. Live driver ordering + incremental persistence (the "prior posts stand" law)

The live loop MUST write the queue AFTER EACH successful row transition (not once
at the end), so that when a later row hits a cap breach (§5), an `AdapterRefusal`
(§4.2), or a missing-byte precondition (§4.4), the earlier successful posts are
already persisted on disk. Concretely: hold the working queue doc in memory,
transition one row, `queue.write_queue(queue_path, new_q)`, advance to the next
row. On success stdout gets one `"posted <slug> <channel> <date>"` line per row
(mirroring `mark_posted` stdout) plus the recorded permalink; the final exit code
is 0 only if EVERY selected row posted.

Order is deterministic ascending `(slug, channel)` (B3). No wall-clock anywhere
(B9): `posted_date` is `--date` verbatim.

---

## 7. Persistence & secrets discipline (spec §5.4, §9)

- **Live writes the QUEUE ONLY.** Live mode MUST NOT write
  `content/publish-plan.json` (persistence §5: the plan is a dry-run artifact). The
  in-memory `_build_plan` pre-validation result is discarded. Testable: after a
  live run, `publish-plan.json` is absent/unchanged.
- **Dry-run writes the PLAN ONLY**, never the queue (B8) — unchanged.
- **Secrets (B13/B17).** `.env` token values are loaded to memory only and NEVER
  appear in stdout, stderr, `publish-plan.json`, or the queue. `ctx` carries real
  tokens ONLY into `execute` → the injected transport (over the wire); no cited
  message, stdout line, or written file contains a token. `.env` stays gitignored
  (`.gitignore` line `.env`, verified); the queue write contains only the
  platform-returned permalink + the supplied `--date`, never a secret. Testable: a
  sentinel token in `.env` is ABSENT from all emitted output AND from the written
  queue after a live run (§12).

---

## 8. Facebook in live (round-5-gap, gated) — explicit decision

- **`--enable-facebook` ON, gate passes (FB tokens present):** a `facebook` row is
  posted via `FacebookAdapter.execute` against the injected transport (the same
  `_fb_flow`), transitioned + permalink-recorded like any other row, and COUNTED
  toward the cap. The `round-5-gap` nature remains labeled in the adapter note; the
  live path adds NO new endpoints. (This fulfills the Sprint 005 §1.3 promise that
  Sprint 006 is FB `execute`'s downstream consumer.)
- **`--enable-facebook` OFF (default):** the `facebook` row is SKIPPED with the
  existing exact NOTICE (Sprint 005 §7.1/§7.2), does NOT transition, does NOT count
  against the cap, does NOT fail the run; IG/LI rows still post. Exit 0 if all
  non-skipped rows post.

---

## 9. No-network proof + transport injection (B38/B39)

- Every Sprint-006 live test injects a `RecordingTransport` (canned responses) or a
  `RaisingTransport`; NO test opens a real socket. `main()` STILL never injects a
  transport (the real `Transport()` is used only when the founder runs live later).
- The single-`urlopen`-call-site AST test (from Sprint 002) stays GREEN — this
  sprint adds no new `urlopen`/`urllib.request` usage (adapters call the injected
  transport; the live driver passes `transport` through unchanged).
- The **raising-transport dry-run proof** stays GREEN: dry-run over the real asset
  with a `RaisingTransport` still exits 0 and emits the full plan (B8) — no live
  code path runs in dry-run.

---

## 10. Risks / assumptions (documented in module + here)

1. **No-regress exit-1 scope (B15 vs B16).** Resolved §4.1: exit-1 already-posted
   refusal fires ONLY under the filter-specificity discriminator — BOTH `--slug` and
   `--channel` supplied, pinning one `posted` row with no queued row in scope. Any
   broader scope (week-only or `--week`+`--slug` without `--channel`) resolving to
   zero queued rows → exit 0 "nothing queued for <week>". Two tests pin both readings
   (§12.1a targeted → exit 1, §12.1b broad week re-run → exit 0).
2. **Day-cap counting (B16).** Single baseline (`posted` rows with
   `posted_date == --date`) + run counter; refuse the breaching row (exit 1), prior
   posts stand (§5). Documented assumption.
3. **Missing local upload bytes (§4.4).** Dry-run's "no byte read" cannot pre-catch
   it; defined as an exit-2 precondition, prior siblings persisted.
4. **Facebook live is a round-5-gap guess (R4-B5).** Wired behind
   `--enable-facebook` only; the label persists; not treated as verified (§8).
5. **`mark_posted.transition` reuse.** Depends on the frozen `queue`/`mark_posted`
   semantics; if those change, this path changes with them (intended — single
   source of transition truth).

---

## 11. Verification gate (commands + expected output)

Run from repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`.

- **Gate 1 — full regression suite GREEN.**
  `python3 -m unittest discover -s tools/marketing-loops/tests -v`
  Expected: OK, 0 failures / 0 errors / 0 skips; the Sprint-005 count (366) PLUS
  the new Sprint-006 tests; no test skipped to pass.

- **Gate 2 — live happy path (mock transport, throwaway workspace).** Seed a
  throwaway queue (IG + LI rows, both `queued`, week `W`) + packages + local
  upload bytes + a `.env` with all tokens + `PUBLIC_ASSET_BASE_URL`. Drive `run(...
  mode="live", date="2026-07-09", transport=RecordingTransport(canned...),
  i_have_verified_dry_run=True, public_asset_base_url=..., env_path=...)`.
  Expected: exit 0; BOTH rows flip `queued → posted` in the written queue with
  `posted_date == "2026-07-09"` and `permalink` == the canned platform URL
  (IG permalink from the media permalink fetch; LI `https://www.linkedin.com/feed/
  update/<urn>`); stdout has a `posted <slug> <channel> 2026-07-09` line per row;
  NO `publish-plan.json` written; the recorded transport calls match the adapter
  flow order.

- **Gate 3 — no-regress, TARGETED already-posted → exit 1.** Seed a queue where
  `(slug, instagram)` is already `posted` (with a permalink); run
  `--live --slug <slug> --channel instagram --week W` (+ passing gate).
  Expected: exit **1**; cited `REFUSED (<slug>, instagram): row is already posted
  …`; queue BYTE-IDENTICAL to before (no regression of `posted_date`/`permalink`);
  ZERO network (RecordingTransport untouched).

- **Gate 4 — no-regress, RE-RUN a fully-posted week → exit 0.** Take the Gate-2
  post-run queue (both rows `posted`), re-run the SAME `--live --week W`.
  Expected: exit **0**; `"nothing queued for W"`; queue BYTE-IDENTICAL (no
  re-post, no field regression); ZERO network.

- **Gate 5 — day-cap breach → exit 1, prior posts stand.** Seed 3 `queued` rows in
  scope (or 2 queued + 1 existing posted with `posted_date == --date`) with
  `--max-per-day 1` (or 2). Run `--live`.
  Expected: the first (in `(slug, channel)` order) allowed row(s) post and are
  persisted; the row that WOULD breach the cap is REFUSED with exit **1**, cited
  `… (day-cap)`; processing STOPS; the written queue shows the earlier row(s)
  `posted` and the breaching + later rows STILL `queued`; ZERO network for the
  refused/untried rows.

- **Gate 6 — adapter refusal surfaced (container ERROR / rate-limit).** Seed an IG
  row; canned `RecordingTransport` returns `status_code == "ERROR"` at the poll
  step (or `quota_usage >= quota_total` at the pre-check). Run `--live`.
  Expected: exit **1**, cited container-error / rate-limit reason; the row is NOT
  transitioned; any earlier successful row this run stands.

- **Gate 7 — real-asset end-to-end dry-run (2-row fidelity, DEFAULT mode).**
  `python3 tools/marketing-loops/publish_api.py --week 2026-W28`
  Expected: exit 0; `content/publish-plan.json` + stdout list EXACTLY the 2 real
  rows (`instagram`, `linkedin`) for `2026-07-09-anarock-vs-propequity` in
  `(slug, channel)` order; IG row shows its full container-flow steps, LI row its
  Document-flow steps; caption + UTM link verbatim; secrets/dep-values as
  placeholders; ZERO network; queue UNCHANGED. (Regression gate — behavior owned by
  Sprint 003/004; this confirms Sprint 006 did not perturb it.)

- **Gate 8 — determinism + raising-transport (B8/B9).** Run Gate 7 twice; the two
  `content/publish-plan.json` files are BYTE-IDENTICAL. Repeat Gate 7 with a
  `RaisingTransport` injected via `run(..., transport=RaisingTransport())`: still
  exit 0, full plan emitted, no queue write (proves dry-run makes zero network
  calls).

- **Gate 9 — live writes queue only, no plan; no secret leak.** After the Gate-2
  live run: assert `publish-plan.json` was NOT written by the live run; assert the
  sentinel `.env` token string is ABSENT from stdout, stderr, AND the written queue
  file.

- **Gate 10 — live gate still enforces (exit 2).** `--live --week W` missing
  `.env` / missing `PUBLIC_ASSET_BASE_URL` / missing `--i-have-verified-dry-run` /
  missing `--date` each → exit **2**, cited, ZERO network, NO queue write. (Gate
  behavior byte-identical to Sprint 002/005.)

- **Gate 11 — missing local upload bytes → exit 2.** LI Document row whose manifest
  PDF is absent on disk, live gate passing: exit **2**, cited precondition; if a
  sibling row was ordered earlier and posted, it stands; otherwise no queue write.

## 12. Unit-test scenarios (appended to `test_publish_api.py`)

Each hermetic (throwaway workspace via the existing `_seed_workspace`, extended to
seed `.env`, local upload bytes, and canned transport responses). No real socket in
any test.

1a. **`test_live_targeted_already_posted_refusal`** — targeted posted row → exit 1,
    cited, queue byte-identical, transport untouched (§4.1, Gate 3).
1b. **`test_live_rerun_fully_posted_week_exit0`** — re-run fully-posted week → exit
    0, "nothing queued", queue byte-identical (Gate 4).
2. **`test_live_happy_path_ig_li_transition`** — IG+LI post, both rows flip to
   `posted` with `posted_date` + platform permalink, stdout `posted …` lines, no
   plan written, transport call order correct (Gate 2).
3. **`test_live_permalink_recorded_from_response`** — the recorded `permalink` is
   EXACTLY the value `execute` returns (IG media permalink fetch; LI URN-derived).
4. **`test_live_daycap_breach_refusal_prior_stand`** — cap breach → exit 1 cited
   `day-cap`, earlier row persisted `posted`, breaching + later rows still
   `queued`, processing stopped (Gate 5).
5. **`test_live_daycap_counts_existing_posted_today`** — an existing `posted` row
   with `posted_date == --date` consumes cap budget (baseline counting, B16).
6. **`test_live_adapter_refusal_container_error`** — canned IG `ERROR` status →
   exit 1, row not transitioned, prior row stands (Gate 6).
7. **`test_live_adapter_refusal_rate_limit`** — `quota_usage >= quota_total` →
   exit 1 cited rate-limit, no transition.
8. **`test_live_incremental_write_prior_posts_persist`** — a 2-row run where row 2
   raises `AdapterRefusal`: row 1 is persisted `posted` on disk, row 2 still
   `queued`, exit 1.
9. **`test_live_no_plan_written`** — after a live run, `publish-plan.json` does not
   exist / is unchanged (§7, Gate 9).
10. **`test_live_no_secret_in_queue_or_output`** — sentinel `.env` token absent
    from stdout, stderr, and the written queue (Gate 9).
11. **`test_live_missing_upload_bytes_exit2`** — LI Document PDF absent → exit 2
    cited precondition (Gate 11, §4.4).
12. **`test_live_facebook_enabled_posts`** — `--enable-facebook` ON, FB row posts
    via `execute`, transitioned, `round-5-gap` note preserved, counts toward cap
    (§8).
13. **`test_live_facebook_disabled_skipped_no_count`** — `--enable-facebook` OFF,
    FB row skipped with NOTICE, not transitioned, does not consume cap; IG/LI still
    post (§8).
14. **`test_live_gate_still_exit2`** — missing env / base / ack / date each →
    exit 2, cited, no network, no queue write (Gate 10).
15. **`test_live_usage_error_prevalidation_exit2`** — >10-child IG package in
    live → exit 2 BEFORE any post, nothing written (§4.3).
16. **`test_real_asset_dryrun_two_rows_fidelity`** — DEFAULT dry-run over the real
    `2026-07-09-anarock-vs-propequity` seed: exactly 2 rows, IG container steps +
    LI Document steps, caption/link verbatim, placeholders present (Gate 7).
17. **`test_real_asset_dryrun_determinism`** — two DEFAULT dry-runs over the real
    seed byte-identical (Gate 8).
18. **`test_dryrun_raising_transport_still_exit0`** — dry-run with
    `RaisingTransport` → exit 0, full plan, no queue write (Gate 8, B8).
19. **`test_live_ast_single_urlopen_site`** — re-assert (or rely on the existing
    AST test) that `urlopen`/`urllib.request` occurs at exactly ONE call site after
    the Sprint-006 additions (B38).

## 13. Playwright click paths

N/A — this is a stdlib CLI + JSON tool with no browser surface. Verification is
`unittest` (§12) + the CLI probes in §11. (Stated explicitly so the Evaluator does
not expect a web UI.)

## 14. Non-goals (this sprint)

- No new adapter endpoints, no new API facts, no re-derivation of RESEARCH.md.
- No renderer / QA-gate / caption authoring changes; the tool never edits marketing
  copy or the UTM link.
- No OAuth acquisition/refresh; tokens come from `.env` (SETUP-CHECKLIST).
- No public-asset hosting/upload implementation; `PUBLIC_ASSET_BASE_URL` is assumed
  to serve the PNGs.
- No REAL network in any test or default run; live posting against real platforms
  is exercised only by the founder later.
- No queue-schema change (frozen, `schema_version "1"`).
- No LinkedIn company-page posting; member-profile only (R5-5).
- No skill/README update — that is Sprint 007.
- Facebook live remains a round-5-gap guess, not treated as verified.

## 15. Acceptance summary — conditions the build must satisfy

1. Live path replaces the honest no-op: in-scope `queued` rows post via the injected
   transport and transition `queued → posted` via `mark_posted.transition`, with
   `posted_date == --date` + the platform permalink recorded (Gate 2, §12.2/§12.3).
2. No-regress: targeted already-posted row → exit 1, queue byte-identical (Gate 3,
   §12.1a); re-run of a fully-posted week → exit 0, no re-post/regression (Gate 4,
   §12.1b).
3. Day-cap (B16): single-baseline + run-counter counting, breaching row refused
   exit 1 cited `day-cap`, prior posts persisted, processing stops (Gate 5,
   §12.4/§12.5).
4. Adapter refusals CLI-observable: IG container ERROR / rate-limit / unexpected
   response → exit 1, no transition, prior posts stand (Gate 6, §12.6/§12.7/§12.8).
5. Incremental persistence: earlier successful posts survive a later refusal
   (§12.8); live writes the QUEUE ONLY, never `publish-plan.json`; no secret leaks
   into any output or the queue (Gate 9, §12.9/§12.10).
6. Preconditions: live gate exit 2 unchanged (Gate 10, §12.14); >10-child
   pre-validation exit 2 before any post (§12.15); missing local upload bytes exit 2
   (Gate 11, §12.11).
7. Facebook gated in live: posts behind `--enable-facebook` (round-5-gap label
   kept), skipped with NOTICE + no cap consumption when OFF (§8, §12.12/§12.13).
8. End-to-end regression: real 2-row asset DEFAULT dry-run faithful + byte-identical
   on repeat; raising-transport dry-run exit 0 with full plan and no queue write
   (Gate 7, Gate 8, §12.16/§12.17/§12.18); FULL prior suite GREEN (Gate 1); AST
   single-`urlopen`-site test green (§12.19); `main()` never injects a transport.
