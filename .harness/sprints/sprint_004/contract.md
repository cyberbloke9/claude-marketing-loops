# Sprint 004 Contract — LinkedIn adapter (verified: R4-B4, R5-5/R5-6)

Scope: spec §11 Sprint 004 + behaviors B25–B29 (LinkedIn adapter — BOTH organic
flows), plus the step-level rendering pieces of B6/B7/B9/B10/B17/B28 as they apply
to steps that carry **non-empty headers and non-null payloads** (LinkedIn is the
first adapter that does; the Instagram slice from Sprint 003 had `headers {}` +
`payload null` on every step). This sprint fills the `linkedin` channel's `steps`
in the dry-run plan (Sprint 003 shipped the linkedin row with `steps: []` + a "no
adapter … Sprint 004+" note) and delivers a mock-transport-executable adapter
proving BOTH LinkedIn organic paths, exactly one executed per row.

Ground truth read (the ONLY authority for API facts — do not re-derive):
`RESEARCH.md` R4-B4, R5-5, R5-6. Verified facts locked for this sprint:
- **Organic LinkedIn carousels are IMPOSSIBLE via the API (R4-B4, High).** Native
  carousels were removed as an organic format in late 2023. The tool MUST NOT
  attempt a "carousel" post type. The two supported organic paths are **MultiImage**
  and **multi-page PDF Documents** (which render as swipeable carousel-like slides).
- **Member-profile posting only (R5-6).** Owner = the founder's **person URN**
  (`w_member_social`), NOT a company page. Company-page / organization posting
  needs the vetted Community Management API (R5-5) — explicitly a NON-GOAL (§14).
  Both the Images and Documents upload APIs accept person-URN owners (R5-6).
- Versioned endpoints under `https://api.linkedin.com/rest/*`:
  `/rest/images` and `/rest/documents` (`?action=initializeUpload`), the upload
  `PUT` to the returned upload URL, and `/rest/posts`.
- Required versioned headers on every `/rest/*` call (B28): `Authorization: Bearer
  <token>`, `LinkedIn-Version: <YYYYMM>` (a FIXED configurable constant, never
  wall-clock-derived — determinism, R5 risk 6), `X-Restli-Protocol-Version: 2.0.0`.

This is a stdlib CLI + JSON tool; there is NO browser surface (Playwright: N/A —
§13). Verification is `unittest` + CLI probes (§11).

---

## 1. What this sprint delivers (the testable core)

A **LinkedIn adapter** inside `tools/marketing-loops/publish_api.py` that
implements BOTH organic post flows and EXECUTES EXACTLY ONE per queue row
(a queue row has one `(slug, channel)` and one `permalink`; never double-post):

1. **Document flow (DEFAULT, B27):** owner person URN; input = the PDF named in
   `content/<slug>/render/manifest.json` field `"pdf"` (e.g. `carousel.pdf`) — NOT
   `package.attachments`. Sequence: `POST /rest/documents?action=initializeUpload`
   → `PUT <uploadUrl>` (PDF bytes) → `POST /rest/posts` with `content.media`
   referencing the document URN. **3 HTTP calls.**
2. **MultiImage flow (B26):** owner person URN; input = `package.attachments`
   (ordered PNGs). Sequence: for each image `POST /rest/images?action=initializeUpload`
   → `PUT <uploadUrl>` (image bytes); then ONE `POST /rest/posts` with
   `content.multiImage.images`. For the real asset (N=3): **7 HTTP calls.**

Both are delivered as:
- **Plan** (dry-run, evaluator-facing via the CLI): for a `linkedin` queue row it
  fills the row's `steps` with the FULL, faithful, ordered list of HTTP calls the
  selected flow makes, rendered with named deterministic placeholders (B10) for
  dependent values (`<li-upload-url-i>`, `<li-image-urn-i>`, `<li-document-urn>`,
  `<li-post-urn>`), `<LI_PERSON_URN>` for the owner (dry-run loads no `.env`), and
  `Authorization: Bearer <REDACTED>` (B17) for the token.
- **Execute** (mock-transport, test-facing): the SAME flow definition, walked
  against an injected `transport`, returning a typed result (permalink) on the
  happy path or a typed refusal on the unexpected-response path.

### 1.1 Shared-flow guarantee (the anti-stub property — spec §7 anti-patterns)

`plan_steps` and `execute` MUST derive from a SINGLE flow definition per post-type
(one generator describing the ordered calls), so the dry-run plan is literally
produced by the same code path live execution walks — never a hand-written
parallel fiction. Proven by the **parity test** (§8.4). This is the same guarantee
Sprint 003 established for `_ig_flow`; LinkedIn adds `_li_document_flow` and
`_li_multiimage_flow` (or one parameterized generator) with the identical
plan-driver / execute-driver split.

### 1.2 `execute()` is CLI-unreachable this sprint — by design, not a stub

Live posting + `queued → posted` transition + permalink recording + day-cap are
Sprint 006 (spec §11). As in Sprint 003, `main()` never injects a mock transport,
so a `--live` linkedin row is an HONEST no-op:
- **Dry-run** wires `plan_steps` into `run()` and is fully evaluator-testable.
- **`execute()`** is reached ONLY by this sprint's unit tests; its named downstream
  consumer is Sprint 006. It is covered by the happy-document / happy-multiimage /
  unexpected-response unit tests AND is the other half of the parity test.
- **`--live` with a `linkedin` row in scope** (gate passing, real LI tokens
  present) emits a cited stderr notice `"linkedin adapter ready; live posting +
  queue transition land in Sprint 006; nothing posted"`, makes ZERO network calls,
  writes no queue, invents no permalink, flips no row, exits 0. (This REPLACES the
  generic Sprint-002 "no adapter registered … Sprint 003+" notice for the linkedin
  channel — §7 conscious-update, mirroring how Sprint 003 replaced it for instagram.)

---

## 2. Files affected

Production (edit — the ONLY production file touched):
- `tools/marketing-loops/publish_api.py` — add the LinkedIn adapter (two flow
  definitions, `plan_steps`, `execute`, `_LiResult`, response readers), register
  it in `_ADAPTERS`, wire `plan_steps` into the dry-run dispatch, add the linkedin
  branch to `run()`'s live-dispatch notice (§1.2), add the `--linkedin-version`
  flag + its validation + `run()` param + `main()` wiring, extend the stdout
  renderer to emit `headers:`/`payload:` lines CONDITIONALLY (§6), and generalize
  `_drive_execute` to send request bodies (§5.3). The frozen `run()`/`main()` shape
  (adding one keyword arg with a default is backward-compatible), the
  `Transport`/`Response`/`RecordingTransport`/`RaisingTransport` classes, the plan
  envelope, and the 7 frozen step-object keys are UNCHANGED.

Tests (edit):
- `tools/marketing-loops/tests/test_publish_api.py` — add the LinkedIn adapter
  suite (§8); consciously update the THREE Sprint-003 assertions that froze the
  linkedin row as `steps: 0` + the "no adapter … Sprint 004+" note (§7); extend
  `_seed_workspace` to also write `content/<slug>/render/manifest.json` (and, for
  execute tests, a small `carousel.pdf` + the PNG attachment files) so the document
  flow is hermetic (§7.3). Mocked transport only.

No edits to any frozen module (`queue.py`, `utm.py`, `channels.py`, `schedule.py`,
`captions.py`) and no edits to the Instagram adapter code paths or the IG tests. If
BUILD finds a frozen module or the IG slice needs changing to satisfy this
contract, that is a finding to disclose — none is expected.

---

## 3. Inputs the LinkedIn adapter consumes (B5) — linkedin only

From the row's package JSON at `row["package_path"]`
(`content/<slug>/publish/linkedin.json`):
- `caption` — the post `commentary`, used VERBATIM (includes the UTM link already;
  the tool NEVER edits it — B5). Multi-line expected (real newlines).
- `attachments` — ordered repo-relative PNG paths. Consumed ONLY by the MultiImage
  flow. The image bytes for a `PUT` upload are `Path(attachment).read_bytes()`
  (execute only). Dry-run does NOT read image bytes.
- `slug` — used as the document post `title` (see §4.3 live-pending note) and to
  locate the render manifest.

From the render manifest at
`Path(package_path).parent.parent / "render" / "manifest.json"`
(i.e. `content/<slug>/render/manifest.json`) — consumed ONLY by the Document flow:
- `pdf` — the PDF filename (e.g. `carousel.pdf`). The PDF bytes for the `PUT`
  upload are `(<slug render dir>/<pdf>).read_bytes()` (execute only). Dry-run reads
  the manifest to obtain the FILENAME (deterministic; no wall-clock) but does NOT
  read PDF bytes.

### 3.1 Precondition validation (B4-adjacent) — both modes, build time

- **Document flow, manifest missing/unreadable** → exit 2, cited `"linkedin row
  (<slug>): render manifest not found at <path> (needed for the document flow)"`.
- **Document flow, manifest has no non-empty `pdf`** → exit 2, cited `"linkedin
  row (<slug>): manifest has no 'pdf' (needed for the document flow)"`.
- **MultiImage flow, 0 attachments** → exit 2, cited `"linkedin row (<slug>): no
  attachments to publish (multi-image)"`.
- **MultiImage flow, > `_LI_MAX_IMAGES` (20) attachments** → exit 2, cited
  `"linkedin multi-image exceeds 20 images (got <n>)"`. (LinkedIn multiImage upper
  bound; there is NO minimum-of-2 gate — nothing in RESEARCH mandates one.)
- These run when the plan is BUILT (dry-run) AND when the adapter executes, so a
  bad package fails identically in both. Raised as `AdapterUsageError` (exit 2, no
  plan/queue write).

---

## 4. The two LinkedIn flows — exact call sequences (B25–B29)

Common rendering rules (frozen):
- **Host / owner.** All URLs are on `https://api.linkedin.com`. The owner is the
  person URN path/body value `<LI_PERSON_URN>`. In dry-run no `.env` is loaded, so
  it renders as the literal placeholder `<LI_PERSON_URN>` (deterministic; never a
  secret in the plan). In execute it is the real env value.
- **Auth + versioned headers (B28).** Every `/rest/*` step carries `headers`:
  `Authorization: Bearer <REDACTED>` (execute sends the real token; the plan/record
  never carries it), `LinkedIn-Version: <VERSION>` (the fixed constant, §4.4),
  `X-Restli-Protocol-Version: 2.0.0`. JSON-body steps additionally carry
  `Content-Type: application/json`. The `PUT` upload step carries ONLY
  `Authorization: Bearer <REDACTED>`.
- **`params` vs `payload`.** `?action=initializeUpload` is a query `params` field
  on the two initialize calls; every other LinkedIn call has empty `params`
  (renders `(none)`). The `initializeUpload` and `/rest/posts` calls carry a JSON
  `payload` (dict). The `PUT` upload step's `payload` is the deterministic string
  placeholder `<binary PDF: <file>>` / `<binary PNG: <file>>` (the plan never shows
  raw bytes); execute sends the real file bytes (§5.3).
- **Post-type selection (B25).** `--linkedin-post-type {document,multi-image}`,
  DEFAULT `document` (justified: `meta.md` declares "LinkedIn PDF" and
  `render/carousel.pdf` exists — RISK §10.1). Exactly ONE flow is emitted/executed
  per linkedin row.

### 4.1 Document flow (DEFAULT) — 3 steps

| # | label | method | url | params | headers | payload |
|---|---|---|---|---|---|---|
| 1 | `LI · initialize document upload` | POST | `https://api.linkedin.com/rest/documents` | `action=initializeUpload` | Authz+Version+Restli+Content-Type | `{"initializeUploadRequest":{"owner":"<LI_PERSON_URN>"}}` |
| 2 | `LI · upload document bytes` | PUT | `<li-upload-url-1>` | (none) | Authz only | `<binary PDF: carousel.pdf>` |
| 3 | `LI · create document post` | POST | `https://api.linkedin.com/rest/posts` | (none) | Authz+Version+Restli+Content-Type | document post body (§4.3) |

- Step 1 response → `value.uploadUrl` (`<li-upload-url-1>`) + `value.document`
  (`<li-document-urn>`). Step 2 `url` = the upload URL from step 1. Step 3 body
  references `<li-document-urn>`. Step 3 response → post URN (`<li-post-urn>`).
- **Permalink (B29): NO separate GET.** The post URN comes back from step 3; the
  permalink is CONSTRUCTED as `https://www.linkedin.com/feed/update/<li-post-urn>`.
  (Unlike IG's B24, which needed a 4th fetch-permalink GET — do NOT add a 4th call.)

### 4.2 MultiImage flow — 7 steps for N=3

For each image i in 1..N (interleaved init→upload), then one post:

| # | label | method | url | params | headers | payload |
|---|---|---|---|---|---|---|
| 2i-1 | `LI · initialize image upload i/N` | POST | `…/rest/images` | `action=initializeUpload` | Authz+Version+Restli+Content-Type | `{"initializeUploadRequest":{"owner":"<LI_PERSON_URN>"}}` |
| 2i | `LI · upload image bytes i/N` | PUT | `<li-upload-url-i>` | (none) | Authz only | `<binary PNG: format-0i.png>` |
| 2N+1 | `LI · create multi-image post` | POST | `…/rest/posts` | (none) | Authz+Version+Restli+Content-Type | multi-image post body (§4.3) |

- Each init i response → `value.uploadUrl` (`<li-upload-url-i>`) + `value.image`
  (`<li-image-urn-i>`). Upload i `url` = that upload URL. The final post body
  references `[<li-image-urn-1> … <li-image-urn-N>]`. Post response → `<li-post-urn>`;
  permalink constructed as in §4.1. Total = `2N+1` (=7 for N=3).

### 4.3 The `/rest/posts` bodies (B26/B27 mandated fields + live-pending extras)

**Document post body:**
```json
{"author":"<LI_PERSON_URN>","commentary":"<caption verbatim>","content":{"media":{"id":"<li-document-urn>","title":"<slug>"}},"distribution":{"feedDistribution":"MAIN_FEED","targetEntities":[],"thirdPartyDistributionChannels":[]},"lifecycleState":"PUBLISHED","visibility":"PUBLIC"}
```
**MultiImage post body:**
```json
{"author":"<LI_PERSON_URN>","commentary":"<caption verbatim>","content":{"multiImage":{"images":[{"id":"<li-image-urn-1>"},{"id":"<li-image-urn-2>"},{"id":"<li-image-urn-3>"}]}},"distribution":{"feedDistribution":"MAIN_FEED","targetEntities":[],"thirdPartyDistributionChannels":[]},"lifecycleState":"PUBLISHED","visibility":"PUBLIC"}
```
- **B26/B27-mandated fields (asserted by tests, treated as verified):** `author`
  (person URN), `commentary` (caption verbatim), `content.multiImage.images` /
  `content.media` (referencing the URN), `visibility: "PUBLIC"`,
  `lifecycleState: "PUBLISHED"`, and the `initializeUploadRequest.owner` on the
  init calls.
- **Live-pending extras (faithful to the Posts API cited in R4-B4, NOT independently
  verified; isolated so a founder correction touches ONE builder):** `distribution`
  (the Posts API requires it), `content.media.title` (document posts require a
  title — set to the `slug`), and the `Content-Type` header. These are marked
  `live-pending` in code and frozen for determinism, but NOT claimed as verified;
  the tests do NOT hard-assert their exact structure beyond presence.

### 4.4 The `LinkedIn-Version` header (B28, R5 risk 6)
- A FIXED module constant `LINKEDIN_VERSION_DEFAULT` (a `YYYYMM` string, pinned to
  `"202506"`), NEVER derived from the wall clock. Overridable via
  `--linkedin-version YYYYMM` (validated `^\d{6}$`; a non-matching value → exit 2,
  cited). The chosen value is a documented assumption (LinkedIn requires SOME valid
  monthly version; the exact accepted value is a founder/live concern) — only this
  constant/flag changes if LinkedIn deprecates it. Determinism: same inputs ⇒
  byte-identical plan regardless of when it runs.

### 4.5 Named placeholders (B10) — the exact set
- `<li-upload-url-i>` — upload URL from init i's response (1-indexed; document uses
  i=1). Used as the `PUT` step's `url`.
- `<li-image-urn-i>` — image URN from init i's response. Used in the multi-image
  post body's `images` list.
- `<li-document-urn>` — document URN from the document init response. Used in the
  document post body's `content.media.id`.
- `<li-post-urn>` — post URN from the `/rest/posts` response. Used to CONSTRUCT the
  permalink. (A natural extension of B10's enumerated set — disclosed here.) NOTE:
  `<li-post-urn>` lives only in the final step's `plan_response` (the dependent-value
  stub), NOT in any of the 7 serialized step keys — it does NOT appear in the
  emitted plan JSON, and no gate asserts it there (the permalink itself is a Sprint
  006 queue-write concern).
In `execute` these are the real values threaded from the real transport responses.

---

## 5. Adapter result / refusal contract + driver generalization

### 5.1 Result / refusal types (exit-code mapping — B41/B42)
`execute(row, package, ctx, transport)` returns / raises:
- **Success** → `_LiResult` with `permalink` (str,
  `https://www.linkedin.com/feed/update/<urn>`) and `post_urn` (str).
- **Domain refusal (exit 1)** → raise `AdapterRefusal(message)` on an unexpected /
  non-JSON response shape (missing `value.uploadUrl`, missing URN, etc.), cited.
  (LinkedIn has NO rate-limit pre-check and NO container poll — those are IG-only;
  so this is the only exit-1 path.)
- **Usage / precondition (exit 2)** → raise `AdapterUsageError(message)`: the §3.1
  cases. Enforced at BUILD time in dry-run too (dry-run exits 2, no plan written).

### 5.2 Response readers (execute; live-pending shapes — isolated, contract §6-style)
- `initializeUpload` (images) → read `resp["value"]["uploadUrl"]` and
  `resp["value"]["image"]`; (documents) → `["value"]["uploadUrl"]` and
  `["value"]["document"]`. Missing → `AdapterRefusal` (cited).
- **Upload `PUT`** → response body IGNORED (no read); LinkedIn returns an empty
  201 live (see §5.3).
- **`/rest/posts`** → the post URN via `_read_li_post_urn(resp)` = `resp.headers`
  `.get("x-restli-id")` FIRST, else `resp.json().get("id")`. RATIONALE: LinkedIn
  returns the created post URN in the `x-restli-id` response HEADER (live-faithful);
  the body fallback keeps the mock (which returns `headers={}` + a JSON body)
  working without touching the frozen `RecordingTransport`. Missing both →
  `AdapterRefusal`. Isolated in one helper (a founder correction touches ONE place).

### 5.3 `_drive_execute` generalization (the ONLY driver change; IG-safe)
Sprint 003's `_drive_execute` always called `transport.request(..., body=None)` and
`resp.json()`. LinkedIn needs real request bodies AND must tolerate empty responses:
- **Request body:** send `step.execute_body()` where `execute_body()` returns
  `Path(step.upload_path).read_bytes()` when `upload_path` is set (the `PUT` steps),
  else `json.dumps(step.payload).encode("utf-8")` when `payload` is a dict/list,
  else `None`. `_Step` gains an optional `upload_path=None` attribute + this method.
- **Empty-response tolerance:** if `resp.body` is empty/whitespace, feed `{}` to the
  generator instead of calling `resp.json()` (which would raise on LinkedIn's empty
  `PUT`/`201` bodies and spuriously produce an `AdapterRefusal`). A non-empty
  non-JSON body still → `AdapterRefusal` (cited).
- **IG regression guard:** IG steps have `upload_path=None` and `payload=None`
  → `execute_body()` returns `None`; IG bodies are always non-empty JSON →
  the empty-body branch is not taken. IG `execute` behavior + all IG tests stay
  byte-for-byte GREEN. (Assert explicitly — §8.7.)

---

## 6. Conditional headers/payload stdout render (the linchpin regression property)

Sprint 003's stdout per-step block was `label` / `METHOD url` / `params:` only
(IG had empty headers + null payload). LinkedIn is the first adapter with non-empty
headers and non-null payloads, so the renderer is extended — CONDITIONALLY, to
preserve the frozen IG template byte-for-byte:

- After the `params:` line, render a `headers:` line ONLY when `headers` is
  non-empty: `       headers: <k1: v1, k2: v2, …>` (7 spaces; keys SORTED; `k: v`
  joined by `, `). Secret-bearing values already carry `<REDACTED>` (e.g.
  `Authorization: Bearer <REDACTED>`).
- Then render a `payload:` line ONLY when `payload` is not `null`:
  `       payload: <rendered>` (7 spaces). A dict/list payload renders as compact
  deterministic JSON `json.dumps(payload, sort_keys=True, separators=(",", ":"))`
  with the DEFAULT `ensure_ascii=True`. Do NOT apply the Sprint-003 `_escape_stdout`
  helper to a dict payload: `json.dumps` already encodes real newlines inside string
  values as the two-char `\n` and non-ASCII (e.g. the caption's em-dash `—`) as
  `\uXXXX` (`—`) — no extra escaping, and the machine-JSON `plan_dumps` uses
  the same default so the plan and stdout carry the same encoded form. A string
  payload (the `PUT` binary placeholder) renders verbatim.
- **BUILD assertion discipline:** the expected §6.1 stdout payload line MUST be
  produced by calling the IDENTICAL `json.dumps(...)` on the same dict in the test —
  NEVER hand-typed (hand-typing a raw em-dash / newline guarantees a failing
  `test_stdout_template_exact`, because the caption is JSON-encoded, not
  `_escape_stdout`-escaped like the IG params).
- **IG invariant:** IG steps have `headers {}` (→ no headers line) and `payload
  null` (→ no payload line), so the entire IG block, `test_stdout_template_exact`,
  and every other frozen IG assertion remain BYTE-IDENTICAL. This is an explicit
  acceptance clause (§15.6) and a regression test (§8.7).

### 6.1 Exact stdout LinkedIn document block (DEFAULT, hermetic seed)
For the seeded workspace (`_seed_workspace` writing the linkedin package with
caption `_REAL_CAPTION` and a manifest `{"pdf":"carousel.pdf"}`), `--week
2026-W28` with NO `--public-asset-base-url` and the default version, the linkedin
row block (Row 2/2) is EXACTLY (leading spaces significant):

```
Row 2/2: 2026-07-09-anarock-vs-propequity (linkedin)
  package: content/2026-07-09-anarock-vs-propequity/publish/linkedin.json
  steps: 3
    1. LI · initialize document upload
       POST https://api.linkedin.com/rest/documents
       params: action=initializeUpload
       headers: Authorization: Bearer <REDACTED>, Content-Type: application/json, LinkedIn-Version: 202506, X-Restli-Protocol-Version: 2.0.0
       payload: {"initializeUploadRequest":{"owner":"<LI_PERSON_URN>"}}
    2. LI · upload document bytes
       PUT <li-upload-url-1>
       params: (none)
       headers: Authorization: Bearer <REDACTED>
       payload: <binary PDF: carousel.pdf>
    3. LI · create document post
       POST https://api.linkedin.com/rest/posts
       params: (none)
       headers: Authorization: Bearer <REDACTED>, Content-Type: application/json, LinkedIn-Version: 202506, X-Restli-Protocol-Version: 2.0.0
       payload: {"author":"<LI_PERSON_URN>","commentary":"<caption>","content":{"media":{"id":"<li-document-urn>","title":"2026-07-09-anarock-vs-propequity"}},"distribution":{"feedDistribution":"MAIN_FEED","targetEntities":[],"thirdPartyDistributionChannels":[]},"lifecycleState":"PUBLISHED","visibility":"PUBLIC"}
  note: linkedin adapter (member profile, api.linkedin.com; document flow); 3 HTTP calls; verified R4-B4/R5-6
```
- `<caption>` and the whole `payload:` line above are a STAND-IN for the real
  rendered value: the seeded caption `_REAL_CAPTION` as JSON-encoded inside the
  compact `json.dumps` of the post-body dict — real newlines appear as the two-char
  `\n` and the em-dash `—` as `—` (default `ensure_ascii=True`). In the machine
  JSON the `payload` object stores the caption as a normal JSON string (also
  `—`-encoded via `plan_dumps`'s default), read back VERBATIM by `json.load`
  (B5). The Evaluator asserts stdout against `json.dumps(body, sort_keys=True,
  separators=(",",":"))`; asserts the JSON against `json.load`.
- `LINKEDIN_VERSION_DEFAULT` is pinned to `202506` (a fixed `YYYYMM` constant, never
  wall-clock). §6.1 is an exact byte block, so BUILD uses exactly `202506` here and
  in §4.4; the Evaluator reads the constant from the module.

### 6.2 The linkedin row `note` (single source, shared by JSON + stdout)
`"linkedin adapter (member profile, api.linkedin.com; <flow> flow); <N> HTTP calls;
verified R4-B4/R5-6"` where `<flow>` is `document` or `multi-image` and `<N>` is
`len(steps)`. Single source shared by the machine `note` field and the stdout
`note:` line (no drift — same rule as `_note_for`).

### 6.3 Machine-plan step objects (the 7 frozen keys — unchanged)
Each step object has EXACTLY the 7 keys frozen in Sprint 002/003: `channel`
(`"linkedin"`), `label`, `method`, `url`, `params`, `headers`, `payload`.
`headers` is now a populated object; `payload` is now a dict (init/posts) or the
binary-placeholder string (`PUT`), or absent-value handling as `null` only for
adapters that use none. NO new keys; `upload_path` is an execute-only `_Step`
attribute, NOT serialized into the plan. Byte-identical on repeat.

---

## 7. Conscious Sprint-003 test update (enumerated — the regression surface)

Filling the linkedin `steps` CHANGES the linkedin-row rendering that Sprint 003
froze (`steps: 0` + the "no adapter … Sprint 004+" note). Deliberate, enumerated
update (analogous to B37 and to Sprint 003 §7), NOT a regression. Known sites (do
NOT stop here if a grep finds more — enumerate all in `generator_trace.log`):

1. **Two-row plan assertion** (`test_default_mode_is_dry_run_two_rows`, ~L284–290):
   the linkedin tuple changes from `(_REAL_SLUG, "linkedin", 0)` to `(…, "linkedin",
   3)` (default document flow) and the `assertIn("Sprint 004+", …)` on the linkedin
   note changes to assert the new linkedin adapter note. The instagram row assertion
   `(…, "instagram", 8)` is UNCHANGED.
2. **Stdout template** (`test_stdout_template_exact`, ~L347–351): the linkedin block
   changes from the 3-line `steps: 0` + old-note form to the exact §6.1 block. The
   ENTIRE instagram block (L305–345) stays BYTE-IDENTICAL.
3. **The `~L698–700` assertion** (`li` row `steps`/note in a later test): update the
   linkedin `steps`/note expectation to the new adapter output.

### 7.1 Seed extension (`_seed_workspace`) — required for the document flow
`_seed_workspace` currently writes only the queue + package JSONs. The document
flow reads `content/<slug>/render/manifest.json`. BUILD extends the seed to also
write that manifest (`{"schema_version":"2","slug":…,"pdf":"carousel.pdf"}`); for
tests that EXECUTE the document flow, also write a small `content/<slug>/render/
carousel.pdf` (any bytes) and the PNG attachment files so `read_bytes()` succeeds.
Dry-run tests need only the manifest (no bytes read). BUILD MUST verify this seed
change does NOT perturb the IG `>10`/`0`/single-image fixtures or any IG assertion
(the IG adapter ignores the manifest).

### 7.2 UNCHANGED (must stay byte-identical)
The instagram row (8 steps + its note + exact block); the envelope keys
(`schema_version`, `week`, `mode`, `rows`); `(slug, channel)` ordering;
determinism; empty-state; the live gate; the transport seam (exactly ONE
`urlopen`); every pure-helper test; and every OTHER Sprint-002/003 assertion.
After the update, BOTH full suites end GREEN (§11 gate clause 2).

---

## 8. Tests (mocked transport only — spec §11 Sprint-004 scenarios)

Add to `tools/marketing-loops/tests/test_publish_api.py`. NO real network in any
test (B39). All adapter execution uses `RecordingTransport` with canned responses.

### 8.1 Dry-run DOCUMENT plan fidelity (default, B27) — via `run()` / CLI
- Dry-run over the real asset (`--week 2026-W28`, default post-type) → linkedin row
  has 3 steps in the exact §4.1 order/shape: POST `/rest/documents?action=
  initializeUpload`, PUT `<li-upload-url-1>`, POST `/rest/posts`; every `/rest/*`
  step's `headers` carry `Authorization: Bearer <REDACTED>` + `LinkedIn-Version` +
  `X-Restli-Protocol-Version: 2.0.0`; the document post body references
  `<li-document-urn>` and carries the B27 mandated fields; permalink is NOT a step.
  Stdout matches the §6.1 block byte-for-byte; caption `\n`-escaped in stdout,
  verbatim in JSON; machine plan byte-identical on repeat (determinism, no
  wall-clock).

### 8.2 Dry-run MULTIIMAGE plan fidelity (B26) — via `run()` / CLI
- `--linkedin-post-type multi-image` → linkedin row has 7 steps in the §4.2 order
  (init/upload ×3 interleaved, then one `/rest/posts`); `<li-upload-url-i>` /
  `<li-image-urn-i>` threaded correctly; post body's `content.multiImage.images`
  lists the 3 image URNs; `visibility PUBLIC`, `lifecycleState PUBLISHED`,
  `author <LI_PERSON_URN>`. Note reads `multi-image flow`.

### 8.3 Execute — happy DOCUMENT path (member profile)
- `RecordingTransport(responses=[init_doc, put_ok, post_ok])` where
  `init_doc = {"value":{"uploadUrl":"https://up.li/DOC","document":"urn:li:document:D1"}}`,
  `put_ok = {}` (empty upload response), `post_ok = {"id":"urn:li:share:S1"}`.
- `execute(...)` returns `permalink ==
  "https://www.linkedin.com/feed/update/urn:li:share:S1"` and `post_urn` set.
- Assert `transport.calls` == the §4.1 sequence (3 calls; POST/PUT/POST); the PUT
  URL equals the exact `uploadUrl` returned by the init response (dependent-value
  wiring); the real access token appears in EVERY `/rest/*` call's `Authorization`
  header (proving live sends it) while NEVER appearing in the emitted plan; the PUT
  body equals the seeded PDF bytes; the post body JSON references the document URN
  from the init response.

### 8.4 Execute — happy MULTIIMAGE path + parity (the shared-flow proof, §1.1)
- `RecordingTransport` with `[init_1, put, init_2, put, init_3, put, post]` →
  `execute` returns the permalink from the post URN; 7 calls in order; each PUT URL
  equals the preceding init's `uploadUrl`; the post body lists the 3 image URNs.
- **Parity (LinkedIn-specific, stronger than IG's):** for one linkedin row, obtain
  the dry-run `plan_steps` AND execute against the canonical mock. Assert
  `len(plan_steps) == len(transport.calls)` and, per index, EQUAL `method`. URL
  parity is asserted on the HOST-ANCHORED steps (the init and posts calls resolve
  to `api.linkedin.com/rest/...` in both). For the `PUT` step, assert the PLAN shows
  the named `<li-upload-url-i>` placeholder AND execute's call URL equals the exact
  `uploadUrl` the mock returned in the immediately preceding init response — the
  dependent-value proof. (Pure placeholder URLs have no host to compare, so this
  clause replaces IG's path-equality for the PUT step.)

### 8.5 Exactly-one-flow-per-row (R4-B4 / RISK §10.1)
- For a single linkedin row: `--linkedin-post-type document` emits ONLY the
  document sequence (no `/rest/images` call, no `multiImage` key); `multi-image`
  emits ONLY the multi-image sequence (no `/rest/documents` call, no `media` key).
  Neither ever emits a "carousel" post type. Assert both directions.

### 8.6 Precondition guards (exit 2) — dry-run AND execute (§3.1)
- Document flow, manifest missing → dry-run `run` exits 2, cited, NO plan written;
  `execute` raises `AdapterUsageError`.
- Document flow, manifest without `pdf` → same.
- Multi-image, 0 attachments → same; >20 attachments → same (fixture).

### 8.7 IG regression + driver generalization safety (explicit)
- Re-run/assert the IG happy-carousel + parity + container-error + rate-limit +
  single-image tests: all GREEN, byte-identical `.calls` and results (the
  `_drive_execute` generalization did not alter IG — IG steps have `upload_path
  None`, `payload None`, non-empty JSON bodies).
- Assert `test_stdout_template_exact`'s instagram block is byte-identical (the
  conditional headers/payload render emits nothing for IG steps).
- **Empty-response tolerance (§5.3), directly exercised:** feed `_drive_execute` a
  step whose transport returns `Response(status=201, headers={}, body=b"")` (via a
  tiny inline fake transport — NOT a change to the frozen `RecordingTransport`,
  which always emits `b"{}"`); assert the generator receives `{}` and does NOT raise
  `AdapterRefusal`, while a non-empty non-JSON body (`b"<html>"`) DOES raise. This
  keeps the empty-body safety branch exercised rather than shipped untested.

### 8.8 Live no-op for linkedin (§1.2) — via `run()`
- `run(week="2026-W28", channel="linkedin", mode="live", …)` with a valid in-scope
  LI env (`LI_PERSON_URN`, `LI_ACCESS_TOKEN`) + base url + ack + date and an
  injected `RaisingTransport` → exit 0, the "linkedin adapter ready; … Sprint 006;
  nothing posted" notice on stderr, ZERO transport calls, queue UNCHANGED, no
  secret echoed.

### 8.9 Redaction proof (B17) — no secret in any emitted output
- With a sentinel `LI_ACCESS_TOKEN` in the mock/env, assert the sentinel string is
  absent from the dry-run stdout AND `publish-plan.json` AND the live-no-op stderr.
  The token lives ONLY in `execute`'s `Authorization` headers (transport `.calls`,
  not emitted). Dry-run never has a token (renders `Bearer <REDACTED>`).

### 8.10 `--linkedin-version` validation
- `--linkedin-version 202503` → the version appears in every `/rest/*` step's
  `LinkedIn-Version` header in the plan. `--linkedin-version bogus` (or `2025-03`)
  → exit 2, cited. No wall-clock: the default renders identically across runs.

### 8.11 Regression: Sprint-002/003 behaviors preserved
- Empty-scope, malformed-input, live-gate, transport-seam-AST (still exactly 1
  `urlopen`), and the pure-helper tests all still pass. (No `facebook` row is
  queued for W28 — the real asset queues only instagram + linkedin; the facebook
  adapter is Sprint 005.)

---

## 9. Determinism, secrets, no-network (unchanged invariants, re-proven)
- **No wall clock** anywhere (B9). The only dates are `--week`/`--date`. The
  `LinkedIn-Version` is a FIXED constant/flag, never wall-clock-derived (§4.4).
  There is no poll loop in the LinkedIn flows.
- **Secrets** (B17): the access token NEVER appears in stdout or `publish-plan.json`;
  every render site shows `Bearer <REDACTED>`. The person URN, being a `.env`
  value, renders as the `<LI_PERSON_URN>` placeholder in dry-run (never loaded).
  Proven by §8.9.
- **No network** (B38/B39): the transport seam is unchanged — still exactly ONE
  `urlopen` call site inside `Transport`; adapters call the INJECTED transport.
  Dry-run invokes the transport ZERO times (`plan_steps` takes no transport). The
  Sprint-002 AST test still passes unchanged. No test opens a socket (byte reads of
  seeded local files in execute tests are filesystem, not network).

---

## 10. States that must exist (spec §6 — linkedin slice)
- **Success (dry-run, document):** linkedin row full 3-step plan on stdout +
  `publish-plan.json`; queue untouched; exit 0.
- **Success (dry-run, multi-image):** 7-step plan; exit 0.
- **Loading / multi-call in flight:** the upload (`PUT`) steps are discrete steps
  between init and post (spec §6 "multi-call in flight").
- **Error — unexpected response:** missing `uploadUrl`/URN → `execute` refuses
  (exit 1), cited.
- **Invalid input:** missing manifest/`pdf` (document) or 0/>20 attachments
  (multi-image) → exit 2, cited, no plan write.
- **Live no-op (this sprint):** `--live` linkedin row, gate passing → honest no-op
  notice, exit 0, nothing posted (§1.2).

---

## 11. Verification — commands the Evaluator runs

All from repo root `/Users/prithviputta/Downloads/terrem-marketing-loops`.

**Precondition — frozen asset present:**
```
python3 -c "import json;d=json.load(open('content/2026-07-09-anarock-vs-propequity/render/manifest.json'));print(d['pdf'])"
```
Expected: `carousel.pdf`. If missing/modified, gate clauses 3–6 are SKIP.

**Gate clause 1 — new suite green:**
```
python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_publish_api.py'
```
Expected: `OK`, 0 failures (Sprint-003 cases as consciously updated + new
Sprint-004 cases).

**Gate clause 2 — no regression, full suite green:**
```
python3 -m unittest discover -s tools/marketing-loops/tests -p 'test_*.py'
```
Expected: `OK`, zero failures/errors (all prior suites).

**Gate clause 3 — dry-run real asset, linkedin 3-step DOCUMENT plan, no network, no queue change:**
```
cp content/publish-queue.json /tmp/q.before
python3 tools/marketing-loops/publish_api.py --week 2026-W28 ; echo "exit=$?"
python3 -c "import json;d=json.load(open('content/publish-plan.json')); r=[x for x in d['rows'] if x['channel']=='linkedin'][0]; print('steps',len(r['steps'])); [print(s['method'],s['url']) for s in r['steps']]"
diff content/publish-queue.json /tmp/q.before && echo QUEUE-UNCHANGED
```
Expected: exit 0; `steps 3`; lines `POST …/rest/documents`, `PUT <li-upload-url-1>`,
`POST …/rest/posts`; `QUEUE-UNCHANGED`. The instagram row is still `steps 8`.

**Gate clause 4 — fidelity + versioned headers + secrets + placeholders + determinism:**
```
python3 -c "import json;d=json.load(open('content/publish-plan.json')); r=[x for x in d['rows'] if x['channel']=='linkedin'][0]; b=json.dumps(r); print('REDACTED' if 'Bearer <REDACTED>' in b else 'MISSING-REDACTION'); print('version-hdr' if 'LinkedIn-Version' in b and 'X-Restli-Protocol-Version' in b else 'MISSING-HDR'); print('placeholders' if '<li-document-urn>' in b and '<li-upload-url-1>' in b else 'MISSING-PLACEHOLDERS'); print('owner-ph' if '<LI_PERSON_URN>' in b else 'MISSING-OWNER'); print('mandated' if 'PUBLISHED' in b and 'PUBLIC' in b else 'MISSING-MANDATED')"
python3 tools/marketing-loops/publish_api.py --week 2026-W28 && cp content/publish-plan.json /tmp/p1
python3 tools/marketing-loops/publish_api.py --week 2026-W28 && diff content/publish-plan.json /tmp/p1 && echo DETERMINISTIC
grep -c 'carousel' tools/marketing-loops/publish_api.py
```
Expected: `REDACTED`, `version-hdr`, `placeholders`, `owner-ph`, `mandated`;
`DETERMINISTIC`. The `carousel` grep counts only PDF-filename / comment references
(no LinkedIn "carousel" POST TYPE — R4-B4); the Evaluator confirms no `/rest/*`
call names a carousel post type.

**Gate clause 5 — MULTIIMAGE flow (opt-in) is the OTHER flow, exactly one:**
```
python3 tools/marketing-loops/publish_api.py --week 2026-W28 --linkedin-post-type multi-image >/dev/null
python3 -c "import json;d=json.load(open('content/publish-plan.json')); r=[x for x in d['rows'] if x['channel']=='linkedin'][0]; print('steps',len(r['steps'])); b=json.dumps(r); print('multiImage' if 'multiImage' in b else 'NO'); print('no-documents' if 'rest/documents' not in b else 'HAS-DOCS')"
```
Expected: `steps 7`; `multiImage`; `no-documents` (exactly one flow, no
cross-contamination).

**Gate clause 6 — live no-op is honest (linkedin adapter not yet wired to post):**
```
printf 'LI_PERSON_URN=urn:li:person:SENTINEL\nLI_ACCESS_TOKEN=SENTINEL_LITOKEN\nPUBLIC_ASSET_BASE_URL=https://assets.example/social-assets\n' > /tmp/li.env
python3 tools/marketing-loops/publish_api.py --week 2026-W28 --channel linkedin --live --env /tmp/li.env --date 2026-07-09 --i-have-verified-dry-run 2>&1 | tee /tmp/li.out ; echo "exit=${PIPESTATUS[0]}"
grep -c SENTINEL /tmp/li.out
grep -Ei 'permalink|posted' /tmp/li.out
diff content/publish-queue.json /tmp/q.before && echo QUEUE-UNCHANGED
```
Expected: exit 0; a cited "linkedin adapter ready; … Sprint 006; nothing posted"
notice; `SENTINEL` count `0`; NO real permalink/posted line; queue unchanged.

**Gate clause 7 — stdout linkedin block matches §6.1 + IG block unchanged:**
```
python3 tools/marketing-loops/publish_api.py --week 2026-W28
```
Expected: the linkedin block matches §6.1 (3 steps with `headers:` + `payload:`
lines, sorted header keys, compact payload JSON); the instagram block is IDENTICAL
to Sprint 003 (no `headers:`/`payload:` lines). (Exact hermetic byte-assert is
`test_stdout_template_exact`, gate clause 1.)

**Gate clause 8 — no-network AST unchanged + import silence:**
```
python3 -c "import ast; t=ast.parse(open('tools/marketing-loops/publish_api.py').read()); refs=[n for n in ast.walk(t) if (isinstance(n,ast.Attribute) and n.attr=='urlopen') or (isinstance(n,ast.Name) and n.id=='urlopen')]; calls=[n for n in ast.walk(t) if isinstance(n,ast.Call) and n.func in refs]; print(len(calls))"
python3 -c "import sys; sys.path.insert(0,'tools/marketing-loops'); import publish_api"
```
Expected: prints `1`; import exits 0 with empty stdout.

**Gate clause 9 — hygiene:**
```
git status --porcelain
```
Expected: only `tools/marketing-loops/publish_api.py` +
`tools/marketing-loops/tests/test_publish_api.py` modified; untracked
`content/publish-plan.json` (gitignored — must NOT be staged); no `.env`, no
secret, no db/upload artifact.

---

## 12. Security / hygiene assumptions
- Access token comes ONLY from an untracked `.env` (live/execute); loaded to
  memory, NEVER printed, NEVER written to any tracked file (B13, B17, B18). The
  dry-run plan carries `Bearer <REDACTED>` and never a real token; the person URN
  renders as `<LI_PERSON_URN>`. `.gitignore` already covers `.env` and
  `content/publish-plan.json`.
- The ONLY writes this sprint: `content/publish-plan.json` (dry-run). The queue
  file is NEVER written this sprint (live posting is Sprint 006).

## 13. Non-applicable sections
- Playwright / browser click paths: N/A — no HTTP surface served, no route, no
  rendered screen. Verification is `unittest` + the §11 CLI probes.
- Keyboard / focus / ARIA / contrast / responsive: N/A — no UI. "Design" here =
  plan legibility (the stdout per-step block is plain, wrappable text; the machine
  plan is stable-sorted for diffing — spec §7).

## 14. Non-goals (explicit)
- NO Facebook adapter (005): the facebook row keeps `steps: []` + its Sprint-005
  note this sprint. NO change to the Instagram adapter or IG tests.
- NO LinkedIn organic CAROUSEL post type — IMPOSSIBLE via the API (R4-B4). Only
  MultiImage or PDF Document.
- NO LinkedIn company-page / organization posting (Community Management API gated,
  R5-5) — member-profile / person-URN only (R5-6).
- NO live posting from the CLI, NO `queued → posted` transition, NO permalink
  RECORDING into the queue, NO `queue.write_queue` call, NO day-cap — all Sprint
  006. `execute()` is built + unit-tested but wired into the live `run()` path only
  in 006.
- NO byte upload in dry-run (the plan shows a binary placeholder; execute reads the
  file). NO reading of the wall clock; NO third-party dependency; stdlib only.
- NO change to the frozen `Transport`/`Response`/`RecordingTransport`/
  `RaisingTransport`/plan-envelope/7-step-key shapes. `run()`/`main()` gain only a
  new `--linkedin-version` keyword (backward-compatible default).
- NO real network in any test or in dry-run — provable (§9).

## 15. Acceptance summary (the contract's testable core)
Sprint 004 passes iff ALL hold:
1. Dry-run over the real asset (DEFAULT) emits a linkedin row with the exact §4.1
   3-step DOCUMENT flow (POST `/rest/documents?action=initializeUpload`; PUT
   `<li-upload-url-1>`; POST `/rest/posts` with `content.media` → `<li-document-urn>`),
   member-profile owner `<LI_PERSON_URN>`, versioned headers with `Bearer
   <REDACTED>`, permalink CONSTRUCTED from `<li-post-urn>` (no 4th call); stdout
   matches §6.1; machine JSON byte-identical on repeat; queue unchanged; zero
   network.
2. `--linkedin-post-type multi-image` emits the §4.2 7-step MULTIIMAGE flow; each
   linkedin row emits EXACTLY ONE flow with no cross-contamination and never a
   carousel post type (§8.5).
3. `execute()` (shared flow) walks the same calls against a mock: document + multi-
   image happy paths return the constructed permalink; unexpected response →
   `AdapterRefusal` (exit 1); §3.1 precondition failures → `AdapterUsageError`
   (exit 2) in dry-run AND execute; the parity test proves plan-steps ==
   transport-calls with dependent-value (`uploadUrl`) wiring (§8.4).
4. The `_drive_execute` generalization sends real bodies (JSON / file bytes),
   tolerates empty upload responses, and leaves IG execute + every IG test
   byte-identical (§8.7). The conditional headers/payload render leaves the IG
   stdout block byte-identical (§6, §8.7).
5. `--live` with a linkedin row is an honest no-op (exit 0, "nothing posted", no
   fake permalink, queue unchanged, no secret echoed) — posting deferred to 006.
6. Secrets: no access-token value in any stdout/JSON output; `Bearer <REDACTED>`
   at every render site; person URN as `<LI_PERSON_URN>` in dry-run. Determinism:
   no wall clock; `LinkedIn-Version` a fixed constant/flag.
7. Both full suites GREEN; the enumerated Sprint-003 linkedin assertions
   consciously updated (§7); the facebook row and every other prior behavior
   preserved; transport seam unchanged (exactly 1 `urlopen`); hygiene clean.
