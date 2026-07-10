---
name: loop-publish
description: Loop 5 (publish layer, up to the API boundary) — generate per-channel publish packages for a gate-passing content asset, then record manual posts back into the publish queue by invoking package.py and mark_posted.py. Args: a path under content/ and an ISO week. The gate is never bypassed; the skill writes no marketing copy.
---

# Loop 5 — Publish Layer (mechanical, up to the API boundary)

This layer is **mechanical, not hand-walked**. You do not write captions, invent
schedule times, or decide whether an asset may ship. You invoke the publish CLIs
and consume their machine-readable output.

A dry-run-first direct-publish CLI (`tools/marketing-loops/publish_api.py`) now
exists, but its `--live` posting path is **gated on `SETUP-CHECKLIST.md`** (platform
tokens + a public asset base URL) and is **not usable today** — no credentials exist
yet. Its `--dry-run` mode (the default) needs **zero credentials** and is useful now
for previewing the exact HTTP request plan. So the **only way to actually publish
today** remains: preview with a dry-run, **post by hand** on each platform, then
record the permalink back into the queue with `mark_posted.py`. The manual flow below
is preserved, not replaced.

Input: a `content/<slug>` path (the asset folder) and an ISO week `YYYY-Www`.

## Steps

1. **Gate + generate packages.** Run the packager on the asset folder:

   ```
   python3 tools/marketing-loops/package.py content/<slug> --week <YYYY-Www>
   ```

   This **re-runs the frozen publish gate first** (Sprint-002 `gate.py`) and
   **refuses** a non-PASS / failed-checks / KILLED asset — the skill never
   bypasses the gate. On success it writes one
   `content/<slug>/publish/<channel>.json` PACKAGE per declared channel and
   updates `content/publish-queue.json` with a `queued` row per channel
   (`schedule_slot` + `package_path` filled).

2. **Preview the request plan (dry-run — the DEFAULT).** Before posting, run the
   direct-publish CLI in dry-run to see the exact HTTP calls each channel adapter
   *would* make:

   ```
   python3 tools/marketing-loops/publish_api.py --week <YYYY-Www> --dry-run
   ```

   `--dry-run` is the **DEFAULT** when neither `--dry-run` nor `--live` is passed. It
   makes **zero network calls** and **zero queue-state change**, and writes the
   ordered per-row plan to **stdout** AND to `content/publish-plan.json`. It needs
   **no `PUBLIC_ASSET_BASE_URL`** and no tokens — response-dependent values render as
   named placeholders (e.g. `<ig-parent-creation-id>`, `<li-document-urn>`), any
   secret renders as `<REDACTED>`, and an absent public base URL renders as the
   placeholder `<PUBLIC_ASSET_BASE_URL>`. Read the plan to confirm fidelity, then
   post by hand (below).

3. **Read each package and post BY HAND.** For each channel, open
   `content/<slug>/publish/<channel>.json` and read:
   - `caption` — the final caption text (authored body + the correct per-channel
     UTM link). Post it **verbatim**; do not edit the copy or the link.
   - `attachments` — the exact ordered PNG paths to attach.
   - `schedule_slot` — the assigned morning/evening A/B bucket + default time
     (an A/B hypothesis, not a fixed real time).

   Post the caption + attachments on the platform yourself. The skill supplies
   **no copy of its own** and adds **no taste judgement** — it reports the
   package fields verbatim.

4. **Record each manual post.** After a post is live, capture its permalink and
   run, per channel:

   ```
   python3 tools/marketing-loops/mark_posted.py <slug> <channel> \
     --posted-on <YYYY-MM-DD> --permalink <https://...>
   ```

   This transitions that `(slug, channel)` queue row `queued` → `posted` and
   records the date + permalink. It is **intentionally non-idempotent**: a second
   mark-posted on an already-`posted` row is **refused** (exit 1) — the
   no-double-post guard.

## Exit codes — report the tool's message, never guess or auto-fix

- `0` — success (packages written + queue updated; or a post recorded).
- `1` — **domain refusal**: `package.py` gate refusal (list each cited
  `[<code>] <message>` verbatim), or `mark_posted.py` on an already-`posted` row.
  Do **not** re-render, rewrite copy, or force a pass — surface the reason and stop.
- `2` — **precondition / usage error**: missing caption body (add a
  `caption:<channel>` or `caption:all` block to `captions.md` — the tool never
  invents copy), invalid Flywheel UTM (cited Sprint-001 code, e.g.
  `campaign-mismatch`), absent/empty manifest, unmapped/zero channels, or bad
  arguments. Report the tool's precondition message; do not auto-fix.

## Verdict to the operator

- `package.py` exit 0 → packages are ready; post each channel by hand, then
  `mark_posted.py` per channel with the real permalink.
- `package.py` exit 1 → **blocked** by the gate. List each `[<code>] <message>`.
  Do not publish; do not auto-fix.
- `package.py` exit 2 → **precondition unmet**. Report the exact message (missing
  caption / invalid UTM / absent manifest / channels). The tool wrote nothing.

## Direct-publish CLI (`publish_api.py`) — dry-run today, live gated

`publish_api.py` is the direct-publishing layer up to and across the platform API
boundary. It reads the same frozen `content/publish-queue.json`, selects `queued`
rows for a `--week`, and drives the correct channel adapter (Instagram / LinkedIn /
Facebook). It has two modes.

### Dry-run (DEFAULT) — works today, no credentials

```
python3 tools/marketing-loops/publish_api.py --week <YYYY-Www> --dry-run
```

- `--dry-run` is the DEFAULT when neither `--dry-run` nor `--live` is given.
- Emits the ordered, per-row HTTP request plan to **stdout** and to
  `content/publish-plan.json` (deterministic: same inputs ⇒ byte-identical plan).
- **Zero network calls, zero queue-state change.** No `PUBLIC_ASSET_BASE_URL` and no
  tokens required; when the base URL is absent it renders as the placeholder
  `<PUBLIC_ASSET_BASE_URL>`.
- Response-dependent values render as **named placeholders** (e.g.
  `<ig-child-container-id-1>`, `<ig-parent-creation-id>`, `<li-document-urn>`,
  `<li-upload-url-1>`); every secret renders as `<REDACTED>`.

### Live (GATED) — not usable today

```
python3 tools/marketing-loops/publish_api.py --week <YYYY-Www> --live \
  --date <YYYY-MM-DD> --i-have-verified-dry-run
```

`--live` actually posts and is **gated on completing `SETUP-CHECKLIST.md`**. It is
**not usable today** — the founder has not provisioned tokens or a public asset base
URL. Three preconditions are each checked independently (any missing ⇒ exit 2, cited,
no network, no write):

- **(a) Tokens** in an env file (default `./.env`, `--env PATH`): `IG_USER_ID`,
  `IG_ACCESS_TOKEN`, `LI_PERSON_URN`, `LI_ACCESS_TOKEN` — and only with
  `--enable-facebook`, also `FB_PAGE_ID`, `FB_PAGE_TOKEN`.
- **(b) `PUBLIC_ASSET_BASE_URL`** — from the env file or `--public-asset-base-url`.
- **(c) `--i-have-verified-dry-run`** — the explicit acknowledgment flag.

On a successful live post, the row transitions `queued → posted`, recording the
platform-returned `permalink` and the `--date` (never wall-clock) — the same
`mark_posted` semantics, with the same no-double-post guard: an already-`posted` row
is never re-posted. A per-day cap (default **3** posts/day across channels,
`--max-per-day N` override, keyed on `--date`) refuses the breaching row.

### Facebook flag and LinkedIn selector

- `--enable-facebook` is **default OFF** and marked `round-5-gap` (unverified,
  best-documented guess). With the flag OFF, a `facebook` queue row is **skipped with
  a notice** and does not fail the run or block the instagram/linkedin rows.
- `--linkedin-post-type {document,multi-image}` defaults to `document`; exactly one
  LinkedIn flow runs per row.

### Exit codes for `publish_api.py` — report verbatim, never bypass the gate

- `0` — success (dry-run plan emitted, or all selected rows posted + recorded).
- `1` — **domain refusal**: an already-`posted` row, an Instagram container `ERROR`,
  a rate-limit exceeded, or a day-cap breach. Cited on stderr.
- `2` — **usage / precondition**: missing/invalid queue or package, unknown channel,
  `--live` missing any of the three gate items, malformed `--week`/`--date`, or a
  carousel over 10 children. Cited on stderr; nothing is written.

**Report the tool's cited message verbatim.** Never auto-fix, never fabricate a
permalink, and never bypass the live gate. Tokens live only in the untracked `.env`,
are never printed and never written to any tracked file, and appear as `<REDACTED>`
in all output.
