#!/usr/bin/env python3
"""Carousel renderer for the TERREM marketing-loop Asset Renderer + QA Gate.

Sprint 002. Reads ``content/<slug>/carousel.md``, renders each declared slide to a
``1080x1350`` PNG using vendored Inter and the locked brand tokens, and emits
``content/<slug>/render/manifest.json`` (spec s5.3) describing every text element
it drew.

Headless CLI raster tool. No browser, no network, no third-party dependency beyond
Pillow. Deterministic (R8): same input twice -> pixel-identical PNGs and byte-
identical manifest. Fonts are loaded ONLY from the vendored ``fonts/`` directory,
resolved from ``__file__`` -- never a system font.

Spec refs: s5.1 (R1, R3, R4, R7, R8, R9), s5.3 (manifest schema), s6 (states),
s7 (design), s9 (tokens, fonts, no-network); contract s3-s7.

Usage:
    python3 tools/marketing-render/render.py <asset-folder>
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Local measurement module (Sprint 001) lives beside this file.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import measure  # noqa: E402


# --- Locked layout + style constants (contract s4.2/s4.3) ----------------------

CANVAS_W = 1080
CANVAS_H = 1350
BG_TOKEN = "bg"            # -> measure.TOKENS["bg"] == "#faf8f3"
MARGIN_X = 90
CONTENT_W = 900           # text column x in [90, 990]
BAND_TOP = 160
BAND_BOTTOM = 1180
BAND_H = BAND_BOTTOM - BAND_TOP  # 1020
WORDMARK_TOP = 1220       # bottom-right wordmark band
WORDMARK_RIGHT = 990

# --- Chart-card layout constants (contract s5.2/s5.3 — vertical 1080x1920) ------
CHART_CANVAS_W = 1080
CHART_CANVAS_H = 1920
CHART_BAND_TOP = 280          # critical stack centered in [280, 1300]
CHART_BAND_BOTTOM = 1300
CHART_BAND_H = CHART_BAND_BOTTOM - CHART_BAND_TOP  # 1020
CHART_SOURCE_TOP = 1380       # source-stamp top (below band, < 1480 safe-zone)
CHART_WORDMARK_TOP = 1800     # wordmark top (bottom-right, V6-exempt band)
CHART_WORDMARK_RIGHT = 990    # wordmark right edge

_FONT_FILES = {
    400: "Inter-Regular.ttf",
    500: "Inter-Medium.ttf",
    600: "Inter-SemiBold.ttf",
    700: "Inter-Bold.ttf",
}
_FONTS_DIR = _HERE / "fonts"


# --- Font loading (R4: vendored only, resolved from __file__) -------------------

_FONT_CACHE = {}
_NOTDEF_CACHE = {}


def _font(weight, size):
    """Load a vendored Inter face at ``size`` pixels. Cached per (weight, size).

    Raises ``FileNotFoundError`` naming the missing file if the vendored TTF is
    absent (state s6: missing vendored font).
    """
    key = (weight, size)
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached
    fname = _FONT_FILES[weight]
    fpath = _FONTS_DIR / fname
    if not fpath.exists():
        raise FileNotFoundError("missing vendored font file: {}".format(fpath))
    font = ImageFont.truetype(str(fpath), size)
    _FONT_CACHE[key] = font
    return font


def _notdef_signature(font, weight, size):
    """Return the (size, bytes) signature of this face's .notdef glyph.

    Rendered from a private-use codepoint that is guaranteed absent, so any real
    character rendering to an identical raster is a tofu (missing glyph)."""
    key = (weight, size)
    sig = _NOTDEF_CACHE.get(key)
    if sig is None:
        mask = font.getmask("\U000F0000")
        sig = (mask.size, bytes(mask))
        _NOTDEF_CACHE[key] = sig
    return sig


def _assert_glyphs(text, font, weight, size, slide_no, role):
    """Anti-tofu guard (contract s4.4): every non-whitespace char must have a real
    glyph. A char rendering identically to .notdef raises RuntimeError naming the
    char, slide, and role -- never a silent .notdef box."""
    notdef_size, notdef_bytes = _notdef_signature(font, weight, size)
    for ch in text:
        if ch.isspace():
            continue
        mask = font.getmask(ch)
        if mask.size == notdef_size and bytes(mask) == notdef_bytes:
            raise RuntimeError(
                "missing glyph (tofu) for {!r} (U+{:04X}) on slide {} role {}".format(
                    ch, ord(ch), slide_no, role
                )
            )


# --- Element style table (contract s3.3) ---------------------------------------
# Each entry: (font_px, weight, color_token). "body-link-accent" is resolved at
# parse time depending on whether the slide carries a wordmark.

_HOOK = (61, 700, "ink")
_HEADLINE = (49, 700, "ink")
_BODY = (25, 400, "ink-muted")
_SOURCE = (20, 400, "ink-muted")
_LINK_ACCENT = (25, 500, "accent")
_LINK_MUTED = (25, 500, "ink-muted")
_WORDMARK = (25, 700, "accent-deep")

# Chart-card element styles (contract s3.3 / s5.6): (font_px, weight, color_token).
_CC_HEADLINE = (44, 700, "ink")
_CC_ORDER = (27, 500, "ink")
_CC_SOURCE = (20, 400, "ink-muted")
_CC_WORDMARK = (25, 700, "accent-deep")


# --- carousel.md parsing (contract s3) -----------------------------------------

_COMMENT_RE = re.compile(r"<!--.*?-->")
_SLIDE_HDR_RE = re.compile(r"^\*\*S(\d+)\b.*\*\*\s*$")
_QUOTE_RE = re.compile(r"^>\s*(.+)$")
_BODY_RE = re.compile(r"^(?:Sub|Body|Caption)\b[^:]*:\s*(.+)$")
_SOURCE_RE = re.compile(r"^Source:\s*(.+)$")
_LINK_RE = re.compile(r"^Link:\s*(.+)$")
_BRACKET_RE = re.compile(r"^\[.*\]$")


def _strip_line(raw):
    """Strip HTML comments then trailing whitespace (contract s3.1)."""
    return _COMMENT_RE.sub("", raw).rstrip()


def parse_carousel(md_text):
    """Parse carousel.md text into an ordered list of slide dicts.

    Each slide dict: ``{"n": int, "chart_ref": str|None, "elements": [ ... ]}``.
    Each element: ``{"role", "text", "font_px", "weight", "color"}`` (color is a
    resolved brand hex). Elements are in file order.

    Raises ``ValueError`` on an unrecognized non-empty line (naming slide+line) or
    if no slides are found (contract s3.3, s6 fail-loud).
    """
    lines = md_text.splitlines()

    # (s3.2) find slide header line indices.
    headers = []  # (index, slide_no)
    for i, raw in enumerate(lines):
        m = _SLIDE_HDR_RE.match(raw)
        if m:
            headers.append((i, int(m.group(1))))
    if not headers:
        raise ValueError("no slides found: expected at least one '**S<n> ...**' header")

    slides = []
    for hi, (start, slide_no) in enumerate(headers):
        end = headers[hi + 1][0] if hi + 1 < len(headers) else len(lines)
        body_lines = lines[start + 1:end]
        slides.append(_parse_slide(slide_no, body_lines))

    # ascending slide-number order (deterministic; file order already ascending).
    slides.sort(key=lambda s: s["n"])
    return slides


def _parse_slide(slide_no, body_lines):
    """Parse one slide body into elements (contract s3.3)."""
    cleaned = []
    for raw in body_lines:
        line = _strip_line(raw)
        if line.strip() == "" or line.strip() == "---":
            continue
        cleaned.append(line)

    # Two-phase: a Link's accent-vs-muted color depends on wordmark presence
    # anywhere in this slide (contract s3.3 Link note).
    has_wordmark = any("wordmark" in ln.lower() for ln in cleaned)

    elements = []
    chart_ref = None
    for line in cleaned:
        m = _QUOTE_RE.match(line)
        if m:
            role = "hook" if slide_no == 1 else "headline"
            style = _HOOK if slide_no == 1 else _HEADLINE
            elements.append(_mk_element(role, m.group(1), style))
            continue
        if _SOURCE_RE.match(line):
            # source-stamp renders the full line INCLUDING the "Source:" prefix
            # (spec s5 expected text + validator's "Source"/"as of" presence check).
            elements.append(_mk_element("source-stamp", line, _SOURCE))
            continue
        m = _BODY_RE.match(line)
        if m:
            elements.append(_mk_element("body", m.group(1), _BODY))
            continue
        m = _LINK_RE.match(line)
        if m:
            style = _LINK_MUTED if has_wordmark else _LINK_ACCENT
            elements.append(_mk_element("body", m.group(1), style))
            continue
        if _BRACKET_RE.match(line):
            chart_ref = "chart-spec.md"
            continue
        if "wordmark" in line.lower():
            elements.append(_mk_element("wordmark", "TERREM", _WORDMARK))
            continue
        raise ValueError(
            "unparseable line on slide {}: {!r}".format(slide_no, line)
        )

    return {"n": slide_no, "chart_ref": chart_ref, "elements": elements}


def _mk_element(role, text, style):
    font_px, weight, color_token = style
    color = measure.TOKENS[color_token]
    # Defensive: every emitted color must be a locked token (contract s3.3).
    if not measure.is_brand_token(color):
        raise ValueError("non-token color {} for role {}".format(color, role))
    return {
        "role": role,
        "text": text,
        "font_px": font_px,
        "weight": weight,
        "color": color,
    }


# --- chart-spec.md parsing (contract s3) ----------------------------------------

_CC_SURFACE_RE = re.compile(r"^Surface:\s*chart-card\s*$")
_CC_CANVAS_RE = re.compile(r"^Canvas:\s*(.+)$")
_CC_HAS_AXIS_RE = re.compile(r"^has_axis:\s*(true|false)\s*$")
_CC_HEADLINE_RE = re.compile(r"^Headline:\s*(.+)$")
_CC_ORDER_RE = re.compile(r"^Order:\s*(.+)$")
_CC_SOURCE_RE = re.compile(r"^Source:\s*(.+)$")
_FENCE_RE = re.compile(r"^\s*```")


def parse_chart_spec(md_text):
    """Parse ``chart-spec.md`` into a chart-card spec dict, or ``None``.

    Returns ``None`` when the file does NOT carry the ``Surface: chart-card``
    trigger (contract s3.1) -- the renderer then ignores it entirely (this is
    what keeps the hyd free-form chart-spec byte-identical: it has no marker).

    On a real chart-card spec, returns
    ``{"canvas": (1080, 1920), "has_axis": bool, "elements": [ ... ]}`` with
    elements in FILE ORDER (contract s3.4). Raises ``ValueError`` fail-loud on
    ``has_axis: true``, a bad ``Canvas:`` value, an unparseable line, or a
    missing required element (contract s3.5).
    """
    raw_lines = md_text.splitlines()

    # (s3.1) Trigger scan: only a chart card if the marker is present anywhere.
    if not any(_CC_SURFACE_RE.match(_strip_line(ln)) for ln in raw_lines):
        return None

    # (s3.2.3) When the spec lives inside a fenced block, parse only inside-fence
    # lines (fence markers skipped, prose/title outside the fence ignored). With
    # no fence at all, every line is parsed.
    has_fence = any(_FENCE_RE.match(ln) for ln in raw_lines)

    canvas = None
    has_axis = None
    elements = []
    in_fence = False
    for raw in raw_lines:
        if _FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if has_fence and not in_fence:
            continue
        line = _strip_line(raw)
        stripped = line.strip()
        if stripped == "" or stripped == "---":
            continue

        if _CC_SURFACE_RE.match(line):
            continue
        m = _CC_CANVAS_RE.match(line)
        if m:
            canvas = m.group(1).strip()
            continue
        m = _CC_HAS_AXIS_RE.match(line)
        if m:
            has_axis = (m.group(1) == "true")
            continue
        m = _CC_HEADLINE_RE.match(line)
        if m:
            elements.append(_mk_element("headline", m.group(1), _CC_HEADLINE))
            continue
        m = _CC_ORDER_RE.match(line)
        if m:
            elements.append(_mk_element("body", m.group(1), _CC_ORDER))
            continue
        m = _CC_SOURCE_RE.match(line)
        if m:
            # Render the captured group (not the raw line): the authored spec
            # doubles the marker (``Source: Source: ...``) so the stamp text is
            # a single ``Source: NewsMeter ...`` (contract s4 note / s5.6).
            elements.append(_mk_element("source-stamp", m.group(1), _CC_SOURCE))
            continue
        if "wordmark" in line.lower():
            # Literal rendered text is always TERREM (contract s3.3).
            elements.append(_mk_element("wordmark", "TERREM", _CC_WORDMARK))
            continue

        raise ValueError("unparseable chart-spec line: {!r}".format(line))

    # (s3.5) directive validation.
    if canvas is not None and canvas != "1080x1920":
        raise ValueError(
            "chart-spec Canvas must be 1080x1920, got: {!r}".format(canvas)
        )
    if has_axis is True:
        raise ValueError(
            "plotted-axis chart cards are not supported in Sprint 003 (non-goal); "
            "this card declares has_axis: true"
        )
    if has_axis is None:
        has_axis = False  # absent -> receipts-card default (no plotted axis).

    # (s3.4) required elements.
    n_headline = sum(1 for e in elements if e["role"] == "headline")
    n_source = sum(1 for e in elements if e["role"] == "source-stamp")
    n_wordmark = sum(1 for e in elements if e["role"] == "wordmark")
    if n_headline < 1:
        raise ValueError("chart-spec missing required element: Headline")
    if n_source < 1:
        raise ValueError("chart-spec missing required element: Source")
    if n_wordmark != 1:
        raise ValueError(
            "chart-spec must declare exactly one Wordmark, got {}".format(n_wordmark)
        )

    return {"canvas": (CHART_CANVAS_W, CHART_CANVAS_H),
            "has_axis": has_axis, "elements": elements}


# --- Layout (contract s4.3, deterministic integer math) -------------------------


def _wrap(text, font):
    """Greedy word-wrap into lines fitting CONTENT_W (deterministic getlength).

    A single word wider than CONTENT_W is placed alone (no mid-word break)."""
    words = text.split(" ")
    lines = []
    cur = ""
    for w in words:
        candidate = w if cur == "" else cur + " " + w
        if font.getlength(candidate) <= CONTENT_W or cur == "":
            cur = candidate
        else:
            lines.append(cur)
            cur = w
    if cur != "":
        lines.append(cur)
    return lines


def _measure_element(el):
    """Compute wrapped lines and visual height for an element.

    Returns ``(lines, width, height, line_advance, em_height)``."""
    font = _font(el["weight"], el["font_px"])
    lines = _wrap(el["text"], font)
    line_advance = round(el["font_px"] * 1.4)
    em_height = round(el["font_px"] * 1.2)
    width = math.ceil(max(font.getlength(ln) for ln in lines))
    height = (len(lines) - 1) * line_advance + em_height
    return lines, width, height, line_advance, em_height


def _layout_slide(slide):
    """Assign bboxes to every element. Returns a list of render-ops:
    ``{"el", "lines", "bbox", "line_advance", "font"}`` in file order.

    Stack roles (all except wordmark) are vertically centered in the band
    [BAND_TOP, BAND_BOTTOM]; wordmark is placed bottom-right. Raises ValueError
    if the stack is taller than the band (fail loud, no overflow)."""
    stack = [e for e in slide["elements"] if e["role"] != "wordmark"]
    wordmark = [e for e in slide["elements"] if e["role"] == "wordmark"]

    measured = [(e, _measure_element(e)) for e in stack]

    # total stack height = sum(heights) + inter-element gaps (0.7 * preceding font).
    stack_h = 0
    for idx, (el, mm) in enumerate(measured):
        stack_h += mm[2]
        if idx < len(measured) - 1:
            stack_h += round(0.7 * el["font_px"])

    if stack_h > BAND_H:
        raise ValueError(
            "slide {} content ({}px) taller than safe band ({}px)".format(
                slide["n"], stack_h, BAND_H
            )
        )

    ops = []
    y = BAND_TOP + (BAND_H - stack_h) // 2
    for idx, (el, mm) in enumerate(measured):
        lines, width, height, line_advance, em_height = mm
        bbox = [MARGIN_X, y, width, height]
        font = _font(el["weight"], el["font_px"])
        ops.append({"el": el, "lines": lines, "bbox": bbox,
                    "line_advance": line_advance, "font": font})
        y += height
        if idx < len(measured) - 1:
            y += round(0.7 * el["font_px"])

    for el in wordmark:
        lines, width, height, line_advance, em_height = _measure_element(el)
        x = WORDMARK_RIGHT - width
        bbox = [x, WORDMARK_TOP, width, height]
        font = _font(el["weight"], el["font_px"])
        ops.append({"el": el, "lines": lines, "bbox": bbox,
                    "line_advance": line_advance, "font": font})

    return ops


# --- Rendering (contract s4) ----------------------------------------------------


def render_slide(slide):
    """Render one slide to a PIL Image + build its manifest surface dict.

    Runs the anti-tofu guard on every run before drawing."""
    ops = _layout_slide(slide)
    bg_hex = measure.TOKENS[BG_TOKEN]
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), bg_hex)
    draw = ImageDraw.Draw(img)

    for op in ops:
        el = op["el"]
        _assert_glyphs(el["text"], op["font"], el["weight"], el["font_px"],
                       slide["n"], el["role"])
        x, y = op["bbox"][0], op["bbox"][1]
        for i, ln in enumerate(op["lines"]):
            draw.text((x, y + i * op["line_advance"]), ln, font=op["font"],
                      fill=el["color"], anchor="la")

    surface = {
        "id": "carousel-{:02d}".format(slide["n"]),
        "role": "carousel-slide",
        "png": "carousel-{:02d}.png".format(slide["n"]),
        "canvas": {"w": CANVAS_W, "h": CANVAS_H},
        "has_axis": False,
        "axis_min": None,
        "zero_based": None,
        "break_disclosed": None,
        "chart_ref": slide["chart_ref"],
        "elements": [
            {
                "text": op["el"]["text"],
                "role": op["el"]["role"],
                "font_px": op["el"]["font_px"],
                "weight": op["el"]["weight"],
                "color": op["el"]["color"],
                "bg": bg_hex,
                "bbox": list(op["bbox"]),
            }
            for op in ops
        ],
    }
    return img, surface


# --- Chart-card layout + render (contract s5) -----------------------------------


def _layout_chart_card(spec):
    """Assign bboxes to every chart-card element. Returns render-ops in FILE
    ORDER (contract s3.4). The headline+body critical stack is vertically
    centered in the band [CHART_BAND_TOP, CHART_BAND_BOTTOM]; source-stamp sits
    at a fixed y below the band; wordmark is bottom-right. Raises ValueError if
    the critical stack is taller than the band (fail loud, no overflow)."""
    elements = spec["elements"]
    stack = [e for e in elements if e["role"] in ("headline", "body")]

    measured = [(e, _measure_element(e)) for e in stack]
    stack_h = 0
    for idx, (el, mm) in enumerate(measured):
        stack_h += mm[2]
        if idx < len(measured) - 1:
            stack_h += round(0.7 * el["font_px"])
    if stack_h > CHART_BAND_H:
        raise ValueError(
            "chart-card content ({}px) taller than safe band ({}px)".format(
                stack_h, CHART_BAND_H
            )
        )

    op_by_id = {}

    y = CHART_BAND_TOP + (CHART_BAND_H - stack_h) // 2
    for idx, (el, mm) in enumerate(measured):
        lines, width, height, line_advance, em_height = mm
        bbox = [MARGIN_X, y, width, height]
        font = _font(el["weight"], el["font_px"])
        op_by_id[id(el)] = {"el": el, "lines": lines, "bbox": bbox,
                            "line_advance": line_advance, "font": font}
        y += height
        if idx < len(measured) - 1:
            y += round(0.7 * el["font_px"])

    for el in elements:
        if el["role"] == "source-stamp":
            lines, width, height, line_advance, em_height = _measure_element(el)
            bbox = [MARGIN_X, CHART_SOURCE_TOP, width, height]
            font = _font(el["weight"], el["font_px"])
            op_by_id[id(el)] = {"el": el, "lines": lines, "bbox": bbox,
                                "line_advance": line_advance, "font": font}
        elif el["role"] == "wordmark":
            lines, width, height, line_advance, em_height = _measure_element(el)
            x = CHART_WORDMARK_RIGHT - width
            bbox = [x, CHART_WORDMARK_TOP, width, height]
            font = _font(el["weight"], el["font_px"])
            op_by_id[id(el)] = {"el": el, "lines": lines, "bbox": bbox,
                                "line_advance": line_advance, "font": font}

    # Emit in file order (contract s3.4 / s5.6).
    return [op_by_id[id(el)] for el in elements]


def render_chart_card(spec):
    """Render the vertical chart card to a PIL Image + build its manifest surface.

    Runs the anti-tofu guard on every run before drawing (contract s5.4)."""
    ops = _layout_chart_card(spec)
    bg_hex = measure.TOKENS[BG_TOKEN]
    img = Image.new("RGB", (CHART_CANVAS_W, CHART_CANVAS_H), bg_hex)
    draw = ImageDraw.Draw(img)

    for op in ops:
        el = op["el"]
        _assert_glyphs(el["text"], op["font"], el["weight"], el["font_px"],
                       "chart-card", el["role"])
        x, y = op["bbox"][0], op["bbox"][1]
        for i, ln in enumerate(op["lines"]):
            draw.text((x, y + i * op["line_advance"]), ln, font=op["font"],
                      fill=el["color"], anchor="la")

    surface = {
        "id": "chart-card",
        "role": "chart-card",
        "png": "chart-card.png",
        "canvas": {"w": CHART_CANVAS_W, "h": CHART_CANVAS_H},
        "has_axis": spec["has_axis"],
        "axis_min": None,
        "zero_based": None,
        "break_disclosed": None,
        "chart_ref": None,
        "elements": [
            {
                "text": op["el"]["text"],
                "role": op["el"]["role"],
                "font_px": op["el"]["font_px"],
                "weight": op["el"]["weight"],
                "color": op["el"]["color"],
                "bg": bg_hex,
                "bbox": list(op["bbox"]),
            }
            for op in ops
        ],
    }
    return img, surface


# =============================================================================
# Renderer V2 — Format Library (Sprint 002, run 003). ADDITIVE.
# =============================================================================
# Everything below draws the batch-A format-slide templates (BIG-NUMBER,
# RECEIPTS, CHECKLIST) at 1080x1350 and emits schema_version "2" surfaces. The
# v1 code above (parse_carousel, render_slide, parse_chart_spec,
# render_chart_card, all _HOOK/_HEADLINE/_BODY/_SOURCE/_WORDMARK and _CC_*
# constants) is byte-unchanged (spec s10 Risk 1). Spec refs: s5.1 (R10-R14, R18,
# R19), s5.3; contract s1.1-s1.6.

# --- v2 locked style constants (contract s1.3; v1 constants untouched) ---------
# role -> (font_px, weight, color_token). All floors met by construction:
#   dominant 132 (>=48, and 132/30=4.4>=3 or 132/26=5.08>=3 with no-body fallback)
#   headline 52 (>=48) · body 30 (>=26) · so-what 30 (>=26) · source 26 (>=24)
_FMT_DOMINANT = (132, 700, "accent")        # the single hook figure (one accent)
_FMT_HEADLINE = (52, 700, "ink")            # context/eyebrow line
_FMT_BODY = (30, 500, "ink-muted")          # generic body / CHECKLIST step
_FMT_CHIP = (30, 700, "ink-muted")          # RECEIPTS chip text (weight-700 emphasis)
_FMT_SOWHAT = (30, 500, "ink-muted")        # stand-alone utility line
_FMT_SOURCE = (26, 400, "ink-muted")        # source-stamp
_FMT_WORDMARK = (26, 700, "accent-deep")    # brand-locked wordmark (R13)
# Sprint 003 (batch B) — one new constant; every batch-A/v1 constant untouched
# (contract s1.3). chart-label 30 >= 26 floor; ink token, drawn on bg (not bars).
_FMT_CHART_LABEL = (30, 500, "ink")         # CHART direct data label (Tufte)

# The batch-A formats (Sprint 002) and batch-B formats (Sprint 003). The renderer
# now accepts all seven (contract s1.1); a tag outside the union still fails loud.
_V2_BATCH_A_FORMATS = frozenset({"BIG-NUMBER", "RECEIPTS", "CHECKLIST"})
_V2_BATCH_B_FORMATS = frozenset({"TIMELINE", "VS-CONTRAST", "LEADERBOARD", "CHART"})
_V2_FORMATS = _V2_BATCH_A_FORMATS | _V2_BATCH_B_FORMATS

# v2 layout band (1080x1350). Content is centered in [top, bottom]; wordmark sits
# bottom-right (inside the (1080,1350) safe zone y_max 1310, forward-compat V6).
_V2_BAND_TOP = 170
_V2_BAND_BOTTOM = 1180
_V2_BAND_H = _V2_BAND_BOTTOM - _V2_BAND_TOP  # 1010
_V2_WORDMARK_TOP = 1240
_V2_WORDMARK_RIGHT = 990
_V2_GAP_FACTOR = 0.35        # inter-element gap = round(factor * preceding font_px)
_V2_CHIP_GAP = 16            # tight gap between consecutive chips
_V2_CHIP_PAD_X = 28          # chip inner horizontal padding
_V2_CHIP_PAD_Y = 20          # chip inner vertical padding
_V2_CHIP_RADIUS = 14         # chip corner radius (decorative)

# --- batch-B (Sprint 003) layout constants (contract s1.4) ---------------------
# CHART: zero-based horizontal --chart-up bars, direct chart-labels ABOVE each bar
# (labels sit on --bg, never on the colored bar — forward-compat V4 honesty).
_V2_BAR_TRACK_W = CONTENT_W  # 900px full track; the max-value bar fills it
_V2_BAR_H = 44               # bar rectangle height
_V2_BAR_LABEL_GAP = 8        # gap between a chart-label and its bar
_V2_BAR_ITEM_GAP = 26        # gap between consecutive bar items
# VS-CONTRAST: asymmetric side-by-side split. The dominant (side-A, accent) column
# is wider than the side-B headline-number column (reinforces the asymmetry theme
# and de-risks the 132px number's width). A 1px --border divider marks the split.
_V2_VS_DIVIDER_X = 560       # vertical divider x (decorative --border, 1px)
_V2_VS_LEFT_CX = 320         # side-A column center x (wider left half [90,560])
_V2_VS_RIGHT_CX = 790        # side-B column center x (right half [560,990])
_V2_VS_LEFT_HALF = (MARGIN_X, _V2_VS_DIVIDER_X - 20)   # [90, 540] usable
_V2_VS_RIGHT_HALF = (_V2_VS_DIVIDER_X + 20, WORDMARK_RIGHT)  # [580, 990] usable
_V2_VS_LABEL_GAP = 22        # gap between a side label and its number

# --- Deterministic multi-page PDF (Sprint 004, R15/R16) ------------------------
# The carousel PDF re-containers the exact format-slide 1080x1350 rasters, one
# page each, in manifest surface-list order. Byte-determinism (R16): Pillow's PDF
# driver otherwise stamps a per-run CreationDate/ModDate (time.gmtime) into /Info
# and derives /Title from the output basename. We suppress the dates (pass None),
# pin a fixed Producer + Title (path-independent), and rely on Pillow 11.3.0
# emitting no run-varying /ID. The transient nature of these constants keeps the
# bytes identical across independent process runs on the same environment.
# NOTE (disclosed): Pillow writes a fixed `created by Pillow <version> PDF driver`
# comment; that version string is environment-pinned, not a cross-machine promise.
_PDF_NAME = "carousel.pdf"
_PDF_PRODUCER = "TERREM marketing-render"
_PDF_TITLE = "TERREM carousel"

# --- formats.md parsing (contract s1.1) ----------------------------------------

_FMT_HDR_RE = re.compile(r"^\*\*F(\d+)\s+([A-Z][A-Z0-9-]*)\*\*\s*$")
_FMT_DIRECTIVE_RE = re.compile(
    r"^(Context|Headline|Body|Chip|Step|Event|Row|Bar|Dominant|So-what|Source):"
    r"\s*(.+)$"
)
_FMT_WORDMARK_RE = re.compile(r"^Wordmark\s*$")

# Last non-negative numeric run in a Bar: line (drives bar length, contract s1.1).
_FMT_BAR_NUM_RE = re.compile(r"\d+(?:\.\d+)?")

# directive keyword -> (element role, style tuple, is_chip). Sprint-003 additions:
#   Event -> dated event chip (reuses the RECEIPTS chip primitive), body/is_chip
#   Row   -> ranked leaderboard row, plain body
#   Bar   -> CHART direct chart-label (also carries a decorative proportional bar)
_FMT_DIRECTIVE_MAP = {
    "Dominant": ("dominant", _FMT_DOMINANT, False),
    "Context": ("headline", _FMT_HEADLINE, False),
    "Headline": ("headline", _FMT_HEADLINE, False),
    "Body": ("body", _FMT_BODY, False),
    "Chip": ("body", _FMT_CHIP, True),
    "Step": ("body", _FMT_BODY, False),
    "Event": ("body", _FMT_CHIP, True),
    "Row": ("body", _FMT_BODY, False),
    "Bar": ("chart-label", _FMT_CHART_LABEL, False),
    "So-what": ("so-what", _FMT_SOWHAT, False),
    "Source": ("source-stamp", _FMT_SOURCE, False),
}


def _mk_fmt_element(role, text, style, is_chip):
    """Build a v2 format-slide element dict (adds ``is_chip`` over _mk_element)."""
    el = _mk_element(role, text, style)
    el["is_chip"] = is_chip
    return el


def parse_formats(md_text):
    """Parse ``formats.md`` into an ordered list of format-slide dicts.

    Each slide: ``{"n": int, "format": str, "elements": [ ... ]}`` in file order.
    Header grammar ``**F<n> <FORMAT>**``; directive -> role mapping per contract
    s1.1. Enforces (fail-loud ``ValueError``, no partial write, contract s1.2/1.5):
      * unknown/unsupported format tag (batch A only) — names slide + tag
      * unparseable non-empty line — names slide + line
      * >10 slides (R14) — names the count
      * per-format required-role counts (exactly one dominant + one wordmark;
        RECEIPTS 2-4 chips; CHECKLIST >=2 steps)
    """
    lines = md_text.splitlines()

    headers = []  # (line_index, slide_no, format_tag)
    for i, raw in enumerate(lines):
        line = _strip_line(raw)
        m = _FMT_HDR_RE.match(line)
        if m:
            headers.append((i, int(m.group(1)), m.group(2)))
    if not headers:
        raise ValueError(
            "no format-slides found: expected at least one '**F<n> <FORMAT>**' header"
        )

    # R14: >10 declared format-slides is a fail-loud render error (contract s1.5).
    if len(headers) > 10:
        raise ValueError(
            "carousel declares {} format-slides; the cap is 10 (R14, "
            "Instagram API limit)".format(len(headers))
        )

    slides = []
    for hi, (start, slide_no, fmt) in enumerate(headers):
        if fmt not in _V2_FORMATS:
            raise ValueError(
                "unknown/unsupported format tag {!r} on slide F{} "
                "(supported: {})".format(
                    fmt, slide_no, ", ".join(sorted(_V2_FORMATS))
                )
            )
        end = headers[hi + 1][0] if hi + 1 < len(headers) else len(lines)
        body_lines = lines[start + 1:end]
        slides.append(_parse_format_slide(slide_no, fmt, body_lines))

    return slides


def _parse_format_slide(slide_no, fmt, body_lines):
    """Parse one format-slide block into elements + validate its role counts."""
    elements = []
    for raw in body_lines:
        line = _strip_line(raw)
        stripped = line.strip()
        if stripped == "" or stripped == "---":
            continue
        if _FMT_WORDMARK_RE.match(stripped):
            elements.append(_mk_fmt_element("wordmark", "TERREM", _FMT_WORDMARK, False))
            continue
        m = _FMT_DIRECTIVE_RE.match(line)
        if m:
            keyword, value = m.group(1), m.group(2).strip()
            role, style, is_chip = _FMT_DIRECTIVE_MAP[keyword]
            el = _mk_fmt_element(role, value, style, is_chip)
            if keyword == "Bar":
                # CHART bar length is driven by the LAST numeric run in the line
                # (contract s1.1). No numeric run -> fail-loud, no partial write.
                nums = _FMT_BAR_NUM_RE.findall(value)
                if not nums:
                    raise ValueError(
                        "CHART Bar line on format-slide F{} has no numeric value: "
                        "{!r}".format(slide_no, line)
                    )
                el["bar_value"] = float(nums[-1])
            elements.append(el)
            continue
        raise ValueError(
            "unparseable line on format-slide F{}: {!r}".format(slide_no, line)
        )

    _validate_format_roles(slide_no, fmt, elements)
    return {"n": slide_no, "format": fmt, "elements": elements}


def _validate_format_roles(slide_no, fmt, elements):
    """Enforce the per-format required-role rules (contract s1.2), fail-loud."""
    n_dominant = sum(1 for e in elements if e["role"] == "dominant")
    n_wordmark = sum(1 for e in elements if e["role"] == "wordmark")
    n_chip = sum(1 for e in elements if e.get("is_chip"))
    n_headline = sum(1 for e in elements if e["role"] == "headline")
    n_step = sum(1 for e in elements
                 if e["role"] == "body" and not e.get("is_chip"))
    n_chart_label = sum(1 for e in elements if e["role"] == "chart-label")
    n_source = sum(1 for e in elements if e["role"] == "source-stamp")

    if n_dominant != 1:
        raise ValueError(
            "format-slide F{} ({}) must declare exactly one dominant, got "
            "{}".format(slide_no, fmt, n_dominant)
        )
    if n_wordmark != 1:
        raise ValueError(
            "format-slide F{} ({}) must declare exactly one wordmark, got "
            "{}".format(slide_no, fmt, n_wordmark)
        )
    if fmt == "RECEIPTS":
        if not (2 <= n_chip <= 4):
            raise ValueError(
                "RECEIPTS slide F{} must have 2-4 Chip elements, got "
                "{}".format(slide_no, n_chip)
            )
    elif fmt == "CHECKLIST":
        if n_step < 2:
            raise ValueError(
                "CHECKLIST slide F{} must have at least 2 Step elements, got "
                "{}".format(slide_no, n_step)
            )
    elif fmt == "BIG-NUMBER":
        if n_headline < 1:
            raise ValueError(
                "BIG-NUMBER slide F{} must declare at least one Context/Headline, "
                "got {}".format(slide_no, n_headline)
            )
    elif fmt == "TIMELINE":
        # n_chip counts Event chips (the only chips on a TIMELINE slide).
        if n_chip < 2:
            raise ValueError(
                "TIMELINE slide F{} must have at least 2 Event chips, got "
                "{}".format(slide_no, n_chip)
            )
    elif fmt == "VS-CONTRAST":
        if n_headline != 1:
            raise ValueError(
                "VS-CONTRAST slide F{} must declare exactly one headline "
                "(the opposing side-B number), got {}".format(slide_no, n_headline)
            )
        if n_step < 2:
            raise ValueError(
                "VS-CONTRAST slide F{} must have at least 2 Body side-labels, got "
                "{}".format(slide_no, n_step)
            )
    elif fmt == "LEADERBOARD":
        # n_step counts plain body rows (Row directives) on a LEADERBOARD slide.
        if n_step < 2:
            raise ValueError(
                "LEADERBOARD slide F{} must have at least 2 Row elements, got "
                "{}".format(slide_no, n_step)
            )
    elif fmt == "CHART":
        if n_chart_label < 2:
            raise ValueError(
                "CHART slide F{} must have at least 2 Bar chart-labels, got "
                "{}".format(slide_no, n_chart_label)
            )
        if n_source < 1:
            raise ValueError(
                "CHART slide F{} must declare at least one Source, got "
                "{}".format(slide_no, n_source)
            )


# --- v2 layout + render (contract s1.4) ----------------------------------------


def _fmt_element_block_height(el):
    """Visual block height of a v2 element (chip adds vertical padding)."""
    _, _, height, _, _ = _measure_element(el)
    if el.get("is_chip"):
        return height + 2 * _V2_CHIP_PAD_Y
    return height


def _layout_format_slide(slide):
    """Assign bboxes + draw metadata to every format-slide element.

    Returns render-ops in file order. Content elements (all except wordmark) are
    stacked and vertically centered in [_V2_BAND_TOP, _V2_BAND_BOTTOM]; wordmark
    is bottom-right. Chip elements carry a ``chip_box`` decorative rectangle
    ([x, y, w, h]) and their text bbox is inset by the chip padding. Overflow
    beyond the band raises ValueError (fail-loud, no silent clipping)."""
    stack = [e for e in slide["elements"] if e["role"] != "wordmark"]
    wordmark = [e for e in slide["elements"] if e["role"] == "wordmark"]

    measured = [(e, _measure_element(e)) for e in stack]
    block_h = [_fmt_element_block_height(e) for e in stack]

    stack_h = 0
    for idx, e in enumerate(stack):
        stack_h += block_h[idx]
        if idx < len(stack) - 1:
            nxt = stack[idx + 1]
            if e.get("is_chip") and nxt.get("is_chip"):
                stack_h += _V2_CHIP_GAP
            else:
                stack_h += round(_V2_GAP_FACTOR * e["font_px"])

    if stack_h > _V2_BAND_H:
        raise ValueError(
            "format-slide F{} content ({}px) taller than safe band ({}px)".format(
                slide["n"], stack_h, _V2_BAND_H
            )
        )

    op_by_id = {}
    y = _V2_BAND_TOP + (_V2_BAND_H - stack_h) // 2
    for idx, (el, mm) in enumerate(measured):
        lines, width, height, line_advance, em_height = mm
        font = _font(el["weight"], el["font_px"])
        if el.get("is_chip"):
            chip_box = [MARGIN_X, y, CONTENT_W, height + 2 * _V2_CHIP_PAD_Y]
            text_bbox = [MARGIN_X + _V2_CHIP_PAD_X, y + _V2_CHIP_PAD_Y, width, height]
            op_by_id[id(el)] = {"el": el, "lines": lines, "bbox": text_bbox,
                                "line_advance": line_advance, "font": font,
                                "chip_box": chip_box}
        else:
            bbox = [MARGIN_X, y, width, height]
            op_by_id[id(el)] = {"el": el, "lines": lines, "bbox": bbox,
                                "line_advance": line_advance, "font": font,
                                "chip_box": None}
        y += block_h[idx]
        if idx < len(stack) - 1:
            nxt = stack[idx + 1]
            if el.get("is_chip") and nxt.get("is_chip"):
                y += _V2_CHIP_GAP
            else:
                y += round(_V2_GAP_FACTOR * el["font_px"])

    for el in wordmark:
        lines, width, height, line_advance, em_height = _measure_element(el)
        x = _V2_WORDMARK_RIGHT - width
        bbox = [x, _V2_WORDMARK_TOP, width, height]
        font = _font(el["weight"], el["font_px"])
        op_by_id[id(el)] = {"el": el, "lines": lines, "bbox": bbox,
                            "line_advance": line_advance, "font": font,
                            "chip_box": None}

    return [op_by_id[id(el)] for el in slide["elements"]]


def _op(el, mm, bbox, chip_box=None, bar_box=None):
    """Build one render-op dict with the standard keys (batch-B layouts)."""
    lines, width, height, line_advance, em_height = mm
    return {"el": el, "lines": lines, "bbox": bbox,
            "line_advance": line_advance, "font": _font(el["weight"], el["font_px"]),
            "chip_box": chip_box, "bar_box": bar_box}


def _layout_chart_format(slide):
    """CHART layout (contract s1.4): headline? + dominant peak + >=2 direct-labeled
    zero-based bars + source-stamp, vertically centered in the band; wordmark
    bottom-right. Each ``Bar`` chart-label text is drawn on ``--bg`` ABOVE its
    bar; the bar is a decorative ``--chart-up`` rectangle (NOT a manifest element),
    zero-based, length proportional to the authored value. Returns ``(ops, [])``.
    """
    els = slide["elements"]
    stack = [e for e in els if e["role"] != "wordmark"]
    wordmark = [e for e in els if e["role"] == "wordmark"]

    bar_values = [e["bar_value"] for e in els if e["role"] == "chart-label"]
    max_value = max(bar_values) if bar_values else 0.0

    measured = {id(e): _measure_element(e) for e in stack}

    def block_h(e):
        _, _, height, _, _ = measured[id(e)]
        if e["role"] == "chart-label":
            return height + _V2_BAR_LABEL_GAP + _V2_BAR_H
        return height

    def gap_after(e_i, e_next):
        if e_i["role"] == "chart-label" and e_next["role"] == "chart-label":
            return _V2_BAR_ITEM_GAP
        return round(_V2_GAP_FACTOR * e_i["font_px"])

    stack_h = 0
    for idx, e in enumerate(stack):
        stack_h += block_h(e)
        if idx < len(stack) - 1:
            stack_h += gap_after(e, stack[idx + 1])
    if stack_h > _V2_BAND_H:
        raise ValueError(
            "CHART format-slide F{} content ({}px) taller than safe band "
            "({}px)".format(slide["n"], stack_h, _V2_BAND_H))

    op_by_id = {}
    y = _V2_BAND_TOP + (_V2_BAND_H - stack_h) // 2
    for idx, e in enumerate(stack):
        mm = measured[id(e)]
        _, width, height, _, _ = mm
        if e["role"] == "chart-label":
            text_bbox = [MARGIN_X, y, width, height]
            if max_value > 0:
                bar_len = round(e["bar_value"] / max_value * _V2_BAR_TRACK_W)
            else:
                bar_len = 0
            bar_y = y + height + _V2_BAR_LABEL_GAP
            bar_box = [MARGIN_X, bar_y, bar_len, _V2_BAR_H]
            op_by_id[id(e)] = _op(e, mm, text_bbox, bar_box=bar_box)
        else:
            op_by_id[id(e)] = _op(e, mm, [MARGIN_X, y, width, height])
        y += block_h(e)
        if idx < len(stack) - 1:
            y += gap_after(e, stack[idx + 1])

    for el in wordmark:
        mm = _measure_element(el)
        _, width, _, _, _ = mm
        op_by_id[id(el)] = _op(el, mm, [_V2_WORDMARK_RIGHT - width,
                                        _V2_WORDMARK_TOP, width, mm[2]])

    return [op_by_id[id(el)] for el in els], []


def _layout_vs_contrast(slide):
    """VS-CONTRAST layout (contract s1.4): asymmetric side-by-side split. Side-A
    (left, wider column) = first ``Body`` label + the ``dominant`` number (132px
    accent, bottom-aligned baseline); side-B (right) = second ``Body`` label + the
    ``headline`` number (52px ink). A 1px ``--border`` vertical divider marks the
    split (decorative extra, NOT a manifest element). Any body label beyond the
    first two stacks centered below. Column overflow -> fail-loud. Returns
    ``(ops, extras)``."""
    els = slide["elements"]
    dominant = next(e for e in els if e["role"] == "dominant")
    headline = next(e for e in els if e["role"] == "headline")
    bodies = [e for e in els if e["role"] == "body"]
    wordmark = [e for e in els if e["role"] == "wordmark"]
    label_a, label_b = bodies[0], bodies[1]
    extra_bodies = bodies[2:]

    mm = {id(e): _measure_element(e) for e in
          (dominant, headline, *bodies)}

    def w(e):
        return mm[id(e)][1]

    def h(e):
        return mm[id(e)][2]

    left_lo, left_hi = _V2_VS_LEFT_HALF
    right_lo, right_hi = _V2_VS_RIGHT_HALF
    left_span = left_hi - left_lo
    right_span = right_hi - right_lo

    def centered_x(e, lo, span, side):
        width = w(e)
        if width > span:
            raise ValueError(
                "VS-CONTRAST slide F{} {} element {!r} ({}px) wider than its "
                "{}px column".format(slide["n"], e["role"], e["text"],
                                     width, span))
        return lo + (span - width) // 2

    label_h = max(h(label_a), h(label_b))
    number_row_h = max(h(dominant), h(headline))  # dominant (132) dominates
    comp_h = label_h + _V2_VS_LABEL_GAP + number_row_h

    # Extra body labels (beyond the canonical two) stack centered below.
    extra_measured = [(e, _measure_element(e)) for e in extra_bodies]
    extra_block = 0
    for e, m in extra_measured:
        extra_block += _V2_VS_LABEL_GAP + m[2]
    total_h = comp_h + extra_block
    if total_h > _V2_BAND_H:
        raise ValueError(
            "VS-CONTRAST format-slide F{} content ({}px) taller than safe band "
            "({}px)".format(slide["n"], total_h, _V2_BAND_H))

    op_by_id = {}
    y_top = _V2_BAND_TOP + (_V2_BAND_H - total_h) // 2
    y_label = y_top
    y_number = y_top + label_h + _V2_VS_LABEL_GAP
    number_bottom = y_number + number_row_h

    # side-A (left): label + dominant number (bottom-aligned to the baseline).
    op_by_id[id(label_a)] = _op(
        label_a, mm[id(label_a)],
        [centered_x(label_a, left_lo, left_span, "left"), y_label,
         w(label_a), h(label_a)])
    dom_top = number_bottom - h(dominant)
    op_by_id[id(dominant)] = _op(
        dominant, mm[id(dominant)],
        [centered_x(dominant, left_lo, left_span, "left"), dom_top,
         w(dominant), h(dominant)])

    # side-B (right): label + headline number (bottom-aligned to same baseline).
    op_by_id[id(label_b)] = _op(
        label_b, mm[id(label_b)],
        [centered_x(label_b, right_lo, right_span, "right"), y_label,
         w(label_b), h(label_b)])
    hn_top = number_bottom - h(headline)
    op_by_id[id(headline)] = _op(
        headline, mm[id(headline)],
        [centered_x(headline, right_lo, right_span, "right"), hn_top,
         w(headline), h(headline)])

    # Extra labels stacked centered full-width below the split.
    y_extra = number_bottom
    for e, m in extra_measured:
        y_extra += _V2_VS_LABEL_GAP
        ew = m[1]
        ex = MARGIN_X + (CONTENT_W - ew) // 2 if ew <= CONTENT_W else MARGIN_X
        op_by_id[id(e)] = _op(e, m, [ex, y_extra, ew, m[2]])
        y_extra += m[2]

    for el in wordmark:
        m = _measure_element(el)
        op_by_id[id(el)] = _op(el, m, [_V2_WORDMARK_RIGHT - m[1],
                                       _V2_WORDMARK_TOP, m[1], m[2]])

    extras = [{"kind": "divider",
               "xy": [_V2_VS_DIVIDER_X, y_label, _V2_VS_DIVIDER_X, number_bottom]}]
    return [op_by_id[id(el)] for el in els], extras


def render_format_slide(slide):
    """Render one format-slide to a PIL Image + build its schema-v2 surface dict.

    Runs the anti-tofu guard on every element every render (R18). Chip boxes,
    CHART bars, and the VS-CONTRAST divider are decorative primitives drawn BEFORE
    the text; they are NOT manifest elements (contract s1.4). Layout dispatches by
    format: CHART and VS-CONTRAST use dedicated layouts; every other format (incl.
    the frozen batch-A + TIMELINE/LEADERBOARD) uses the generic stack unchanged."""
    fmt = slide["format"]
    if fmt == "CHART":
        ops, extras = _layout_chart_format(slide)
    elif fmt == "VS-CONTRAST":
        ops, extras = _layout_vs_contrast(slide)
    else:
        ops, extras = _layout_format_slide(slide), []
    bg_hex = measure.TOKENS[BG_TOKEN]
    surface_hex = measure.TOKENS["surface"]
    border_hex = measure.TOKENS["border"]
    chart_up_hex = measure.TOKENS["chart-up"]
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), bg_hex)
    draw = ImageDraw.Draw(img)

    for op in ops:
        if op.get("chip_box") is not None:
            cx, cy, cw, ch = op["chip_box"]
            draw.rounded_rectangle(
                [cx, cy, cx + cw, cy + ch], radius=_V2_CHIP_RADIUS,
                fill=surface_hex, outline=border_hex, width=1,
            )
        if op.get("bar_box") is not None:
            bx, by, bw, bh = op["bar_box"]
            draw.rectangle([bx, by, bx + bw, by + bh], fill=chart_up_hex)

    for ex in extras:
        if ex["kind"] == "divider":
            x0, y0, x1, y1 = ex["xy"]
            draw.line([x0, y0, x1, y1], fill=border_hex, width=1)

    for op in ops:
        el = op["el"]
        _assert_glyphs(el["text"], op["font"], el["weight"], el["font_px"],
                       "F{}".format(slide["n"]), el["role"])
        x, y = op["bbox"][0], op["bbox"][1]
        for i, ln in enumerate(op["lines"]):
            draw.text((x, y + i * op["line_advance"]), ln, font=op["font"],
                      fill=el["color"], anchor="la")

    elements = []
    for op in ops:
        el = op["el"]
        el_bg = surface_hex if el.get("is_chip") else bg_hex
        elements.append({
            "text": el["text"],
            "role": el["role"],
            "font_px": el["font_px"],
            "weight": el["weight"],
            "color": el["color"],
            "bg": el_bg,
            "bbox": list(op["bbox"]),
        })

    surface = {
        "id": "format-{:02d}".format(slide["n"]),
        "role": "format-slide",
        "format": slide["format"],
        "png": "format-{:02d}.png".format(slide["n"]),
        "canvas": {"w": CANVAS_W, "h": CANVAS_H},
        "has_axis": False,
        "elements": elements,
    }
    return img, surface


def render_asset(asset_folder):
    """Render the asset's carousel slides, chart card, and/or format-slides +
    build the manifest. Returns ``(images, manifest)`` (png-name -> PIL Image).

    A folder is renderable if it has ``carousel.md``, a ``chart-spec.md`` with the
    ``Surface: chart-card`` marker, and/or a ``formats.md`` (v2). Carousel
    surfaces come first, then the chart card, then format-slides. ``schema_version``
    is ``"2"`` iff >=1 format-slide surface is emitted, else ``"1"`` (contract
    s1.6) — so hyd/tgrera, which carry no formats.md, stay byte-identical. Builds
    everything in memory; writes nothing (atomicity, R19)."""
    folder = Path(asset_folder)
    if not folder.is_dir():
        raise FileNotFoundError("asset folder not found: {}".format(asset_folder))

    md_path = folder / "carousel.md"
    chart_path = folder / "chart-spec.md"
    formats_path = folder / "formats.md"
    has_carousel = md_path.exists()
    has_formats = formats_path.exists()

    chart_spec = None
    if chart_path.exists():
        chart_spec = parse_chart_spec(chart_path.read_text(encoding="utf-8"))

    if not has_carousel and chart_spec is None and not has_formats:
        raise FileNotFoundError(
            "no renderable input (need carousel.md, a chart-spec.md with "
            "'Surface: chart-card', or a formats.md) in {}".format(asset_folder)
        )

    slug = folder.name
    images = {}
    surfaces = []

    if has_carousel:
        slides = parse_carousel(md_path.read_text(encoding="utf-8"))
        for slide in slides:
            img, surface = render_slide(slide)
            images[surface["png"]] = img
            surfaces.append(surface)

    if chart_spec is not None:
        img, surface = render_chart_card(chart_spec)
        images[surface["png"]] = img
        surfaces.append(surface)

    if has_formats:
        fmt_slides = parse_formats(formats_path.read_text(encoding="utf-8"))
        for slide in fmt_slides:
            img, surface = render_format_slide(slide)
            images[surface["png"]] = img
            surfaces.append(surface)

    has_format_slide = any(s["role"] == "format-slide" for s in surfaces)
    schema_version = "2" if has_format_slide else "1"
    manifest = {
        "schema_version": schema_version,
        "slug": slug,
        "surfaces": surfaces,
    }
    # R15/R16: a carousel PDF is emitted iff >=1 format-slide surface exists
    # (exactly the schema_version "2" condition). v1 assets (hyd carousel-slide,
    # tgrera chart-card, all 12 fixtures) carry no format-slide -> no pdf key,
    # no carousel.pdf (Risk 1 freeze). sort_keys=True places "pdf" ahead of
    # "schema_version" deterministically.
    if has_format_slide:
        manifest["pdf"] = _PDF_NAME
    return images, manifest


def _format_slide_pdf_pages(images, manifest):
    """Ordered list of the format-slide RGB page images for the carousel PDF.

    Pages are exactly the ``format-slide`` surfaces, one per surface, in manifest
    surface-list order (== slide order, R19). chart-card / carousel-slide surfaces
    never enter the PDF (contract s1.1, mixed-asset rule). Each page is the
    identical in-memory raster of its ``format-NN.png`` (same rendered pixels)."""
    return [images[s["png"]] for s in manifest["surfaces"]
            if s["role"] == "format-slide"]


def write_carousel_pdf(render_dir, images, manifest):
    """Write ``render/carousel.pdf`` from the ordered format-slide rasters.

    Byte-deterministic (R16): per-run CreationDate/ModDate suppressed, fixed
    Producer + Title (path-independent), no run-varying /ID. Returns the written
    path. Precondition: ``manifest`` carries a ``pdf`` key (>=1 format-slide)."""
    pages = _format_slide_pdf_pages(images, manifest)
    pdf_path = Path(render_dir) / manifest["pdf"]
    first, rest = pages[0], pages[1:]
    first.save(
        str(pdf_path),
        format="PDF",
        save_all=True,
        append_images=rest,
        producer=_PDF_PRODUCER,
        title=_PDF_TITLE,
        creationDate=None,
        modDate=None,
    )
    return pdf_path


def write_outputs(asset_folder, images, manifest):
    """Write PNGs + manifest.json (+ carousel.pdf when a v2 asset) into
    ``<asset-folder>/render/`` only.

    Called only after render_asset succeeds (atomic; no partial writes). Returns
    ``(written_pngs, manifest_path, pdf_path_or_None)``."""
    render_dir = Path(asset_folder) / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    written = []
    # File order comes from manifest surfaces (list), not any set -> deterministic.
    for surface in manifest["surfaces"]:
        name = surface["png"]
        out = render_dir / name
        images[name].save(str(out), "PNG")
        written.append(out)
    manifest_path = render_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    pdf_path = None
    if "pdf" in manifest:
        pdf_path = write_carousel_pdf(render_dir, images, manifest)
    return written, manifest_path, pdf_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Render a content asset (carousel.md 1080x1350 slides and/or "
                    "a chart-spec.md 1080x1920 chart card) to PNGs + manifest.json"
    )
    parser.add_argument("asset_folder", help="path to content/<slug>/")
    args = parser.parse_args(argv)

    try:
        images, manifest = render_asset(args.asset_folder)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        sys.stderr.write("error: {}\n".format(exc))
        return 1

    written, manifest_path, pdf_path = write_outputs(
        args.asset_folder, images, manifest)
    for out in written:
        print("wrote {}".format(out))
    if pdf_path is not None:
        print("wrote {}".format(pdf_path))
    print("wrote {}".format(manifest_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
