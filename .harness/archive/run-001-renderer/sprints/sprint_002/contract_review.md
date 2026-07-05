VERDICT: ACCEPT
SCORE: n/a
BLOCKERS: 0
HIGH: 0

## Summary

The revised contract for Sprint 002 (Carousel Renderer + Manifest) is **approvable**. Both findings from the prior REJECT have been resolved with concrete fixes.

## Prior Findings — Resolution

### Finding CR-001: Background dominance assertion (BLOCKER) — RESOLVED ✓

**Prior Issue:** The variable `bgc` (background hit count) was computed but never asserted on.

**Fix Applied:** Line 387 of §9 attack script now contains:
```python
assert bgc >= 1800, (s["id"], "bg does not dominate canvas", bgc)
```

The assertion verifies that at least 90% of deterministic-stride pixel samples land on the background token `#faf8f3`, closing the loophole where a renderer with the wrong background (gradient, wrong hex, or omitted fill) would pass. This is a hard requirement per spec §6 ("bg token dominates canvas").

**Verification:** The attack script will now FAIL if the background does not dominate the canvas as required.

---

### Finding CR-002: Text-content verification (HIGH) — RESOLVED ✓

**Prior Issue:** §5 enumerated exact text strings as "MUST contain" requirements, but the attack script (§9) had zero text-content assertions. Silent omission of entire sentences would pass.

**Fix Applied:** Lines 427–470 of §9 now contain comprehensive exact-text verification:
```python
expected = {
    "carousel-01": [
        ("hook", "Jubilee Hills just got cheaper. Medchal rose 19%."),
        ("body", "Same city. Same 3 months."),
    ],
    "carousel-02": [
        ("headline", "\"Hyderabad prices are rising\" is a meaningless sentence."),
        # ... all 8 slides enumerated with exact (role, text) pairs
    ]
}
for sid, pairs in expected.items():
    surf=[x for x in surfaces if x["id"]==sid][0]
    got={(e["role"], e["text"]) for e in surf["elements"]}
    for role, text in pairs:
        assert (role, text) in got, ("MISSING/CORRUPT COPY", sid, role, repr(text), "actual:", sorted(got))
    assert len(surf["elements"])==len(pairs), (sid, "element count", len(surf["elements"]), "!=", len(pairs), sorted(got))
```

This closes the "silent omission / stale copy / mid-word corruption" loophole. The manifest cannot claim to have rendered the authored copy while dropping or mangling sentences.

**Verification:** The attack script will now FAIL if any required text is missing, corrupted, or if phantom text elements are present.

---

## Contract Quality: Detailed Assessment

### Specificity ✓

Every requirement has a concrete, measurable value:
- Canvas dims: `1080×1350` (pixels)
- Font sizes: Hook 61px, headline 49px, body 25px, source-stamp 20px, wordmark 25px
- Margins: `MARGIN_X = 90`, `CONTENT_W = 900` → x∈[90,990]
- Line advance: `round(font_px * 1.4)`
- Em height: `round(font_px * 1.2)`
- Safe zone: x∈[40,1040], y∈[160,1180]
- Wordmark baseline: y ≈ 1250, right edge x = 990
- Inter-element gap: `round(0.7 * preceding_font_px)`
- Background check threshold: bgc ≥ 1800 / 2000 (90%)
- Token set: five specific hex values (#faf8f3, #1c1917, #57534e, #0f766e, #0d3d38)
- Determinism: decoded-RGBA SHA-256 identical across re-renders

### Testability ✓

Every requirement is verifiable:
- **§8 command 0:** `python3 -m unittest discover -s tools/marketing-render/tests -v` → exit 0
- **§8 command 1:** Render CLI → 8 PNG files + manifest.json
- **§8 command 2:** Determinism → SHA-256 hash comparison across two renders
- **§8 command 3:** Import purity → assert render.py imports only {os, sys, re, json, math, hashlib, argparse, pathlib, typing, measure, PIL}
- **§8 command 4:** Font vendoring → assert four TTF files exist, no system/ruflo font paths in source
- **§9 attack script:** 25+ assertions covering schema, dims, tokens, type-sizes, safe zones, ink presence, hook count, word limit, source-stamp, wordmark, exact text content, element count

### Completeness ✓

- **Scope clarity:** §0 explicitly states "carousel text-slide rendering only, no browser/web UI, no chart plotting"
- **Dependencies:** Stated — "Depends on Sprint 001 (measure.py, PASSED)"
- **In-scope files:** §2 enumerates all creates/modifies (7 created files, 3 carousel.md edits, runtime outputs)
- **Input grammar:** §3 fully specifies how carousel.md is parsed (preprocessing, slide segmentation, element extraction, three copy-preserving edits)
- **Output format:** §5.3 provides complete JSON schema for manifest.json
- **Expected output:** §5 enumerates all 8 carousel surfaces with exact element lists, roles, font sizes, weights, colors, and text
- **Error states:** §6 covers missing folder, missing carousel.md, unparseable lines, missing fonts, missing glyphs, stack overflow, success, determinism, anti-stub
- **Non-goals:** §11 clearly lists what's NOT in scope (1080×1920 chart card, validator, qa-verdict.json, meta.md verdict append, qa-checklist.md edits, CI/scheduling)

### No Ambiguities ✓

- Layout math is deterministic (integer division specified)
- Text wrapping is deterministic (greedy word-wrap, getlength measurement)
- Vertical centering uses integer division ("deterministic")
- PNG serialization is deterministic (json.dumps with sort_keys=True, ensure_ascii=False, trailing newline)
- Fonts are vendored locally (no system fonts, no network)
- Font size mapping is precise (e.g., em_height = round(font_px * 1.2), within ±25% tolerance for Sprint 004 glyph-size cross-check)

### No Loopholes ✓

- **Stub PNG loophole:** V3 anti-stub check (§9 lines 399–404) verifies declared ink is actually present inside bbox
- **Silent copy omission loophole:** CR-002 fix (§9 lines 427–470) asserts exact (role, text) pairs and element count
- **Wrong background loophole:** CR-001 fix (§9 line 387) asserts bg token dominates canvas (≥90% samples)
- **Token color loophole:** All declared colors validated against is_brand_token() and must equal one of five tokens
- **Determinism loophole:** Concrete SHA-256 equality check across two renders, decoded-RGBA format (immune to PNG container variance)

---

## Verdict

The contract is **specific, testable, and complete**. Both prior blockers have been fixed. No new defects identified. Ready for generation.

