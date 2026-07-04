---
name: loop-qa
description: Loop 4 — run the mechanical design/QA gate on a content asset folder by invoking validate.py and consuming qa-verdict.json. Args: a path under content/. A single FAIL blocks publishing the asset.
---

# Loop 4 — Design/QA Gate (mechanical)

This gate is **mechanical, not hand-walked**. You do not eyeball the checklist.
You invoke the validator CLI and consume its machine-readable verdict. The
validator does all contrast math, pixel checks, safe-zone math, hook word-count,
source-stamp presence, blacklist scan, and provenance checks itself.

Input: a `content/<slug>` path (the asset folder).

## Steps

1. **Render only when absent.** If `content/<slug>/render/manifest.json` does
   **not** exist, run the renderer first:

   ```
   python3 tools/marketing-render/render.py content/<slug>
   ```

   If `render/manifest.json` already exists, **use it as-is** — do not silently
   overwrite an existing render. (Render once; render only when the render is
   absent.)

2. **Invoke the validator** on the `content/<slug>` path:

   ```
   python3 tools/marketing-render/validate.py content/<slug> --checked-on <YYYY-MM-DD>
   ```

   This writes `content/<slug>/render/qa-verdict.json` and appends the human
   verdict block to the asset's `meta.md`.

3. **Read and parse `qa-verdict.json`.** After validation, read and parse
   `content/<slug>/render/qa-verdict.json`. It is the stable machine contract —
   `verdict` is `"PASS"` or `"FAIL"`; `failed_checks` and `needs_review` are lists.

4. **Map the exit code, report the rule.** Exit `0` = PASS, `1` = FAIL,
   `2` = precondition/usage error (e.g. missing folder or malformed manifest).
   On exit `2`, report the validator's **precondition error**, not a verdict.
   Every reported failure carries the validator-emitted `rule` string verbatim;
   the skill adds **no independent taste judgement** of its own — rule citation only.

5. **Report `failed_checks` and `needs_review`.**
   - For each entry in `failed_checks`, print `id`, `detail`, and `rule`,
     formatted `<id> — <detail> (<rule>)`.
   - List each `needs_review` item as **informational / non-blocking** — these
     are the data-provenance human-review prompts; they do not block the gate.

6. **FAIL is terminal; the gate never auto-fixes.** A `FAIL` verdict **blocks
   publishing** the asset. The validator **reports** violations; it **does not
   fix** them and **never edits** the asset's copy or layout. Surface exactly
   what must change (the failed checks and their cited rules) and stop — do not
   re-render or rewrite to force a pass.

## Verdict to the operator

- `qa-verdict.json verdict == "PASS"` (exit 0) → asset may be scheduled.
- `qa-verdict.json verdict == "FAIL"` (exit 1) → **blocked**. List each failed
  check as `<id> — <detail> (<rule>)`. Do not publish; do not auto-fix.
