# Sprint 003 Contract — Instagram adapter (verified: R4-B1/B2/B3, R5-1/R5-3)

Scope: spec §11 Sprint 003 + behaviors B19–B24 (Instagram adapter), plus the
step-level pieces of B6/B7/B9/B10/B17 as they apply to a NON-empty `steps` list.
This sprint fills the Instagram channel's `steps` in the dry-run plan (the
skeleton from Sprint 002 shipped every row with `steps: []`) and delivers a
mock-transport-executable adapter proving the full container flow.

Ground truth read (the ONLY authority for API facts — do not re-derive):
`RESEARCH.md` R4-B1/B2/B3 and R5-1/R5-3. Verified facts locked for this sprint:
- Host `graph.instagram.com` (Instagram Login flavor, no Facebook Page).
- Two-step container model: `POST /<IG_ID>/media` → `POST /<IG_ID>/media_publish`
  with `creation_id`; poll `status_code`; carousels ≤10 children
  (`is_carousel_item=true`) + parent (`media_type=CAROUSEL`).
- Rate limit is a DISCREPANCY (50 vs 100), NOT a settled gate — check
  `content_publishing_limit` at runtime, never hard-code either number (R4-B3).
- **BLACKLIST (binding, RESEARCH §9):** the permission name is
  `instagram_business_content_publish` — the `…_content_publishing` variant is
  REFUTED and MUST NOT appear anywhere in code, comments, or output. The publish
  endpoint is `media_publish`, never `media_publishing`. No invented endpoints.

This is a stdlib CLI + JSON tool; there is NO browser surface (Playwright: N/A —
§13). Verification is `unittest` + CLI probes (§11).

---

## 1. What this sprint delivers (the testable core)

An **Instagram adapter** inside `tools/marketing-loops/publish_api.py` that:

1. **Plans** (dry-run, evaluator-facing via the CLI): for an `instagram` queue
   row it fills the row's `steps` array with the FULL, faithful, ordered list of
   HTTP calls the container flow makes (B19–B24), rendered with named
   deterministic placeholders (B10) for dependent values and `<REDACTED>` (B17)
   for the access token. Reached from `run()` in dry-run — the primary
   deliverable an evaluator inspects.
2. **Executes** (mock-transport, test-facing): the SAME flow definition, walked
   against an injected `transport`, returning a typed result (permalink) on the
   happy path or a typed refusal on the container-error / rate-limit paths. This
   is unit-tested with `RecordingTransport` per spec §11's Sprint-003 scenarios.

### 1.1 Shared-flow guarantee (the anti-stub property — spec §7 anti-patterns)

`plan_steps` and `execute` MUST derive from a SINGLE flow definition (one
generator/function describing the ordered calls), so the dry-run plan is
literally produced by the same code path live execution walks — never a
hand-written parallel fiction. This is proven by the **parity test** (§8.3): for
one row, the dry-run plan's step sequence is 1:1 with the transport-call sequence
produced by executing the adapter against a mock, under the canonical execution
(container `status_code == FINISHED` on the first poll). Same count, same order,
same `method`, same URL endpoint (placeholders in the plan resolve to the mock's
concrete values).

### 1.2 `execute()` is CLI-unreachable this sprint — by design, not a stub

Live posting + `queued → posted` transition + permalink recording + day-cap are
Sprint 006 (spec §11). The live CLI cannot post this sprint: `main()` never
injects a mock transport, so `--live` would use the real `Transport` (real
network) — forbidden (§9 "no live network in this deliverable"). Therefore:

- **Dry-run** wires `plan_steps` into `run()` and is fully evaluator-testable
  from the CLI (§11 gate clauses).
- **`execute()`** is reached ONLY by the unit tests this sprint; its named
  downstream consumer is Sprint 006 (which wires it into `run()`'s live path +
  the queue transition). It is NOT dead code: it is covered by the happy /
  container-error / rate-limit unit tests AND is the other half of the shared
  flow the parity test exercises.
- **`--live` with an `instagram` row in scope** (gate passing, real IG tokens
  present) is an HONEST no-op this sprint: after the passing gate it emits a
  cited stderr notice `"instagram adapter ready; live posting + queue transition
  land in Sprint 006; nothing posted"`, makes ZERO network calls, writes no
  queue, invents no permalink, flips no row, and exits 0. (This replaces Sprint
  002's generic "no adapter registered … Sprint 003+" notice for the instagram
  channel; see §7 conscious-update.)

---

## 2. Files affected

Production (edit — the ONLY production file touched):
- `tools/marketing-loops/publish_api.py` — add the Instagram adapter (flow
  definition, `plan_steps`, `execute`, typed result/refusal classes), register
  it in the adapter registry, wire `plan_steps` into `run()`'s dry-run dispatch,
  and update `run()`'s live-dispatch notice for the instagram channel (§1.2). The
  frozen `run()`/`main()` signatures, `Transport`/`Response`/`Recording`/
  `RaisingTransport`, and the plan envelope shape from Sprint 002 are UNCHANGED
  (adapters conform to them; no reshaping).

Tests (edit):
- `tools/marketing-loops/tests/test_publish_api.py` — add the Instagram adapter
  suite (§8) AND consciously update the two Sprint-002 assertions that froze the
  instagram row as `steps: 0` + "no adapter" (§7). Mocked transport only.

No edits to any frozen module (`queue.py`, `utm.py`, `channels.py`,
`schedule.py`, `captions.py`) and no edits to any OTHER existing test. If BUILD
finds a frozen module needs changing to satisfy this contract, that is a finding
to disclose — none is expected.

---

## 3. Package fields consumed (B5) — instagram only

The Instagram adapter reads these fields from the row's package JSON (at
`row["package_path"]`, e.g. `content/<slug>/publish/instagram.json`):

- `attachments` — ordered list of repo-relative PNG paths. Carousel children in
  order. The image filename for the public URL is `Path(attachment).name` (e.g.
  `content/<slug>/render/format-01.png` → `format-01.png`).
- `caption` — the post caption, used VERBATIM (includes the UTM link already;
  the tool NEVER edits it — B5). Multi-line is expected (the real asset's caption
  contains `\n`).
- `slug` — for the `image_url` join (fall back to the queue row's `slug` if the
  package omits it; the real package includes it).

The real asset (`content/2026-07-09-anarock-vs-propequity/publish/instagram.json`)
has 3 attachments (`format-01.png`, `format-02.png`, `format-03.png`) → a 3-image
carousel. Field consumption for OTHER channels stays deferred (linkedin=004,
facebook=005): those rows keep `steps: []` this sprint.

### 3.1 Attachment-count validation (B20/B2) — both modes, build time

- `len(attachments) == 0` → exit 2, cited `"instagram row (<slug>): no
  attachments to publish"`. No plan/queue write.
- `len(attachments) > 10` → exit 2, cited `"instagram carousel exceeds 10
  children (got <n>): Instagram allows at most 10 (R4-B2)"`. No plan/queue write.
- This validation runs when the plan is BUILT (dry-run) AND when the adapter
  executes (live/tests), so a >10 package fails identically in both. Testable in
  dry-run with a fixture package holding 11 attachments.

---

## 4. The Instagram container flow — exact call sequence (B19–B24)

For a carousel of N images (the real asset N=3), the flow — and thus the ordered
`steps` in the plan AND the ordered transport calls in `execute` — is EXACTLY:

Common rendering rules (frozen):
- **Host / path segment id.** All URLs are on `https://graph.instagram.com`. The
  account id path segment is `<IG_USER_ID>`. In dry-run no `.env` is loaded, so
  it renders as the literal placeholder `<IG_USER_ID>` (deterministic; never a
  secret in the plan). In live/execute it is the real env value in the URL.
- **Access token.** `access_token` is a QUERY `params` field, NOT an
  `Authorization` header. IG calls send NO auth header (`headers: {}`). In every
  rendered step the token value is `<REDACTED>` (B17); in execute the real token
  is sent but the recorded/emitted plan never carries it.
- **`params` vs `payload`.** Faithful to Meta's documented curl form, IG Graph
  calls carry their fields as query `params`; `payload` is `null` for every IG
  step. `params` keys are rendered sorted (deterministic).
- **`image_url`.** Built via the Sprint-002 `image_url(base, slug, filename)`
  helper = `<base>/<slug>/<filename>` (single trailing slash on base collapsed).
  In dry-run without `--public-asset-base-url`, `base` is `None` → the literal
  `<PUBLIC_ASSET_BASE_URL>` placeholder (B11). With `--public-asset-base-url` a
  concrete preview is rendered.

| # | label | method | url | params (sorted; token=`<REDACTED>`) |
|---|---|---|---|---|
| 1 | `IG · check content_publishing_limit` | GET | `…/<IG_USER_ID>/content_publishing_limit` | `access_token`, `fields=quota_usage,quota_total` |
| 2..N+1 | `IG · create child container i/N` | POST | `…/<IG_USER_ID>/media` | `access_token`, `image_url=<url i>`, `is_carousel_item=true` |
| N+2 | `IG · create parent carousel container` | POST | `…/<IG_USER_ID>/media` | `access_token`, `caption=<caption>`, `children=<ids>`, `media_type=CAROUSEL` |
| N+3 | `IG · poll container status` | GET | `…/<ig-parent-creation-id>` | `access_token`, `fields=status_code` |
| N+4 | `IG · publish media` | POST | `…/<IG_USER_ID>/media_publish` | `access_token`, `creation_id=<ig-parent-creation-id>` |
| N+5 | `IG · fetch permalink` | GET | `…/<ig-media-id>` | `access_token`, `fields=permalink` |

For N=3 that is **8 steps** total. `…` = `https://graph.instagram.com`.

### 4.1 Named placeholders (B10) — the exact set
- Child container id from step i's response → `<ig-child-container-id-i>`
  (1-indexed). Used in step N+2's `children` param as the comma-joined list
  `<ig-child-container-id-1>,<ig-child-container-id-2>,<ig-child-container-id-3>`.
- Parent creation id from step N+2's response → `<ig-parent-creation-id>`. Used
  in the poll URL (step N+3) and the `creation_id` param (step N+4).
- Published media id from step N+4's response → `<ig-media-id>`. Used in the
  permalink-fetch URL (step N+5).
These are the plan's dependent-value placeholders. In `execute` they are the
real values returned by the transport.

### 4.2 Single-image degrade (B21)
When `len(attachments) == 1`: step 2 is a single `POST …/media` with
`image_url` + `access_token` and NEITHER `is_carousel_item` NOR
`media_type=CAROUSEL`; there is NO separate parent step (the one container IS the
publishable media). Sequence: limit-check → create container → poll → publish →
permalink (6 steps). Supported and unit-tested, but the real asset is a 3-image
carousel (the primary path).

### 4.3 Polling (B22, spec §6 loading state)
- Dry-run renders EXACTLY ONE poll step (deterministic). Its `label` notes the
  bounded repeat: `IG · poll container status` — the plan cannot render a
  data-dependent poll count without a clock/network, so one representative step
  is emitted (disclosed decision).
- `execute` polls `GET …/<parent-id>?fields=status_code` up to a fixed module
  constant `MAX_POLL_ATTEMPTS` (default 30) until `status_code == "FINISHED"`.
  - `status_code == "ERROR"` or `"EXPIRED"` → container-error refusal (exit 1,
    §5). 
  - Reaching `MAX_POLL_ATTEMPTS` without `FINISHED` → container-error refusal
    (exit 1, cited "container did not finish after N polls").
  - NO wall-clock read anywhere (no `time.time`/`datetime.now`). If a delay
    between polls is used it MUST be via an injectable no-op-in-tests seam
    (default `time.sleep(POLL_DELAY_SECONDS)`, tests pass a no-op); tests never
    block. The CANONICAL execution the parity test uses returns `FINISHED` on the
    first poll (one poll call), making plan-steps count == transport-calls count.

### 4.4 Rate-limit pre-check (B19, R4-B3)
- Dry-run ALWAYS renders step 1 (the limit check) and the full happy flow; it
  merely annotates (no branch — dry-run has no response). The 50-vs-100
  discrepancy is NOT hard-coded as a gate.
- `execute` reads the response and, if `quota_usage >= quota_total`, takes the
  rate-limit-exceeded refusal (exit 1, §5, cited). Otherwise proceeds.

---

## 5. Adapter result / refusal contract (exit-code mapping — B41/B42)

`execute(row, package, ctx, transport)` returns / raises:
- **Success** → a small result object (plain class / `SimpleNamespace`) with at
  least `permalink` (str, the value written to the queue in Sprint 006) and
  `media_id` (str). Built from the transport responses.
- **Domain refusal (exit 1)** → raise a typed `AdapterRefusal(message)`:
  container `status_code == ERROR/EXPIRED` or poll-exhausted; rate-limit
  exceeded. `run()`/Sprint 006 map this to exit 1, cited on stderr.
- **Usage / precondition (exit 2)** → raise a typed `AdapterUsageError(message)`:
  0 or >10 attachments (§3.1). Enforced at BUILD time in dry-run too (so dry-run
  exits 2 on a >10 package, no plan written).

The two exception types are distinct so the caller maps them to the right exit
code without string-matching. This sprint they are raised and unit-tested;
Sprint 006 wires the exit-1/exit-2 mapping into the live `run()` path.

---

## 6. Response shapes `execute()` parses (documented assumptions — live-pending)

The dry-run PLAN emits faithful REQUESTS (§4). `execute()` parses RESPONSES; the
canned mock responses in tests MUST match the parse the adapter performs. Because
live verification is deferred (no credentials yet), these response shapes are
DOCUMENTED ASSUMPTIONS, marked live-pending in the module, and the tests' canned
payloads are constructed to match them exactly:

- **`content_publishing_limit`** → the adapter reads `quota_usage` and
  `quota_total`. ASSUMPTION: with `fields=quota_usage,quota_total` the response
  is the flattened form `{"data": [{"quota_usage": <int>, "quota_total": <int>}]}`
  (Meta returns limit data under `data[0]`). The adapter reads
  `resp.json()["data"][0]["quota_usage"]` / `["quota_total"]`. If a founder's
  live response differs (e.g. `config.quota_total` nesting, R4-B3), ONLY this
  parse changes — it is isolated in one helper and flagged live-pending. The
  mock returns this flattened shape.
- **`POST /media` (child or parent)** → `{"id": "<container-id>"}`; adapter reads
  `resp.json()["id"]`.
- **`POST /media_publish`** → `{"id": "<media-id>"}`; adapter reads
  `["id"]`.
- **`GET /<parent-id>?fields=status_code`** → `{"status_code": "FINISHED"}` (or
  `IN_PROGRESS`/`ERROR`/`EXPIRED`); adapter reads `["status_code"]`.
- **`GET /<media-id>?fields=permalink`** → `{"permalink": "<url>"}`; adapter
  reads `["permalink"]` and returns it as the row permalink.

A response missing an expected key (e.g. no `id`) → treated as a container-error
refusal (exit 1) rather than an uncaught `KeyError` (cited "unexpected Instagram
response for <step>"). These parse choices are unit-tested against the mock.

---

## 7. Conscious Sprint-002 test update (enumerated — the regression surface)

Filling the instagram `steps` CHANGES the instagram row rendering that the Sprint
002 suite froze (`steps: 0` + the `"no adapter registered … Sprint 003+"` note).
This is a deliberate, enumerated update (analogous to B37), NOT a regression:

- **Machine-plan assertion (002 gate-3 shape):** the instagram row's `steps`
  length changes from `0` to `8` (3-image carousel) and its `note` changes from
  `"no adapter registered for channel 'instagram' (lands in Sprint 003+)"` to the
  new instagram note (§7.1). The BUILD updates exactly the 002 test assertions
  that hard-coded the instagram row's `steps == []` / `steps: 0` and its old
  note.
- **Stdout-template assertion (002 §7.2 frozen 2-row template):** the instagram
  row block now renders 8 steps (§7.2 template below). The 002 test that asserted
  the instagram block line-for-line is updated to the new block.
- **UNCHANGED (must stay byte-identical):** the LinkedIn row keeps `steps: 0` and
  the note `"no adapter registered for channel 'linkedin' (lands in Sprint
  004+)"`; the envelope keys (`schema_version`, `week`, `mode`, `rows`), the
  `(slug, channel)` ordering, determinism, the empty-state behavior, the live
  gate, the transport seam, the helpers, and every OTHER 002 assertion are
  untouched. Enumerate any additional 002 sites touched in `generator_trace.log`;
  do not stop at the two named above if a grep finds more.

After the update, BOTH full suites end GREEN (§11 gate clause 2).

### 7.1 The instagram row `note` (replaces the "no adapter" note)
`"instagram adapter (Instagram Login, graph.instagram.com); <N> HTTP calls;
verified R4-B2/R4-B3/R5-3"` where `<N>` is `len(steps)`. Single source shared by
the machine `note` field and the stdout `note:` line (no drift — same rule as
Sprint 002's `_note_for`).

### 7.2 Exact stdout per-step template (freezing 002's deferred per-step render)

The stdout plan (dry-run) renders each row block as follows. For the real asset
`--week 2026-W28` with NO `--public-asset-base-url` (base is the placeholder),
the instagram block is EXACTLY (leading spaces significant):

```
Row 1/2: 2026-07-09-anarock-vs-propequity (instagram)
  package: content/2026-07-09-anarock-vs-propequity/publish/instagram.json
  steps: 8
    1. IG · check content_publishing_limit
       GET https://graph.instagram.com/<IG_USER_ID>/content_publishing_limit
       params: access_token=<REDACTED>, fields=quota_usage,quota_total
    2. IG · create child container 1/3
       POST https://graph.instagram.com/<IG_USER_ID>/media
       params: access_token=<REDACTED>, image_url=<PUBLIC_ASSET_BASE_URL>/2026-07-09-anarock-vs-propequity/format-01.png, is_carousel_item=true
    3. IG · create child container 2/3
       POST https://graph.instagram.com/<IG_USER_ID>/media
       params: access_token=<REDACTED>, image_url=<PUBLIC_ASSET_BASE_URL>/2026-07-09-anarock-vs-propequity/format-02.png, is_carousel_item=true
    4. IG · create child container 3/3
       POST https://graph.instagram.com/<IG_USER_ID>/media
       params: access_token=<REDACTED>, image_url=<PUBLIC_ASSET_BASE_URL>/2026-07-09-anarock-vs-propequity/format-03.png, is_carousel_item=true
    5. IG · create parent carousel container
       POST https://graph.instagram.com/<IG_USER_ID>/media
       params: access_token=<REDACTED>, caption=<caption>, children=<ig-child-container-id-1>,<ig-child-container-id-2>,<ig-child-container-id-3>, media_type=CAROUSEL
    6. IG · poll container status
       GET https://graph.instagram.com/<ig-parent-creation-id>
       params: access_token=<REDACTED>, fields=status_code
    7. IG · publish media
       POST https://graph.instagram.com/<IG_USER_ID>/media_publish
       params: access_token=<REDACTED>, creation_id=<ig-parent-creation-id>
    8. IG · fetch permalink
       GET https://graph.instagram.com/<ig-media-id>
       params: access_token=<REDACTED>, fields=permalink
  note: instagram adapter (Instagram Login, graph.instagram.com); 8 HTTP calls; verified R4-B2/R4-B3/R5-3
```

Per-step stdout format rules (frozen):
- Step line: `    <i>. <label>` (4 spaces, 1-indexed number, `. `, label).
- Method+url line: `       <METHOD> <url>` (7 spaces).
- Params line: `       params: <k1=v1, k2=v2, …>` (7 spaces), keys SORTED,
  joined by `, `. A step with empty `params` renders `       params: (none)`.
  `payload` is `null` for every IG step, so no payload line is rendered for IG
  (if a future adapter has a non-null payload, its render is defined there).
- **Caption newline rule (stdout only):** the `caption` param VALUE has its
  newlines escaped to the literal two-character sequence `\n` in stdout (so the
  line-oriented template stays intact and byte-assertable). In the machine JSON
  the caption is stored VERBATIM (real `\n` preserved, B5). The template above
  shows `caption=<caption>` as a stand-in; the real rendered value is the escaped
  single-line caption string. The Evaluator asserting stdout line-for-line uses
  the escaped form; asserting the JSON uses the verbatim form.
- The row header, `package:`, `steps: <n>`, and `note:` lines keep the Sprint-002
  format; only the per-step block (between `steps:` and `note:`) is new.
- Blocks separated by one blank line; final line `Plan written to <plan_path>`
  (Sprint-002 rule, unchanged). The LinkedIn block (row 2) is byte-identical to
  Sprint 002 (`steps: 0`, its note, no per-step lines).

### 7.3 Machine-plan step objects (the 7 frozen keys — Sprint 002 §7.1)
Each step object has EXACTLY: `channel` (`"instagram"`), `label`, `method`,
`url`, `params` (object; token value `<REDACTED>`; `image_url`/`children`/
`caption`/`fields`/etc. as strings; caption VERBATIM here), `headers` (`{}` for
IG), `payload` (`null` for IG). `steps` element ORDER is emission order (not
sorted); object KEYS are sorted by the deterministic writer. Byte-identical on
repeat (§11 gate clause 4).

---

## 8. Tests (mocked transport only — spec §11 Sprint-003 scenarios)

Add to `tools/marketing-loops/tests/test_publish_api.py`. NO real network in any
test (B39). All adapter execution uses `RecordingTransport` with canned
responses; no test opens a socket.

### 8.1 Dry-run plan fidelity (B19–B24, R4-B2) — via `run()` / CLI
- Dry-run over the real asset (`--week 2026-W28`) → instagram row has 8 steps in
  the exact order/shape of §4; each step's `params` token is `<REDACTED>`;
  `image_url`s use the `<PUBLIC_ASSET_BASE_URL>` placeholder (no base flag);
  `children` uses the comma-joined child placeholders; `headers == {}`,
  `payload is None`. LinkedIn row still `steps: []`.
- With `--public-asset-base-url https://assets.example/social-assets` the
  `image_url`s render concretely as
  `https://assets.example/social-assets/2026-07-09-anarock-vs-propequity/format-01.png`
  (join rule verified).
- Machine plan byte-identical on repeat (determinism); no wall-clock.
- Caption in the machine JSON is VERBATIM (contains real `\n`); in stdout it is
  the `\n`-escaped single-line form.

### 8.2 Adapter `execute` — happy carousel path
- `RecordingTransport(responses=[limit-ok, child_1, child_2, child_3, parent,
  status-FINISHED, media, permalink])` where limit-ok =
  `{"data":[{"quota_usage":1,"quota_total":50}]}`, children/parent/media =
  `{"id":"…"}`, status = `{"status_code":"FINISHED"}`, permalink =
  `{"permalink":"https://www.instagram.com/p/ABC/"}`.
- `execute(...)` returns a result with `permalink ==
  "https://www.instagram.com/p/ABC/"` and `media_id` set.
- Assert the transport `.calls` sequence == the §4 flow: 8 calls, correct
  methods/URLs; the real access token appears in EVERY call's params (proving
  live sends it) while NEVER appearing in the emitted plan (proving redaction is
  a render-time concern).
- Child ids from responses are threaded into the parent `children` param and the
  parent id into the poll URL + `creation_id` (dependent-value wiring).

### 8.3 Parity test (the shared-flow proof, §1.1)
- For the real instagram row, obtain the dry-run `plan_steps` AND execute the
  adapter against a canonical mock (FINISHED on first poll). Assert
  `len(plan_steps) == len(transport.calls)` and, per index, same `method` and
  same URL PATH (plan placeholders resolve to the mock's concrete ids). This is
  the proof the plan is not a hand-written fiction.

### 8.4 Container-error path (exit 1)
- Mock returns `status_code == "ERROR"` (and separately `"EXPIRED"`) →
  `execute` raises `AdapterRefusal`; the message cites the container error. No
  permalink returned. (Poll-exhausted: mock returns `IN_PROGRESS` forever →
  refusal after `MAX_POLL_ATTEMPTS`, tested with a small patched constant or a
  mock exhausting the responses.)

### 8.5 Rate-limit-exceeded path (exit 1)
- Mock limit response `{"data":[{"quota_usage":50,"quota_total":50}]}` (usage >=
  total) → `execute` raises `AdapterRefusal` citing rate limit BEFORE any
  `/media` call (assert `.calls` has only the 1 limit call).

### 8.6 `>10` and `0` children (exit 2) — dry-run AND execute
- A fixture package with 11 attachments → dry-run `run(--week …)` exits 2, cited,
  NO `publish-plan.json` written; and `execute` raises `AdapterUsageError`.
- A fixture package with 0 attachments → same exit-2 treatment.

### 8.7 Single-image degrade (§4.2)
- A fixture package with 1 attachment → dry-run plan has the 6-step no-carousel
  sequence (no `is_carousel_item`, no `media_type=CAROUSEL`, no separate parent);
  `execute` posts one container then publishes. Parity holds.

### 8.8 Live no-op for instagram (§1.2) — via `run()`
- `run(week="2026-W28", channel="instagram", mode="live", …)` with a valid
  in-scope IG env + base url + ack + date and an injected `RaisingTransport` →
  exit 0, the "instagram adapter ready; … Sprint 006; nothing posted" notice on
  stderr, ZERO transport calls (RaisingTransport never raises ⇒ never called),
  queue UNCHANGED, no secret echoed.

### 8.9 Redaction proof (B17) — no secret in any emitted output
- With a sentinel access token in the mock/env, assert the sentinel string is
  absent from the dry-run stdout AND `publish-plan.json` AND the live-no-op
  stderr (the token only ever lives in `execute`'s transport calls, which are not
  emitted). Dry-run never has a token at all (renders `<REDACTED>`).

### 8.10 Blacklist guard
- A test asserts the string `content_publishing` (the refuted `…_publishing`
  variant) and `media_publishing` do NOT appear anywhere in `publish_api.py`
  source (grep/AST), and that `media_publish` and `content_publishing_limit` DO.
  (`content_publishing_limit` legitimately contains `content_publishing` as a
  substring, so the guard checks for the refuted PERMISSION token
  `content_publishing"` / `content_publish` + `ing` word-boundary — BUILD picks a
  precise check that flags the refuted permission name without false-positiving
  the legitimate `content_publishing_limit` endpoint.)

### 8.11 Regression: Sprint-002 behaviors preserved
- Re-assert the LinkedIn row still `steps: 0` + its Sprint-004 note; empty-scope,
  malformed-input, live-gate, transport-seam-AST (still exactly 1 `urlopen`),
  and helper tests all still pass (they are unchanged).

---

## 9. Determinism, secrets, no-network (unchanged invariants, re-proven with steps)
- **No wall clock** anywhere (B9). The only dates are `--week`/`--date` args. The
  poll loop is count-bounded (`MAX_POLL_ATTEMPTS`), never time-bounded; any inter-
  poll delay is an injectable no-op-in-tests seam.
- **Secrets** (B17): the access token NEVER appears in stdout or
  `publish-plan.json`; render sites show `<REDACTED>`. Proven by §8.9.
- **No network** (B38/B39): the transport seam is unchanged — still exactly ONE
  `urlopen` call site inside `Transport` (the adapter calls the INJECTED
  transport, never `urlopen`). The Sprint-002 AST test still passes unchanged.
  Dry-run invokes the transport ZERO times (plan_steps takes no transport).

---

## 10. States that must exist (spec §6 — instagram slice)
- **Success (dry-run):** instagram row full 8-step plan on stdout +
  `publish-plan.json`; queue untouched; exit 0.
- **Loading / multi-call in flight:** the poll step is present as a discrete step
  (§4.3).
- **Error — container:** `status_code == ERROR/EXPIRED` (or poll-exhausted) →
  `execute` refuses (exit 1), cited.
- **Error — rate limit:** `quota_usage >= quota_total` → `execute` refuses (exit
  1), cited, before any `/media` call.
- **Invalid input:** `>10` or `0` attachments → exit 2, cited, no plan write.
- **Live no-op (this sprint):** `--live` instagram row, gate passing → honest
  no-op notice, exit 0, nothing posted (§1.2).

---

## 11. Verification — commands the Evaluator runs

All from repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`.

**Precondition — frozen asset present** (as Sprint 002 §10):
```
python3 -c "import json;d=json.load(open('content/2026-07-09-anarock-vs-propequity/publish/instagram.json'));print(len(d['attachments']),'attachments')"
```
Expected: `3 attachments`. If missing/modified, gate clauses 3–5 are SKIP.

**Gate clause 1 — new suite green:**
```
python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_publish_api.py'
```
Expected: `OK`, 0 failures (Sprint-002 cases as consciously updated + new
Sprint-003 cases).

**Gate clause 2 — no regression, full suite green:**
```
python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_*.py'
```
Expected: `OK`, zero failures/errors (all prior suites, including the updated
`test_publish_api.py`).

**Gate clause 3 — dry-run real asset, instagram 8-step plan, no network, no queue change:**
```
cp content/publish-queue.json /tmp/q.before
python3 tools/marketing-loops/publish_api.py --week 2026-W28 ; echo "exit=$?"
python3 -c "import json;d=json.load(open('content/publish-plan.json')); r=[x for x in d['rows'] if x['channel']=='instagram'][0]; print('steps',len(r['steps'])); [print(s['method'],s['url']) for s in r['steps']]"
diff content/publish-queue.json /tmp/q.before && echo QUEUE-UNCHANGED
```
Expected: exit 0; `steps 8`; the 8 method+url lines match §4 (GET limit, 3× POST
media, POST media, GET parent-id, POST media_publish, GET media-id);
`QUEUE-UNCHANGED`.

**Gate clause 4 — fidelity + secrets + determinism inspection:**
```
python3 -c "import json;d=json.load(open('content/publish-plan.json')); r=[x for x in d['rows'] if x['channel']=='instagram'][0]; import sys; body=json.dumps(r); print('REDACTED-only-token' if '<REDACTED>' in body else 'MISSING-REDACTION'); print('has-placeholders' if '<ig-parent-creation-id>' in body and '<ig-child-container-id-1>' in body else 'MISSING-PLACEHOLDERS'); print('base-placeholder' if '<PUBLIC_ASSET_BASE_URL>' in body else 'no-base-placeholder')"
python3 tools/marketing-loops/publish_api.py --week 2026-W28 && cp content/publish-plan.json /tmp/p1
python3 tools/marketing-loops/publish_api.py --week 2026-W28 && diff content/publish-plan.json /tmp/p1 && echo DETERMINISTIC
grep -c 'media_publishing\|content_publishing"' tools/marketing-loops/publish_api.py || true
```
Expected: `REDACTED-only-token`, `has-placeholders`, `base-placeholder`;
`DETERMINISTIC`; the blacklist grep prints `0` (refuted names absent).

**Gate clause 5 — concrete base-url preview + `>10`/`0` guard:**
```
python3 tools/marketing-loops/publish_api.py --week 2026-W28 --public-asset-base-url https://assets.example/social-assets >/dev/null
python3 -c "import json;d=json.load(open('content/publish-plan.json'));r=[x for x in d['rows'] if x['channel']=='instagram'][0];print([s for s in r['steps'] if 'child container 1' in s['label']][0]['params']['image_url'])"
```
Expected: `https://assets.example/social-assets/2026-07-09-anarock-vs-propequity/format-01.png`.
(The `>10`/`0`-attachment exit-2 paths are covered by the suite via fixtures,
gate clause 1; the Evaluator MAY additionally point `--queue`/package at an
11-attachment fixture to reproduce exit 2 with no plan write.)

**Gate clause 6 — live no-op is honest (instagram adapter not yet wired to post):**
```
printf 'IG_USER_ID=SENTINEL_IGID\nIG_ACCESS_TOKEN=SENTINEL_IGTOKEN\nPUBLIC_ASSET_BASE_URL=https://assets.example/social-assets\n' > /tmp/ig.env
python3 tools/marketing-loops/publish_api.py --week 2026-W28 --channel instagram --live --env /tmp/ig.env --date 2026-07-09 --i-have-verified-dry-run 2>&1 | tee /tmp/ig.out ; echo "exit=${PIPESTATUS[0]}"
grep -c SENTINEL /tmp/ig.out
grep -Ei 'permalink|posted' /tmp/ig.out
diff content/publish-queue.json /tmp/q.before && echo QUEUE-UNCHANGED
```
Expected: exit 0; a cited "instagram adapter ready; … Sprint 006; nothing posted"
notice; `SENTINEL` count `0`; NO real permalink/posted success line; queue
unchanged. (This proves live posting is genuinely deferred, not faked.)

**Gate clause 7 — no-network AST unchanged + import silence:**
```
python3 -c "import ast; t=ast.parse(open('tools/marketing-loops/publish_api.py').read()); refs=[n for n in ast.walk(t) if (isinstance(n,ast.Attribute) and n.attr=='urlopen') or (isinstance(n,ast.Name) and n.id=='urlopen')]; calls=[n for n in ast.walk(t) if isinstance(n,ast.Call) and n.func in refs]; print(len(calls))"
python3 -c "import sys; sys.path.insert(0,'tools/marketing-loops'); import publish_api"
```
Expected: prints `1` (single seam, unchanged); import exits 0 with empty stdout.

**Gate clause 8 — hygiene:**
```
git status --porcelain
```
Expected: only `tools/marketing-loops/publish_api.py` and
`tools/marketing-loops/tests/test_publish_api.py` modified; untracked
`content/publish-plan.json` (gitignored — must NOT be staged); no `.env`, no
secret, no db/upload artifact.

---

## 12. Security / hygiene assumptions
- Access token comes ONLY from an untracked `.env` (live/execute); loaded to
  memory, NEVER printed, NEVER written to any tracked file (B13, B17, B18). The
  dry-run plan carries `<REDACTED>` and never a real token. `.gitignore` already
  covers `.env` and `content/publish-plan.json` (Sprint 002).
- The ONLY writes this sprint: `content/publish-plan.json` (dry-run). The queue
  file is NEVER written this sprint (live posting is Sprint 006).

## 13. Non-applicable sections
- Playwright / browser click paths: N/A — no HTTP surface served, no route, no
  rendered screen. Verification is `unittest` + the CLI probes in §11.
- Keyboard / focus / ARIA / contrast / responsive: N/A — no UI. "Design" here =
  plan legibility (the stdout per-step block is plain, wrappable text; the
  machine plan is stable-sorted for diffing — spec §7).

## 14. Non-goals (explicit)
- NO LinkedIn adapter (004), NO Facebook adapter (005): linkedin/facebook rows
  keep `steps: []` + their Sprint-002 "no adapter" notes this sprint.
- NO live posting from the CLI, NO `queued → posted` transition, NO permalink
  RECORDING into the queue, NO `queue.write_queue` call, NO day-cap enforcement —
  all Sprint 006. `execute()` is built + unit-tested but wired into the live
  `run()` path only in 006.
- NO change to the frozen `run()`/`main()` signatures or the Sprint-002
  `Transport`/`Response`/`Recording`/`RaisingTransport`/plan-envelope shapes.
- NO frozen-module edits; NO edits to any existing test EXCEPT the enumerated
  Sprint-002 instagram-row assertions in `test_publish_api.py` (§7).
- NO Facebook-Login IG flavor (`graph.facebook.com`) — Instagram Login only
  (`graph.instagram.com`, R5-3).
- NO byte upload for IG (images are public-hosted via `image_url` — R4-B2); byte
  upload is a LinkedIn concern (004).
- NO hard-coded rate-limit number (check `content_publishing_limit` — R4-B3).
- NO use of the refuted `…_content_publishing` / `media_publishing` names
  (BLACKLIST, RESEARCH §9).
- NO wall-clock read; NO third-party dependency; stdlib only.
- NO real network in any test or in dry-run — provable (§9).

## 15. Acceptance summary (the contract's testable core)
Sprint 003 passes iff ALL hold:
1. Dry-run over the real asset emits an instagram row with 8 steps in the exact
   §4 order/shape (GET limit; 3× POST child /media; POST parent /media
   CAROUSEL; GET poll parent-id; POST /media_publish; GET permalink), each on
   `graph.instagram.com`, token `<REDACTED>`, dependent values as named
   placeholders, `image_url` via the join rule, `headers {}`, `payload null`; to
   stdout (exact §7.2 template) AND `publish-plan.json`; byte-identical on
   repeat; queue unchanged; zero network.
2. The LinkedIn row and every other Sprint-002 behavior are preserved
   (`steps: 0` + Sprint-004 note; empty-state, gate, seam, helpers unchanged);
   both full suites GREEN.
3. `execute()` (shared flow) walks the same 8 calls against a mock: happy path
   returns the permalink; container ERROR/EXPIRED/poll-exhausted → refusal (exit
   1); rate-limit exceeded → refusal (exit 1) before any `/media`; the parity
   test proves plan-steps == transport-calls (canonical execution).
4. `>10` or `0` attachments → exit 2, cited, no plan write (dry-run and execute).
5. Single-image degrade renders/executes the 6-step no-carousel sequence.
6. `--live` with an instagram row is an honest no-op (exit 0, "nothing posted",
   no fake permalink, queue unchanged, no secret echoed) — posting deferred to
   006.
7. Secrets: no access-token value in any stdout/JSON output; `<REDACTED>` at
   every render site. Determinism: no wall clock; bounded poll.
8. Blacklist: refuted `…_publishing` names absent; `media_publish` +
   `content_publishing_limit` present. Transport seam unchanged (exactly 1
   `urlopen` site). Hygiene clean (no secret/artifact staged).
