# Loop 4 — Design/QA Gate

Run per asset before publish. Every check is mechanical — pass/fail, no taste debates. A single FAIL blocks publish. Verdict is appended to the asset's `meta.md`.

## Typography
- [ ] Headings IBM Plex Sans 600; body Inter 400–500
- [ ] Headline ≥48px (1080×1080/1350) or ≥36px (story/reel); body ≥24px
- [ ] No condensed/thin faces on video overlays; no all-lowercase overlay text
- [ ] Line length 45–90 chars; line height 1.4–1.6×

## Color & contrast
- [ ] Text contrast ≥4.5:1 (normal) / ≥3:1 (≥24px or 18.5px bold) — check actual hex pairs
- [ ] Exactly one accent color, applied to the single most important element
- [ ] Text sits on a plain background (no photo/texture under type)

## Layout
- [ ] Correct canvas: 1080×1350 feed · 1080×1920 reel/story · 1200×627 LinkedIn link
- [ ] Critical content inside safe zone (center ~1000×1270 feed; clear of top 250px / bottom 440px on vertical)
- [ ] Legible when previewed at 360px width

## Chart integrity (any asset containing a chart)
- [ ] One chart, one claim
- [ ] Y-axis from zero, or break explicitly marked
- [ ] Source + as-of date printed on the graphic
- [ ] TERREM wordmark present
- [ ] No chartjunk (3D, gradients, decorative gridlines)
- [ ] The claim in the copy matches what the chart actually shows

## Carousel (if applicable)
- [ ] Slide 1 hook ≤10 words, one idea
- [ ] Slide 2 works as a standalone hook
- [ ] One idea per slide
- [ ] Final slide has CTA + TERREM link + source/date

## Script/copy
- [ ] Hook is from (or added to) `personas/hook-bank.md` and names a persona pain point
- [ ] Specifics present: locality, number, date
- [ ] CTA points to a live intel.terrem.in page (flywheel closes)
- [ ] No blacklisted stats (brand-kit.md §8)
- [ ] Voice passes the Candid Analyst do/don't table
- [ ] UTM-tagged link (`utm_source=<channel>&utm_medium=social&utm_campaign=<slug>`)

## Verdict
```
QA: PASS | FAIL
Failed checks: <list or none>
Checked by: <agent/human> on YYYY-MM-DD
```
