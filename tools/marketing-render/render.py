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


def render_asset(asset_folder):
    """Render the asset's carousel slides and/or chart card + build the manifest.
    Returns ``(images, manifest)`` where ``images`` maps png-name -> PIL Image.

    A folder is renderable if it has ``carousel.md`` and/or a ``chart-spec.md``
    carrying the ``Surface: chart-card`` marker. Carousel surfaces come first,
    then the chart card (contract s6). Builds everything in memory; writes
    nothing (atomicity, contract s4.6)."""
    folder = Path(asset_folder)
    if not folder.is_dir():
        raise FileNotFoundError("asset folder not found: {}".format(asset_folder))

    md_path = folder / "carousel.md"
    chart_path = folder / "chart-spec.md"
    has_carousel = md_path.exists()

    chart_spec = None
    if chart_path.exists():
        chart_spec = parse_chart_spec(chart_path.read_text(encoding="utf-8"))

    if not has_carousel and chart_spec is None:
        raise FileNotFoundError(
            "no renderable input (need carousel.md or a chart-spec.md with "
            "'Surface: chart-card') in {}".format(asset_folder)
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

    manifest = {
        "schema_version": "1",
        "slug": slug,
        "surfaces": surfaces,
    }
    return images, manifest


def write_outputs(asset_folder, images, manifest):
    """Write PNGs + manifest.json into ``<asset-folder>/render/`` only.

    Called only after render_asset succeeds (atomic; no partial writes)."""
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
    return written, manifest_path


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

    written, manifest_path = write_outputs(args.asset_folder, images, manifest)
    for out in written:
        print("wrote {}".format(out))
    print("wrote {}".format(manifest_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
