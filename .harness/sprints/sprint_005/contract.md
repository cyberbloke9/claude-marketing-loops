# Sprint 005 Contract — Facebook Page adapter (ROUND-5 GAP, gated)

Scope: spec §11 Sprint 005 + behaviors **B30, B31, B32** (Facebook Page adapter —
photos+feed best-documented-guess, gated behind `--enable-facebook` default OFF),
plus the step-level rendering pieces of B6/B7/B9/B10/B11/B17 as they apply to a
`facebook` row's plan `steps`. This sprint fills the `facebook` channel's `steps`
in the dry-run plan **only when `--enable-facebook` is passed**, and delivers a
mock-transport-executable adapter deriving plan+execute from ONE flow definition
(the anti-stub guarantee established in Sprint 003/004). When the flag is OFF
(the default), a `facebook` row is **skipped with a cited notice** — it does not
render steps, does not transition, and does not fail the run (IG/LI rows still
process).

Ground truth read (the ONLY authority for API facts — do not re-derive):
`RESEARCH.md` **R4-B5** and **R5-4**. Facts locked for this sprint:

- **R4-B5 (High): Facebook Pages Graph API publishing specifics DID NOT survive
  verification.** They are an explicit round-5 GAP. Therefore the entire Facebook
  publishing FLOW (endpoints, params, response shapes, permalink construction) is
  a **best-documented-guess pending live verification** — NOT an authoritative
  transcript. It MUST be labeled `round-5-gap` in both code and emitted output,
  and MUST be gated behind `--enable-facebook` (default OFF).
- **R5-4 (High): the ACCESS story is verified** — Standard Access suffices for
  the founder's own Page; `pages_manage_posts` + `pages_read_engagement` +
  `pages_show_list` with a **Page token**. This justifies member-owned Page
  posting via `graph.facebook.com` with `FB_PAGE_ID` + `FB_PAGE_TOKEN` (already
  the `_CHANNEL_TOKENS["facebook"]` entry). R5-4 verifies WHO may post, NOT the
  publishing endpoint mechanics — those remain the R4-B5 gap.
- **Reuse Instagram assets on Facebook (R4-A3): zero Facebook-specific creative.**
  The Facebook adapter consumes the SAME `package.attachments` PNGs, publicly
  hosted via `PUBLIC_ASSET_BASE_URL` (the `image_url` join, B11), exactly like
  Instagram — no new asset pipeline.

Blacklist / do-not-invent (spec §9, §7 anti-patterns): do NOT dress the FB flow
up as verified; do NOT invent a Graph API version prefix (`/vXX.0/`) — mirror the
IG adapter, which uses the bare host `https://graph.instagram.com` with no version
segment (B32 shows `POST /<FB_PAGE_ID>/photos` with no version). The permalink
shape is a fixed module constant, clearly marked a guess.

This is a stdlib CLI + JSON tool; there is NO browser surface (Playwright: N/A —
§13). Verification is `unittest` + CLI probes (§11). Python 3 stdlib only.

---

## 1. What this sprint delivers (the testable core)

A **`FacebookAdapter`** inside `tools/marketing-loops/publish_api.py` that
implements the round-5-gap photos+feed publishing guess (B32) and derives both its
dry-run plan and its mock-transport execution from a SINGLE flow definition
(`_fb_flow`), plus the **gating + skip-with-notice** control logic (B30, B31).

### 1.1 The Facebook photos+feed flow (B32) — best-documented-guess

Input = `package.attachments` (the ordered PNGs, N images), publicly hosted via
`PUBLIC_ASSET_BASE_URL` (B11 join, identical to Instagram). For N attachments the
flow is **N+1 HTTP calls**:

1. For each image `i` (1..N): `POST https://graph.facebook.com/<FB_PAGE_ID>/photos`
   with `url=<public image url i>`, `published=false`, `access_token` →
   response yields an unpublished **photo id**.
2. One `POST https://graph.facebook.com/<FB_PAGE_ID>/feed` with `message=<caption>`,
   `attached_media=<JSON array of {"media_fbid":"<photo id i>"}>`, `access_token` →
   response yields the **post id**.
3. **Permalink** is CONSTRUCTED from the post id (`_FB_PERMALINK_PREFIX + post_id`)
   — NO extra call. `_FB_PERMALINK_PREFIX = "https://www.facebook.com/"` is a fixed
   module constant marked a round-5-gap guess.

For the real 3-image carousel shape (N=3): **4 HTTP calls** (3 photos + 1 feed).

Delivered as both:
- **Plan** (dry-run, evaluator-facing via the CLI with `--enable-facebook`): for a
  `facebook` row it fills the row's `steps` with the FULL, faithful-to-the-guess,
  ordered list of the N+1 calls, rendered with named deterministic placeholders
  (B10) for dependent values (`<fb-photo-id-i>`, `<fb-post-id>`),
  `<PUBLIC_ASSET_BASE_URL>` for the image base when no concrete base is supplied
  (B11), `<FB_PAGE_ID>` for the page id (dry-run loads no `.env`), and
  `access_token=<REDACTED>` (B17) for the token.
- **Execute** (mock-transport, test-facing): the SAME `_fb_flow` walked against an
  injected `transport`, returning an `_FbResult(permalink, post_id)` on the happy
  path or an `AdapterRefusal` on an unexpected response.

### 1.2 Shared-flow guarantee (the anti-stub property — spec §7)

`FacebookAdapter.plan_steps` and `.execute` MUST both derive from the single
`_fb_flow` generator (one description of the ordered calls), so the dry-run plan
is literally produced by the same code path live execution walks — never a
hand-written parallel fiction. Proven by the **parity test** (§12.5). This is the
identical guarantee `_ig_flow` (Sprint 003) and `_li_document_flow` /
`_li_multiimage_flow` (Sprint 004) established; `_fb_flow` reuses the frozen
`_drive_plan` / `_drive_execute` drivers and the `_Step` model unchanged.

### 1.3 `execute()` is CLI-unreachable this sprint — by design, not a stub

Live posting + `queued → posted` transition + permalink recording + day-cap are
Sprint 006 (spec §11). Exactly as IG/LI shipped, `main()`/`run()` never inject a
mock transport, so a `--live` facebook row is an HONEST no-op:
- **Dry-run with `--enable-facebook`** wires `plan_steps` into `run()` and is fully
  evaluator-testable (this is the CLI-reachable half — unlike IG/LI, whose plan
  was reachable but execute was not; FB's plan is likewise reachable).
- **`FacebookAdapter.execute()`** is reached ONLY by this sprint's unit tests; its
  named downstream consumer is Sprint 006. It is covered by the happy-path /
  unexpected-response unit tests AND is the other half of the parity test.
- **`--live` with a `facebook` row in scope** (gate passing, `--enable-facebook`
  ON, real FB tokens) is an honest no-op stderr line naming Sprint 006 — ZERO
  network, no invented permalink, no queue flip (§7.2). With the flag OFF it is
  the skip-with-notice (§7.1).

---

## 2. Routes / screens / components affected

None (CLI). Affected code, all in `tools/marketing-loops/publish_api.py`:
- **New:** `FacebookAdapter`, `_fb_flow`, `_FbResult`, `_read_fb_id`,
  FB constants (`_FB_HOST`, `_FB_PERMALINK_PREFIX`, disabled-note / labels).
- **Changed:** `_ADAPTERS` registry (add `"facebook": FacebookAdapter()`);
  `_build_plan` (thread `enable_facebook`, branch facebook enabled/disabled);
  `run()` (pass `enable_facebook` into `_build_plan`, emit the skip NOTICE, and
  update the live no-op facebook branch); `_note_for`/`_CHANNEL_SPRINT` must no
  longer emit a "no adapter registered … facebook" string for any path.
- **New tests** appended to `tools/marketing-loops/tests/test_publish_api.py`.

No changes to `queue.py`, `utm.py`, `channels.py`, `schedule.py`, `captions.py`
(the frozen-module facebook extension already landed in Sprint 001).

---

## 3. Preconditions / guards (run in BOTH dry-run-enabled and execute)

- **G1 — attachments present.** A `facebook` row whose package has 0 `attachments`
  is an `AdapterUsageError` (exit 2, cited: `"facebook row (<slug>): no
  attachments to publish"`). NO upper-bound cap is asserted (the FB feed
  attachment limit is part of the unverified R4-B5 gap; do NOT invent a hard gate).
- **G2 — flag gate (B30/B31).** The FB adapter code paths (`plan_steps` / execute)
  are entered ONLY when `--enable-facebook` is ON. When OFF, the row is skipped
  with a notice (§7.1) BEFORE any guard runs — a disabled row with 0 attachments
  is still just skipped (no exit 2 from G1).
- **G3 — live tokens (B12a, unchanged).** In `--live` with `--enable-facebook` ON,
  the live gate already requires `FB_PAGE_ID` + `FB_PAGE_TOKEN` (existing
  `_live_gate` line — verify still correct). With the flag OFF the gate does NOT
  require FB tokens (facebook row is skipped, not posted).

---

## 4. The Facebook flow — exact endpoints, params, placeholders

`_FB_HOST = "https://graph.facebook.com"` (bare host, NO version prefix — mirrors
`_IG_HOST`, faithful to B32). Every FB step carries its fields as query `params`
(Graph API curl form, identical to the Instagram convention), `headers = {}`,
`payload = None` (like IG — FB sends form/query params, not a JSON body).

### 4.1 Photo upload step (×N), step i of N

| field | value |
|---|---|
| channel | `facebook` |
| label | `FB · upload unpublished photo {i}/{N}` |
| method | `POST` |
| url | `https://graph.facebook.com/<FB_PAGE_ID>/photos` |
| params | `access_token`, `published=false`, `url=<public image url i>` |
| headers | `{}` |
| payload | `null` |
| plan_response (stub) | `{"id": "<fb-photo-id-i>"}` |

- `<FB_PAGE_ID>`: dry-run uses the literal placeholder `<FB_PAGE_ID>`; execute uses
  `ctx["fb_page_id"]`.
- `access_token`: dry-run `<REDACTED>`; execute the real `ctx["fb_page_token"]`.
- `url` value: `image_url(base, slug, filename)` (B11) → dry-run without a base
  renders `<PUBLIC_ASSET_BASE_URL>/<slug>/<filename>`; `--public-asset-base-url`
  gives a concrete preview.
- `<fb-photo-id-i>`: `placeholder("fb-photo-id", i)` (1-indexed).

### 4.2 Feed post step (×1)

| field | value |
|---|---|
| channel | `facebook` |
| label | `FB · create feed post` |
| method | `POST` |
| url | `https://graph.facebook.com/<FB_PAGE_ID>/feed` |
| params | `access_token`, `attached_media=<json>`, `message=<caption verbatim>` |
| headers | `{}` |
| payload | `null` |
| plan_response (stub) | `{"id": "<fb-post-id>"}` |

- `attached_media` value = a compact deterministic JSON string of the ordered list
  `[{"media_fbid":"<fb-photo-id-1>"}, …, {"media_fbid":"<fb-photo-id-N>"}]`
  (`json.dumps(..., sort_keys=True, separators=(",",":"))`). Dry-run threads the
  `<fb-photo-id-i>` placeholders (from step-i `plan_response`) verbatim into this
  value — proving dependent-value flow (B10).
- `message` = `package.caption` VERBATIM (never edited, B5; contains a real
  newline for the real asset — the stdout renderer escapes it to `\n`, the machine
  JSON keeps it verbatim, mirroring the existing `_escape_stdout` rules).
- `<fb-post-id>`: `placeholder("fb-post-id")`.

### 4.3 Permalink construction (no call)

`_FB_PERMALINK_PREFIX = "https://www.facebook.com/"` (fixed module constant,
commented as a round-5-gap guess). `permalink = _FB_PERMALINK_PREFIX + post_id`
where `post_id` is the feed response `id`. Recorded to the queue in Sprint 006;
this sprint only returns it from `execute` (unit-tested).

### 4.4 `round-5-gap` labeling (B30, spec §7)

The unverified nature MUST be visible in emitted OUTPUT and in CODE:
- **Output:** the facebook row's `note` (in `publish-plan.json` AND the stdout
  plan) contains the substring `round-5-gap`. Exact enabled note (for a package
  with N attachments):
  `"facebook adapter (Page feed, graph.facebook.com; photos+feed flow); {TOTAL} HTTP
  calls; round-5-gap: best-documented-guess pending live verification (R4-B5)"`
  where **`{TOTAL}` = N + 1** (N photo uploads + 1 feed post). For the real
  3-image carousel (N=3) the note renders `"… ; 4 HTTP calls; round-5-gap: …"`.
- **Code:** the `FacebookAdapter` / `_fb_flow` docstrings and the FB constants
  block carry a `round-5-gap` / `R4-B5` comment.

---

## 5. Execute + response readers

- `_read_fb_id(resp, step_label)`: returns `resp["id"]`; on a missing/malformed
  `id` raises `AdapterRefusal("unexpected Facebook response for <step_label>")`
  (exit 1 domain refusal in a future live path; this sprint surfaces via unit
  tests). Reused for both the photo id and the post id.
- `_fb_flow(image_urls, caption, page_id, token)` is a generator yielding `_Step`
  and receiving each step's parsed response via `.send` — same protocol as
  `_ig_flow`. It reads each photo id from its response, builds `attached_media`
  from the collected ids, reads the post id, and `return`s
  `_FbResult(permalink=_FB_PERMALINK_PREFIX + post_id, post_id=post_id)`.
- `FacebookAdapter.plan_steps(row, package, base)` — signature identical to
  `InstagramAdapter.plan_steps`; runs G1, builds the flow with placeholder page id
  / `<REDACTED>` / `image_url(base, …)` urls, returns `_drive_plan(gen)`.
- `FacebookAdapter.execute(row, package, ctx, transport)` — runs G1, builds the
  flow with `ctx["fb_page_id"]` / `ctx["fb_page_token"]` and concrete image urls
  (`image_url(ctx["public_asset_base_url"], slug, filename)`), returns
  `_drive_execute(gen, transport)`. CLI-unreachable this sprint (§1.3).

No new transport code; `_drive_plan`, `_drive_execute`, `_Step`, `Transport`,
`RecordingTransport`, `RaisingTransport` are reused UNCHANGED.

---

## 6. Dry-run rendering

### 6.1 Enabled facebook row — exact stdout step block (per step)

Reuses the existing `_render_plan_stdout` template unchanged. Because FB steps
carry `headers = {}` and `payload = null`, each step renders EXACTLY like an
Instagram step (no `headers:` line, no `payload:` line) — the 4-line form:

```
    {j}. FB · upload unpublished photo {i}/{N}
       POST https://graph.facebook.com/<FB_PAGE_ID>/photos
       params: access_token=<REDACTED>, published=false, url=<PUBLIC_ASSET_BASE_URL>/<slug>/<filename>
```
(params rendered keys-SORTED by the existing `_render_step_params`.) The feed step
renders its `attached_media` and `message` params likewise (message newline →
`\n`). The row closes with `  note: <the §4.4 enabled note>`.

### 6.2 Disabled facebook row — see §7.1 (steps `[]`, disabled note).

Determinism (B9): no wall-clock; same inputs ⇒ byte-identical `publish-plan.json`
and stdout.

---

## 7. Skip-with-notice + gating (B31) — the sprint's core NEW behavior

This is the only genuinely new user-visible control behavior; it is pinned to
byte-level assertions.

### 7.1 Dry-run, `--enable-facebook` OFF (the DEFAULT) — facebook row in scope

- The facebook row **IS listed** in `publish-plan.json` and the stdout plan (kept
  for legibility + deterministic diffing), with:
  - `steps`: `[]` (empty — the adapter code is never entered),
  - `note` (exact): `"facebook adapter disabled (round-5-gap, unverified); pass
    --enable-facebook to render this row"`.
- `run()` appends to **stderr**, once per skipped facebook row (in `(slug,
  channel)` order), the exact NOTICE line:
  `"NOTICE: facebook row (<slug>) skipped: facebook adapter disabled; pass
  --enable-facebook (round-5-gap, unverified)"`.
- **Exit code 0.** Other rows (instagram / linkedin) render their full steps
  normally and are UNAFFECTED. The plan file IS written (dry-run always writes the
  plan). No queue write.

### 7.2 Live, `--enable-facebook` OFF — facebook row in scope

- After a passing gate (which does NOT require FB tokens when the flag is OFF), the
  live no-op loop emits the SAME skip NOTICE (§7.1) for the facebook row to stderr;
  other rows emit their existing "adapter ready … Sprint 006 … nothing posted"
  lines. Exit 0. ZERO network, no queue write. (Live posting is Sprint 006.)

### 7.3 Live, `--enable-facebook` ON — facebook row in scope

- Gate requires FB tokens (G3). On pass, the live no-op loop emits for the facebook
  row: `"facebook adapter ready (round-5-gap, unverified); live posting + queue
  transition land in Sprint 006; nothing posted"`. Exit 0, ZERO network.

### 7.4 `_note_for` regression

`_note_for` / `_CHANNEL_SPRINT` MUST NOT produce a `"no adapter registered for
channel 'facebook'"` string on ANY path — facebook now always resolves to either
the disabled note (§7.1) or the enabled adapter note (§4.4). (youtube still uses
`_note_for`; unchanged.)

---

## 8. `_build_plan` / `run` threading + non-regression

- **B-Thread.** `_build_plan(...)` gains a keyword param `enable_facebook=False`
  (default preserves current callers). Branch order inside the row loop:
  1. `channel == "facebook"` and NOT `enable_facebook` → `steps=[]`, disabled note.
  2. `channel == "facebook"` and `enable_facebook` → load package, run
     `FacebookAdapter.plan_steps`, adapter note.
  3. `channel == "linkedin"` → (existing) LinkedIn branch.
  4. adapter present (instagram) → (existing) IG branch.
  5. else (youtube) → `_note_for`.
  `run()` passes `enable_facebook=enable_facebook` into `_build_plan` and, in
  dry-run, emits the §7.1 stderr NOTICE for each in-scope disabled facebook row.
- **NON-REGRESSION (named, mandatory).** The DEFAULT dry-run over the REAL 2-row
  asset (`--week 2026-W28`, no facebook in scope, `enable_facebook` default False)
  MUST produce a `publish-plan.json` **byte-identical** to what Sprint 004 emitted
  (adding facebook to the registry + threading the flag must NOT perturb the IG or
  LI rows). Proven by §12.7 and by the full pre-existing suite staying GREEN.
- Registry: `_ADAPTERS = {"instagram": …, "linkedin": …, "facebook":
  FacebookAdapter()}`.

---

## 9. Determinism, secrets, safety

- **No wall-clock anywhere** (B9). FB permalink prefix + graph host are fixed
  constants; no version derived from time. Same inputs ⇒ byte-identical output.
- **Secrets (B17).** `FB_PAGE_TOKEN` NEVER appears in stdout or
  `publish-plan.json`: every `access_token` param renders `access_token=<REDACTED>`
  in dry-run via the existing `redact_token_param` convention. Testable: a sentinel
  token string is ABSENT from all emitted dry-run output (§12.6).
- **Persistence.** Dry-run writes ONLY `content/publish-plan.json`. No queue write
  this sprint (live transition is Sprint 006). `.env` stays gitignored; no secret
  written to any tracked file.

---

## 10. States that must exist (spec §6)

- **Feature-flag OFF (default):** facebook row skipped with cited notice, listed
  with `steps:[]` + disabled note, exit 0, other rows proceed (§7.1).
- **Feature-flag ON, dry-run:** facebook row renders full N+1 photos+feed steps,
  `round-5-gap` note, exit 0.
- **Feature-flag ON, execute (unit only):** happy path returns `_FbResult` with
  constructed permalink; unexpected response → `AdapterRefusal`.
- **Invalid input:** enabled facebook row with 0 attachments → exit 2, cited (G1).
- **Live no-op:** facebook row (flag on or off) posts NOTHING, ZERO network (§7.2,
  §7.3).
- **Non-regression:** real 2-row asset dry-run byte-identical to Sprint 004.

---

## 11. Verification gate (commands + expected output)

Run from repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`.

- **Gate 1 — full regression suite GREEN.**
  `python3 -m unittest discover -s tools/marketing-loops/tests -v`
  Expected: OK, 0 failures / 0 errors; the pre-existing count (Sprint 004 = 350)
  PLUS the new Sprint-005 facebook tests; no test skipped to pass.

- **Gate 2 — flag OFF skip (fixture with a facebook row).** Seed a throwaway
  workspace whose queue has an IG row + a facebook row (both `queued`, same week),
  run the CLI dry-run with NO `--enable-facebook`:
  `publish_api.py --week <W> --queue <fixtureq>`
  Expected: exit 0; stdout plan lists BOTH rows; the facebook row shows
  `steps: 0` and note `facebook adapter disabled (round-5-gap, unverified); pass
  --enable-facebook to render this row`; stderr contains the exact
  `NOTICE: facebook row (<slug>) skipped: …` line; the IG row renders its full 8
  steps; `publish-plan.json` facebook row has `"steps": []`.

- **Gate 3 — flag ON renders the flow.** Same fixture, add `--enable-facebook`:
  Expected: exit 0; facebook row shows `steps: {N+1}` (4 for a 3-image package);
  step 1 label `FB · upload unpublished photo 1/3`, url
  `https://graph.facebook.com/<FB_PAGE_ID>/photos`, params include
  `access_token=<REDACTED>`, `published=false`,
  `url=<PUBLIC_ASSET_BASE_URL>/<slug>/format-01.png`; final step label
  `FB · create feed post`, url `.../<FB_PAGE_ID>/feed`, `attached_media` param
  contains `<fb-photo-id-1>`…`<fb-photo-id-3>`; row note contains `round-5-gap`.

- **Gate 4 — no invented version / no false fidelity.**
  `grep -n 'graph.facebook.com/v[0-9]' tools/marketing-loops/publish_api.py` → prints
  NOTHING (no version prefix). `grep -c 'round-5-gap' tools/marketing-loops/publish_api.py`
  → ≥ 1. The facebook note in a flag-ON `publish-plan.json` contains
  `best-documented-guess`.

- **Gate 5 — no secret leak (flag ON, concrete base + sentinel).** With a fixture
  package + a sentinel token, run dry-run `--enable-facebook`; assert the sentinel
  string is ABSENT from stdout AND from `publish-plan.json` (dry-run loads no
  `.env`, so tokens render `<REDACTED>` regardless — the test also drives
  `execute` with a `RecordingTransport` and asserts the plan output never contains
  the token used).

- **Gate 6 — non-regression (real asset byte-identical).** Load the saved
  `publish-plan.json` golden from Sprint 004 for `--week 2026-W28` (the baseline
  before facebook was added). Run the Sprint 005 generator with `--week 2026-W28`
  and NO `--enable-facebook` flag (so facebook rows are not in scope). Assert the
  emitted `publish-plan.json` is byte-identical to the Sprint-004 golden. This
  confirms adding facebook to `_ADAPTERS` and threading `enable_facebook` does not
  perturb the IG/LI rows. (If no Sprint-004 golden file is checked in, capture the
  DEFAULT dry-run output on the pre-Sprint-005 tree first and treat that as the
  golden; the test compares the Sprint-005 output against that saved baseline.)

- **Gate 7 — determinism.** Run the flag-ON facebook fixture dry-run twice; the two
  `publish-plan.json` files are byte-identical.

- **Gate 8 — live no-op (flag ON + flag OFF).** With a fixture facebook row and a
  passing gate (`.env` with FB tokens + base + `--i-have-verified-dry-run` +
  `--date`), run `--live --enable-facebook`: exit 0, stderr shows the "adapter
  ready … Sprint 006 … nothing posted" facebook line, ZERO network (a
  `RaisingTransport` via the execute unit test proves no socket); queue file
  unchanged. With flag OFF: the skip NOTICE, exit 0.

## 12. Unit-test scenarios (appended to `test_publish_api.py`)

Each hermetic (throwaway workspace via the existing `_seed_workspace`, extended to
allow a facebook row + package). No real socket in any test.

1. **`test_facebook_disabled_skip_dryrun`** — facebook row + flag OFF: exit 0,
   plan lists the row with `steps == []` + exact disabled note, stderr has the
   exact NOTICE line, IG row still renders 8 steps.
2. **`test_facebook_enabled_dryrun_fidelity`** — flag ON, 3-image package: N+1=4
   steps; exact labels/urls/params for photo step 1 and the feed step; params
   keys sorted; `attached_media` threads `<fb-photo-id-1..3>`; note has
   `round-5-gap` + `best-documented-guess`.
3. **`test_facebook_zero_attachments_usage_error`** — flag ON, 0 attachments:
   exit 2, cited `no attachments`; NO plan written.
4. **`test_facebook_execute_happy_path`** — `FacebookAdapter.execute` against a
   `RecordingTransport` with canned photo ids + post id: returns `_FbResult`,
   permalink == `https://www.facebook.com/<post_id>`, recorded calls = N photos +
   1 feed in order, feed `attached_media` carries the real photo ids.
5. **`test_facebook_parity_plan_matches_transport`** — `len(plan_steps) ==
   len(recorded execute calls)`, same methods + url paths (anti-stub proof).
6. **`test_facebook_no_secret_in_output`** — sentinel token via execute
   RecordingTransport; dry-run output (stdout + plan JSON) never contains it;
   redaction token present.
7. **`test_facebook_non_regression_real_asset`** — DEFAULT dry-run over the real
   2-row seed byte-identical before/after facebook registry addition (no facebook
   in scope).
8. **`test_facebook_unexpected_response_refusal`** — feed response missing `id` →
   `AdapterRefusal`.
9. **`test_facebook_live_noop_flag_on`** — `--live --enable-facebook` passing gate,
   facebook row → stderr "adapter ready … Sprint 006 … nothing posted", exit 0,
   queue unchanged, no network (RaisingTransport-backed execute untouched).
10. **`test_facebook_determinism_flag_on`** — two flag-ON dry-runs byte-identical.

## 13. Playwright click paths

N/A — this is a stdlib CLI + JSON tool with no browser surface. Verification is
`unittest` (§12) + the CLI probes in §11. (Stated explicitly so the Evaluator does
not expect a web UI.)

## 14. Non-goals (this sprint)

- No live posting, no `queued → posted` transition, no permalink WRITE to the
  queue, no day-cap enforcement — all Sprint 006. FB `execute` is unit-only.
- No treating the FB flow as verified: it is a round-5-gap guess (R4-B5); the
  contract does NOT assert its endpoints are canonical.
- No FB-specific creative or new asset pipeline (reuse IG PNGs, R4-A3).
- No Instagram / LinkedIn behavior change (non-regression is mandatory, §8).
- No frozen-module edits (facebook was added to utm/channels/schedule in Sprint
  001).
- No invented Graph API version prefix; no upper attachment cap gate (unverified).

## 15. Acceptance summary — conditions the build must satisfy

1. `FacebookAdapter` + `_fb_flow` + `_FbResult` + `_read_fb_id` shipped; plan +
   execute derive from the SINGLE `_fb_flow` (parity test passes).
2. Flag OFF (default): facebook row skipped with the EXACT disabled note + EXACT
   stderr NOTICE, `steps:[]`, exit 0, other rows unaffected (Gate 2, §12.1).
3. Flag ON: full N+1 photos+feed plan, faithful to B32, `round-5-gap` labeled in
   output + code, no invented version prefix (Gate 3, Gate 4, §12.2).
4. 0-attachment enabled facebook row → exit 2 cited; no upper-cap invented (§12.3).
5. Secrets never leak; determinism byte-identical (Gate 5, Gate 7, §12.6, §12.10).
6. Non-regression: real 2-row asset dry-run byte-identical to Sprint 004; FULL
   prior suite GREEN (Gate 1, Gate 6, §12.7).
7. Live facebook row (flag on/off) is an honest no-op: ZERO network, no queue
   write, cited Sprint-006 / skip line (Gate 8, §12.9).
