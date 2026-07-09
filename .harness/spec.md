# Product Spec

## 1. Original Request

Build `tools/marketing-loops/publish_api.py` — the direct-publishing layer for the TERREM marketing-loop system — in **dry-run-first** form (no platform credentials exist yet; live verification happens later when the founder completes `SETUP-CHECKLIST.md`).

Verbatim scope from the requester:

> Build publish_api.py — the direct-publishing layer — for the TERREM marketing-loop system in the existing repo, in DRY-RUN-FIRST form (no platform credentials exist yet; live verification happens later when the founder completes SETUP-CHECKLIST.md). Ground truth for all API facts: RESEARCH.md Round 4 Part B (R4-B1..B4) and Round 5 (R5-1..R5-7) — verified against official Meta/LinkedIn docs. Read PIPELINE-V2.md §6 for the finalized architecture.
>
> (1) A CLI that consumes the EXISTING publish queue (`content/publish-queue.json`, schema from run 2, frozen) and its per-asset publish packages: for each queued row, drives the correct channel adapter, and on success performs the same queued→posted transition `mark_posted.py` does (same no-regress rules), recording the returned permalink.
> (2) Channel adapters faithful to the verified API surfaces (Instagram / LinkedIn / Facebook Page).
> (3) Modes: `--dry-run` is the DEFAULT; `--live` is gated on env + config + an explicit acknowledgment flag. Per-day post cap enforced in code (default 3/day across channels).
> (4) Conscious frozen-module extension: add `facebook` to the channel universe.
> (5) Tests with MOCKED transport only; NO real network calls anywhere in tests or dry-run — provable.
> (6) `/loop-publish` skill updated; README section added.
>
> Constraints: Python stdlib only (urllib for the transport), deterministic dry-run output, secrets never printed/committed, everything in-repo. Verification: evaluator runs the dry-run against the REAL queued asset (`2026-07-09-anarock-vs-propequity`, 2 queued rows) and inspects the emitted request plan for fidelity; attacks with fixtures; confirms all prior suites stay green.

Ground-truth sources (already in the repo, read them; do not re-derive API facts):
- `RESEARCH.md` — Round 4 Part B (R4-B1..B5) and Round 5 (R5-1..R5-7). These are the ONLY authority for API surface facts. The DO-NOT-USE blacklist in RESEARCH.md is binding (see §9).
- `PIPELINE-V2.md` §6 — the finalized publisher architecture.
- `SETUP-CHECKLIST.md` — the founder's non-code dependencies (accounts, tokens, public asset hosting).

## 2. Product Goal

A single stdlib-only CLI, `publish_api.py`, that reads the frozen publish queue and per-asset packages and, for each `queued` row, emits a faithful, inspectable plan of every HTTP request the correct platform adapter *would* make (dry-run, the default) — or, once credentials exist and the operator explicitly acknowledges, actually posts and records the permalink back into the queue (live). It ships useful and safe with zero credentials.

## 3. Target User

The TERREM founder-operator (also the `/loop-publish` skill acting on their behalf). They already know: the existing marketing-loops toolchain (`package.py`, `mark_posted.py`, the queue), how to run a Python CLI, and how to read JSON. They should NOT need to know: any platform's raw API URLs from memory, how to hand-craft container/upload flows, or how to keep secrets out of stdout — the tool guarantees all of that. They have NO platform credentials today and must get full value from the dry-run without any.

## 4. Core User Stories

1. **Preview (default).** As the operator, I run `publish_api.py --week 2026-W28` with no credentials and get, for each queued row, the exact ordered list of HTTP calls that would be made per channel — printed to stdout and written to `content/publish-plan.json` — with zero network activity and zero change to queue state.
2. **Inspect fidelity.** As the evaluator, I read the emitted plan and confirm each adapter's call sequence matches the verified API flow (IG two-step container flow; LinkedIn initializeUpload + posts; Facebook photos + feed), with secrets redacted and dependent values shown as named placeholders.
3. **Go live (gated).** As the operator, once `.env` holds tokens, `PUBLIC_ASSET_BASE_URL` is set, and I pass `--i-have-verified-dry-run`, I run `--live` and each successful row transitions `queued → posted` with the returned permalink recorded — exactly as `mark_posted.py` would.
4. **Be protected from myself.** As the operator, if I try to go live without tokens, without the public base URL, or without the acknowledgment flag, the tool refuses with a cited message and posts nothing. If I would exceed the daily cap, it refuses the offending row. If a row is already `posted`, it is never re-posted.
5. **Extend to Facebook consciously.** As the maintainer, `facebook` is now a first-class channel across the frozen modules, but the Facebook adapter (an unverified round-5 gap) only runs behind an explicit `--enable-facebook` flag defaulting OFF.

## 5. Required Behaviors

Each behavior is atomic and testable with a mocked transport.

### 5.1 CLI shape and queue consumption
- B1. `publish_api.py` is a stdlib-only CLI at `tools/marketing-loops/publish_api.py`, consistent with the existing `tools/marketing-loops/` toolchain (same `sys.path.insert(_HERE)` import pattern, same exit-code philosophy).
- B2. It reads the queue via the frozen `queue.py` helpers (`load_queue`) at `content/publish-queue.json` by default (overridable with `--queue PATH`), and selects rows with `state == "queued"`. `posted` rows are never re-processed.
- B3. It filters to a run scope: `--week YYYY-Www` (required) limits to rows whose `week` matches; optional `--slug` and `--channel` narrow further. Processing order is deterministic: ascending `(slug, channel)`.
- B4. For each selected row it loads that row's package JSON at `row["package_path"]` (e.g. `content/<slug>/publish/instagram.json`). A missing/unreadable package is a precondition error (exit 2, cited), not a silent skip.
- B5. The package fields consumed: `caption` (verbatim, includes the UTM link already), `attachments` (ordered PNG repo-relative paths), `channel`, `slug`, `schedule_slot`. The tool NEVER edits caption copy or the link.

### 5.2 Dry-run (the DEFAULT mode)
- B6. `--dry-run` is the default when neither `--dry-run` nor `--live` is passed. It renders the FULL request plan: for every HTTP call that would be made, the `method`, full `url`, `params`/query, request `headers`, and request `payload`/body.
- B7. The plan is written BOTH to stdout (human-readable) AND to `content/publish-plan.json` (machine-readable, deterministic JSON: `sort_keys=True`, `indent=2`, single trailing newline — mirror `queue.dumps` style) next to the queue.
- B8. Dry-run makes ZERO network calls and does NOT transition any queue state and does NOT write the queue. Provable: running dry-run with a transport whose every method raises must still exit 0 and produce the full plan.
- B9. Dry-run output is DETERMINISTIC: no wall-clock anywhere. The only dates permitted are those supplied via `--week`/`--date` args (the API payloads never read the current time). Same inputs ⇒ byte-identical `publish-plan.json`.
- B10. **Dependent-value placeholders.** Values that in a live run come from a prior response (IG child-container IDs feeding the parent `children` param; IG parent `creation_id` feeding `media_publish`; LinkedIn image/document URNs and upload URLs from `initializeUpload`) are rendered in the dry-run plan as named deterministic placeholders, e.g. `<ig-child-container-id-1>`, `<ig-parent-creation-id>`, `<li-image-urn-1>`, `<li-upload-url-1>`, `<li-document-urn>`. This keeps the plan both deterministic and inspectable.
- B11. **`image_url` construction.** Instagram/Facebook `image_url` is `PUBLIC_ASSET_BASE_URL` joined with the attachment path as `<PUBLIC_ASSET_BASE_URL>/<slug>/<filename>` (matching SETUP-CHECKLIST `…/social-assets/<slug>/…`). In dry-run, `PUBLIC_ASSET_BASE_URL` is NOT required; when absent it is rendered as the placeholder `<PUBLIC_ASSET_BASE_URL>` (optionally overridable via `--public-asset-base-url` for a fully concrete preview). The exact join rule is fixed and documented in the module.

### 5.3 Live mode (gated)
- B12. `--live` requires ALL THREE, each checked independently with a cited message, else exit 2 and no network / no write:
  - (a) a `.env` file (default `./.env`, `--env PATH`) holding the tokens needed by the selected channels: `IG_USER_ID`, `IG_ACCESS_TOKEN`, `LI_PERSON_URN`, `LI_ACCESS_TOKEN`, and (only if `--enable-facebook`) `FB_PAGE_ID`, `FB_PAGE_TOKEN`;
  - (b) a `PUBLIC_ASSET_BASE_URL` config value (from `.env` or `--public-asset-base-url`);
  - (c) the explicit `--i-have-verified-dry-run` acknowledgment flag.
- B13. `.env` parsing is minimal stdlib (`KEY=VALUE` lines, `#` comments). Secret values are loaded into memory only; never echoed.
- B14. On a successful live post for a row, the tool performs the SAME transition `mark_posted.py` performs: flip that one `(slug, channel)` row `queued → posted`, set `posted_date` (from `--date YYYY-MM-DD`, required in `--live`; never wall-clock), and set `permalink` (the platform-returned URL). It reuses the frozen queue semantics / no-regress rules (see B15).
- B15. **No-regress / no-double-post.** A row already `posted` is refused (no re-post), consistent with `mark_posted.py` (exit 1 domain refusal for that row). The write is deterministic via `queue.write_queue`. Other rows in the run are unaffected.
- B16. **Per-day cap.** Default 3 posts/day across all channels, `--max-per-day N` override. Cap is keyed on `--date`: count = (existing `posted` rows with `posted_date == --date`) + (posts made so far in this run). Rows are processed in `(slug, channel)` order; the row that WOULD breach the cap is refused (exit 1, cited "day-cap") and processing stops; already-posted rows in this run stand. This counting semantics is an assumption (see §10).

### 5.4 Secrets discipline
- B17. Token values from `.env` NEVER appear in stdout or in `publish-plan.json`. Every place a token would go, the plan shows a redaction token (e.g. `access_token=<REDACTED>`, `Authorization: Bearer <REDACTED>`). Testable: the literal secret string is absent from all emitted output.
- B18. `.env` is already in `.gitignore` (verified: `.gitignore` line `.env`). The tool never writes secrets to any tracked file.

### 5.5 Instagram adapter (verified — R4-B1/B2/B3, R5-1/R5-3)
Instagram Login flavor, host `graph.instagram.com`. Input images = `package.attachments` (ordered PNGs). Flow rendered/executed:
- B19. Optional pre-check: `GET https://graph.instagram.com/<IG_USER_ID>/content_publishing_limit?fields=quota_usage,quota_total&access_token=…`. If `quota_usage >= quota_total`, take the rate-limit-exceeded path: refuse the row (exit 1 in live; in dry-run just annotate). (Rate-limit discrepancy 50-vs-100 is noted, not hard-coded as a gate — R4-B3.)
- B20. For each attachment image (carousel child, `len ≤ 10` — reject >10 with a cited error, R4-B2): `POST https://graph.instagram.com/<IG_USER_ID>/media` with `image_url=<public url>`, `is_carousel_item=true`, `access_token`. Response → child container id.
- B21. Parent container: `POST /<IG_USER_ID>/media` with `media_type=CAROUSEL`, `children=<comma-joined child ids>`, `caption=<package caption>`, `access_token`. Response → parent creation id. (Single-image asset degrades to one `POST /media` with no `is_carousel_item`/`media_type=CAROUSEL`, then publish — support but the real asset is a 3-image carousel.)
- B22. Poll status: `GET /<parent-container-id>?fields=status_code&access_token=…` until `status_code == FINISHED`. A `status_code == ERROR` (or `EXPIRED`) is the container-error path → refuse the row (exit 1, cited). Polling is bounded (fixed max attempts constant; never a wall-clock sleep loop in tests — the transport returns canned statuses).
- B23. Publish: `POST /<IG_USER_ID>/media_publish` with `creation_id=<parent id>`, `access_token`. Response → media id.
- B24. Permalink: fetch `GET /<media-id>?fields=permalink&access_token=…` and record the returned `permalink` (or the documented equivalent). This is the value written to the queue row.

### 5.6 LinkedIn adapter (verified — R4-B4, R5-5/R5-6)
Member-profile posting only: person URN owner, `w_member_social`. **Organic carousels via API are impossible (R4-B4) — never attempt that post type.** The adapter IMPLEMENTS BOTH organic paths but EXECUTES EXACTLY ONE per row (one queue row has one `permalink`; never double-post):
- B25. Post-type selection: `--linkedin-post-type {document,multi-image}`, DEFAULT `document` (justified: `meta.md` declares `Channels: IG carousel, LinkedIn PDF`, and `render/carousel.pdf` exists). This default is an assumption (see §10). Live must emit exactly one of the two flows for a LinkedIn row.
- B26. **MultiImage flow** (input = `package.attachments`): for each image, `POST https://api.linkedin.com/rest/images?action=initializeUpload` with body `{"initializeUploadRequest":{"owner":"<LI_PERSON_URN>"}}` → returns `value.uploadUrl` + `value.image` (image URN); then upload the PNG bytes with `PUT <uploadUrl>` (Authorization Bearer); then `POST https://api.linkedin.com/rest/posts` with `author=<LI_PERSON_URN>`, `commentary=<caption>`, `content.multiImage.images=[<image urns>]`, `visibility=PUBLIC`, `lifecycleState=PUBLISHED`.
- B27. **Document (PDF) flow** (input = the PDF from `render/manifest.json` field `"pdf"`, e.g. `carousel.pdf`, NOT `package.attachments`): `POST /rest/documents?action=initializeUpload` with owner person URN → `uploadUrl` + document URN; `PUT <uploadUrl>` PDF bytes; `POST /rest/posts` with `content.media` referencing the document URN, `author`, `commentary`, visibility/lifecycle as above.
- B28. Required versioned headers on `/rest/*` calls: `Authorization: Bearer <REDACTED>`, `LinkedIn-Version: <YYYYMM>` (a fixed configurable constant — from `--linkedin-version` or a module default; never derived from wall-clock), `X-Restli-Protocol-Version: 2.0.0`.
- B29. Permalink: constructed from the returned post URN, e.g. `https://www.linkedin.com/feed/update/<urn>`. Record it to the queue row.

### 5.7 Facebook Page adapter (ROUND-5 GAP — R4-B5, unverified)
- B30. This adapter is clearly marked in code and output as `round-5-gap: best-documented-guess pending live verification`. It is behind `--enable-facebook`, DEFAULT OFF.
- B31. When a `facebook` row is queued and `--enable-facebook` is OFF: the row is SKIPPED with a cited notice ("facebook adapter disabled; pass --enable-facebook"), does NOT transition, and does NOT fail the whole run (instagram/linkedin rows still process). It is not a hard error.
- B32. When enabled, the documented-guess flow (input = `package.attachments`): for each image `POST /<FB_PAGE_ID>/photos` with `url=<public image url>`, `published=false`, Page token → unpublished photo id; then `POST /<FB_PAGE_ID>/feed` with `message=<caption>`, `attached_media=[{"media_fbid":"<photo id>"}, …]`, Page token → post id. Permalink constructed from the post id.

### 5.8 Frozen-module extension: add `facebook` (conscious, tested)
- B33. Add `facebook` to `utm.CHANNEL_SOURCE_MAP` — **appended LAST** (`{"instagram":…, "youtube":…, "linkedin":…, "facebook":"facebook"}`) so existing ordinals instagram=0/youtube=1/linkedin=2 are preserved and `schedule.py` bucket math for the existing three is unchanged.
- B34. Add `facebook`/`fb` aliases to `channels.py._ALIASES` so `Channels:` lines mentioning Facebook map instead of surfacing as unmapped (fixes the "Facebook currently exits 2" behavior).
- B35. Add a `facebook` entry to `schedule.py._TIMES` (morning/evening times) so `slot_for("...", "facebook")` does not `KeyError`.
- B36. `captions.py` and `queue.py` derive their channel set from `utm.CHANNEL_SOURCE_MAP` automatically — verify (no code change expected) that `captions.body_for(..., "facebook")` and `queue.VALID_CHANNELS` now include facebook.
- B37. **Consciously update existing tests** that assert the exact old channel set. Known sites to update (enumerate all, do not stop at these): `test_utm.py:40` (`sorted(CHANNEL_SOURCE_MAP) == ["instagram","linkedin","youtube"]`), `test_channels.py:25-28` (`CANONICAL_CHANNELS == ("instagram","youtube","linkedin")`) and the several `["instagram","youtube","linkedin"]` expectations, `test_queue.py:29` (`VALID_CHANNELS == …`), `test_schedule.py:61` (`CANONICAL_CHANNELS == …`). All prior suites must end GREEN.

### 5.9 No-network proof (import discipline)
- B38. `publish_api.py` MAY import `urllib.request`, but every network call routes through a single injectable transport seam. AST-provable: `urlopen`/`urllib.request` usage occurs at exactly ONE call site, inside the transport class; adapters call the injected transport, never `urlopen` directly. A new test asserts this (the existing AST test in `test_utm.py` is hardcoded to `utm.py`/`verify_utm.py` and does not police this module — a new equivalent is required).
- B39. The default transport used in tests and by the raising-transport proof is a fake; NO test and NO dry-run ever opens a real socket.

### 5.10 Exit codes (mirror the toolchain convention)
- B40. `0` success (dry-run plan emitted; or all selected rows posted + recorded).
- B41. `1` domain refusal (a row already `posted`; container ERROR; rate-limit exceeded; day-cap breach). Cited on stderr.
- B42. `2` usage / precondition (missing/invalid queue; missing package; unknown channel; `--live` missing `.env` tokens / `PUBLIC_ASSET_BASE_URL` / `--i-have-verified-dry-run`; malformed `--week`/`--date`; >10 carousel children). Cited on stderr, no write.

## 6. States That Must Exist

- **Empty:** no `queued` rows in scope for `--week` → exit 0, plan/queue unchanged, a clear "nothing queued for <week>" message.
- **Success (dry-run):** full plan on stdout + `publish-plan.json`; queue untouched.
- **Success (live):** rows transitioned, permalinks recorded, queue written deterministically.
- **Loading/multi-call in flight:** container polling (`status_code` PENDING→FINISHED) rendered as discrete steps in the plan.
- **Error — container:** IG `status_code == ERROR/EXPIRED` → row refused (exit 1), cited.
- **Error — rate limit:** `content_publishing_limit` exceeded → row refused (exit 1), cited.
- **Invalid input:** missing package / malformed `--week` / >10 children / unknown channel → exit 2, cited.
- **Permission/precondition denied (live gate):** missing tokens / base URL / acknowledgment flag → exit 2, cited, no network.
- **Domain refusal:** already-`posted` row; day-cap breach → exit 1, cited.
- **Feature-flag off:** `facebook` row with `--enable-facebook` OFF → skipped with notice, no transition.
- **No-network proof:** raising transport in dry-run → still exit 0 with full plan.

## 7. Design Direction

This is a CLI + JSON tool; "design" = output legibility, fidelity, and safety ergonomics.
- **Fidelity over cleverness.** The dry-run plan must read like a faithful transcript of the verified API flows in RESEARCH.md R4-B/R5. An evaluator holding RESEARCH.md open must be able to check each call against the docs. No invented endpoints, no "publishing" misspelling of the `_publish` permission (blacklisted, R5-3).
- **Legible plan format.** Each row's plan is an ordered list of steps; each step shows `channel`, a human step label (e.g. "IG · create child container 1/3"), `method`, `url`, `params`, `headers`, `payload`. Machine JSON mirrors the same fields.
- **Redaction is visible, not silent.** Show `<REDACTED>` where a secret would be, so the reader knows a secret belongs there.
- **Anti-patterns to avoid:** hiding calls behind a helper so the plan under-reports steps; printing a secret "just in this one debug line"; emitting wall-clock timestamps that break determinism; a Facebook adapter that runs by default; a stub that prints a plan without actually walking the adapter code paths (the plan must be produced by the same adapter functions that live mode drives).
- **Accessibility / operability:** `--help` documents every flag with the gate requirements; every refusal cites WHY and WHAT to do; stdout plan is plain text wrappable in a terminal; the machine plan is stable-sorted for diffing.

## 8. Non-Goals

- No renderer, QA-gate, or caption authoring changes (those are prior runs). The tool consumes existing packages/renders; it never writes marketing copy.
- No third-party scheduler integration (Ayrshare/Buffer/etc.) — build-vs-buy is unresolved (R5-7); direct APIs only.
- No LinkedIn company-page / organization posting (gated Community Management API, R5-5) — member-profile only this run.
- No OAuth token acquisition / refresh flow — tokens are handed in via `.env` by the founder (SETUP-CHECKLIST).
- No public asset hosting/upload implementation — `PUBLIC_ASSET_BASE_URL` is assumed to already serve the PNGs (founder dependency).
- No live network calls in this deliverable's tests or default run — live posting is only exercised by the founder later.
- No change to the queue schema (frozen, schema_version "1").

## 9. Technical Constraints

- **Language/stack:** Python 3, standard library ONLY. `urllib.request` for the transport; `urllib.parse` for URL building; `json`, `argparse`, `pathlib`, `re`, `ast` (tests). No third-party packages.
- **Toolchain consistency:** live under `tools/marketing-loops/`, use the `_HERE = Path(__file__).resolve().parent; sys.path.insert` import pattern; reuse frozen `queue.py`, `utm.py`, `channels.py`, `schedule.py`, `captions.py` — never fork the channel map.
- **Determinism:** never read the wall clock. Dates come only from `--week`/`--date`. Deterministic JSON serialization (`sort_keys`, `indent=2`, trailing newline).
- **Security/privacy:** secrets only from untracked `.env`; never printed, never written to tracked files; `.env` stays gitignored. Redaction in all output.
- **Persistence:** the only writes are `content/publish-plan.json` (dry-run) and the queue file (live only, via `queue.write_queue`).
- **API-fact authority:** RESEARCH.md R4-B + R5 ONLY. Binding blacklist items: permission name is `instagram_business_content_publish` (NOT `…_publishing`); do NOT hard-assert a flat "50/24h" IG limit (check the endpoint); LinkedIn organic carousels are impossible (MultiImage or PDF Document only); Facebook Pages endpoints are UNVERIFIED (round-5 gap, flag + gate).
- **Everything in-repo:** no external services touched by this deliverable.

## 10. Risks and Ambiguities

1. **LinkedIn "MultiImage AND Document."** The request lists both flows for the LinkedIn adapter. A queue row has exactly one `permalink` and `(slug, channel)` is unique ⇒ one row = one post. RESOLUTION (safest default): implement BOTH flows, EXECUTE exactly one per row, selected by `--linkedin-post-type` defaulting to `document` (meta.md declares "LinkedIn PDF"; `carousel.pdf` exists). Both flows are mocked-transport tested; live never emits both for one row. If the founder wants MultiImage, they pass the flag. Flagged so downstream does not silently pick differently.
2. **Day-cap counting semantics.** "3/day across channels" is given; the counting rule is not. Assumption: keyed on `--date`; count = existing `posted` rows with that date + posts made this run; refuse the row that would breach (exit 1), let prior posts stand. Documented in module + here.
3. **Facebook endpoints unverified (R4-B5).** The whole FB adapter is a documented guess; mitigated by `--enable-facebook` default-OFF and explicit `round-5-gap` labels. Do not treat FB dry-run fidelity as authoritative.
4. **IG rate-limit discrepancy (R4-B3, 50 vs 100).** Do not hard-code either as a gate; check `content_publishing_limit` and compare `quota_usage`/`quota_total` at runtime. TERREM cadence is far below either.
5. **`PUBLIC_ASSET_BASE_URL` join shape.** Assumed `<base>/<slug>/<filename>` per SETUP-CHECKLIST `/social-assets/<slug>/…`. If the founder's hosting differs, only this join constant changes.
6. **LinkedIn-Version header value.** LinkedIn requires a `YYYYMM` version; must be a fixed configurable constant (default in module, `--linkedin-version` override), never wall-clock-derived — else determinism breaks.
7. **Frozen-module blast radius.** Appending `facebook` touches `utm`, `channels`, `schedule` and several existing test assertions (see B37). Risk: a missed `_TIMES` entry KeyErrors, or a missed test assertion fails a prior suite. Mitigation: grep for exact channel-set assertions and update all; run the FULL suite green before done.

## 11. Suggested Sprint Breakdown

Each sprint is independently contract-testable with a mocked transport. Adapters depend on the Sprint 002 transport + placeholder convention, so that lands first.

- **Sprint 001 — Frozen-module extension (facebook).** Append `facebook` to `utm.CHANNEL_SOURCE_MAP` (last), add `channels.py` aliases (`facebook`, `fb`), add `schedule.py._TIMES["facebook"]`, verify `captions`/`queue` pick it up. Enumerate and consciously update every existing test asserting the old channel set (B37). Contract: full existing suite green with facebook present; `Channels:` line with Facebook now maps instead of exit 2.
- **Sprint 002 — Transport seam + dry-run plan renderer + CLI skeleton.** Injectable HTTP transport (single `urlopen` call site) + a fake/recording transport + a raising transport for tests. CLI arg parsing (`--week/--slug/--channel/--dry-run/--live/--queue/--date/--max-per-day/--enable-facebook/--linkedin-post-type/--public-asset-base-url/--env/--i-have-verified-dry-run`), `.env` loader, live-gate precondition checks (B12), plan model + deterministic `publish-plan.json` writer + named-placeholder convention (B10) + redaction (B17). Contract: dry-run with no adapters wired still gates correctly and emits an empty-but-valid plan; missing-env/base-url/ack → exit 2; AST no-network test; raising-transport dry-run proof.
- **Sprint 003 — Instagram adapter.** Full container flow (B19–B24): rate-limit check, per-image child containers (≤10), parent CAROUSEL, poll status, publish, permalink fetch. Contract: happy carousel path (canned container ids/FINISHED/media id/permalink); container-error path; rate-limit-exceeded path; >10 children exit 2; dry-run plan fidelity vs R4-B2.
- **Sprint 004 — LinkedIn adapter.** Both flows (B25–B29): Document (default, PDF from manifest) and MultiImage (from attachments), versioned headers, person URN, permalink from URN. Contract: happy Document path; happy MultiImage path; exactly-one-flow-per-row; dry-run fidelity vs R4-B4/R5-6.
- **Sprint 005 — Facebook adapter (round-5-gap, gated).** `--enable-facebook` default OFF; skip-with-notice when off (B31); photos+feed guess flow when on (B32); `round-5-gap` labels. Contract: facebook row skipped when flag off (other rows proceed); flow rendered when flag on; clearly marked unverified.
- **Sprint 006 — Live transition, no-regress, day-cap, end-to-end.** Queue transition reusing `mark_posted` semantics (B14–B15), permalink recording, day-cap enforcement (B16), full run over the REAL asset `2026-07-09-anarock-vs-propequity` (2 queued rows) in dry-run. Contract: no-regress (already-posted refused, exit 1); permalink+posted_date written on live-with-mock-transport; day-cap breach refusal; real-asset dry-run emits a faithful 2-row plan; determinism (byte-identical `publish-plan.json` on repeat).
- **Sprint 007 — Skill + README.** Update `.claude/skills/loop-publish/SKILL.md`: dry-run flow as the DEFAULT operator path; live flow documented as gated on SETUP-CHECKLIST completion + the three live preconditions. Add a README section for `publish_api.py`. Contract: skill documents both modes, the gate, exit codes, and the facebook flag; README section present and accurate.
