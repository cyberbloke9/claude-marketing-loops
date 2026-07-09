---
name: loop-create
description: Loop 3 v2 — the creative engine. Turns a signal into a rendered, QA-passed, queued v2 carousel (hook × format selection, formats.md authoring, render, gate, enqueue). Args: signal reference (e.g. "2026-07-06 #2") or a raw topic for the reactive lane.
---

# Loop 3 v2 — Creative Engine

Output: `content/YYYY-MM-DD-<slug>/` containing `formats.md`, `meta.md`, `captions.md`, and a rendered+validated+queued asset. The old script.md flow remains only for reactive video takes.

## 1. Context (read before choosing anything)
`context/BUSINESS.md` (what a post must do, in priority order) · `context/BRAND.md` (voice + visual identity) · `personas/personas.md` + `personas/hook-bank.md` · `PIPELINE-V2.md` §4 (format library + hard rules) · `brand/brand-kit.md` §8 (blacklist) · the referenced signal in `signals/`.

## 2. Choose hook × format (the creative decision)
- Hook: prefer a proven bank hook adapted to the signal; new hooks get the next number, tagged NEW, mapped to a pain code.
- Format per slide, by story shape: single striking stat → BIG-NUMBER · multi-item evidence → RECEIPTS · two opposing claims → VS-CONTRAST · dated sequence → TIMELINE · rankings → LEADERBOARD · trend → CHART · utility steps → CHECKLIST.
- Default shape: 3-slide carousel — cover (the hook, one dominant element) → evidence → CHECKLIST with inline `So-what:` + `Source:`. One dataset per post; if it needs two, it's two posts.
- Record the cover pattern (BIG-NUMBER | CHART-FIRST) in meta.md for the A/B log.

## 3. Author the files
- `formats.md` — grammar per format (see `content/2026-07-03-tgrera-enforcement-wave/formats.md` and `tests/inputs/fmt-*` as canon). Copy rules: specifics (city, number, date) mandatory; VS columns are ~410–450px wide at their type sizes so keep labels short; digits-only headlines can fail the V15 thumbnail band — include a descender glyph (j/y/p/g) or bump size.
- `meta.md` — signal ref, persona×pain, hook #, channels (only mapped channels: instagram/linkedin/youtube), UTM flywheel line (`utm_campaign` = date-stripped slug), target metrics, `cover-pattern` block, `provenance` block. Provenance rule: public dated sources only; TERREM DB price trends BLOCKED until Path A.
- `captions.md` — `caption:all` + optional per-channel blocks; captions may sell, the graphic must stand alone.

## 4. Run the pipeline (all must pass)
```
python3 tools/marketing-render/render.py content/<slug>       # fail-loud on grammar/overflow
python3 tools/marketing-render/validate.py content/<slug> --checked-on <YYYY-MM-DD>
python3 tools/marketing-loops/verify_utm.py content/<slug>
python3 tools/marketing-loops/enqueue.py content/<slug> --week <YYYY-Www>
python3 tools/marketing-loops/package.py content/<slug> --week <YYYY-Www>
```
On any FAIL: fix the *copy/spec*, never weaken a check. A KILLED or FAILed asset stays in the repo as a record.
