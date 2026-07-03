---
name: loop-qa
description: Loop 4 — run the mechanical design/QA gate on a content asset folder. Args: path under content/. A single FAIL blocks publish.
---

# Loop 4 — Design/QA Gate

Evaluate the given `content/<folder>/` against every check in `brand/qa-checklist.md`. Rules live in `brand/brand-kit.md` — cite the rule for any failure.

1. Read the asset's four files + `brand/qa-checklist.md` + `brand/brand-kit.md`.
2. Walk every checklist item literally. For items requiring rendered graphics (contrast, px sizes, safe zones): if only specs exist, verify the specs declare compliant values; if image files exist, inspect them (Read the image) and measure.
3. Check the copy: blacklisted stats (brand-kit §8), voice table, specifics, UTM link, hook-bank linkage.
4. Append the verdict block to the asset's `meta.md`:
   - `QA: PASS` — ready to schedule.
   - `QA: FAIL` + failed checks with the violated rule. Do not fix silently; list what must change.

Be adversarial. The gate exists to catch the asset that *almost* passes — a truncated y-axis, a missing as-of date, an 11-word hook slide.
