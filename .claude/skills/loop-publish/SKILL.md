---
name: loop-publish
description: Loop 5 (publish layer, up to the API boundary) — generate per-channel publish packages for a gate-passing content asset, then record manual posts back into the publish queue by invoking package.py and mark_posted.py. Args: a path under content/ and an ISO week. The gate is never bypassed; the skill writes no marketing copy.
---

# Loop 5 — Publish Layer (mechanical, up to the API boundary)

This layer is **mechanical, not hand-walked**. You do not write captions, invent
schedule times, or decide whether an asset may ship. You invoke the publish CLIs
and consume their machine-readable output. There is **no live posting API and no
credentials** — the operator posts by hand on each platform and records the
permalink back into the queue.

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

2. **Read each package and post BY HAND.** For each channel, open
   `content/<slug>/publish/<channel>.json` and read:
   - `caption` — the final caption text (authored body + the correct per-channel
     UTM link). Post it **verbatim**; do not edit the copy or the link.
   - `attachments` — the exact ordered PNG paths to attach.
   - `schedule_slot` — the assigned morning/evening A/B bucket + default time
     (an A/B hypothesis, not a fixed real time).

   Post the caption + attachments on the platform yourself. The skill supplies
   **no copy of its own** and adds **no taste judgement** — it reports the
   package fields verbatim.

3. **Record each manual post.** After a post is live, capture its permalink and
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
