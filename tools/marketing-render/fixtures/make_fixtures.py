#!/usr/bin/env python3
"""Deterministic fixture generator for the Sprint 004 validator (contract s7).

Each fixture is a minimal ``content/``-shaped folder that trips **exactly one**
V-check, plus a positive-control ``fx-good-min`` that PASSes. Fixtures render
real vendored-Inter glyphs (same ``render._font`` + ``anchor="la"`` as the
renderer) so the V3 ink / V5 glyph-size calibration transfers verbatim. Only the
one intended defect is injected per fixture; everything else is a valid render.

Run:  python3 tools/marketing-render/fixtures/make_fixtures.py
Writes only under ``tools/marketing-render/fixtures/fx-*/``. No network.
"""

import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

_HERE = Path(__file__).resolve().parent
_RENDER_DIR = _HERE.parent
if str(_RENDER_DIR) not in sys.path:
    sys.path.insert(0, str(_RENDER_DIR))
import measure  # noqa: E402
import render   # noqa: E402  (reused for the vendored-Inter font loader only)

TOK = measure.TOKENS
PROVENANCE = (
    "<!-- provenance:start -->\n"
    "sources: NewsMeter · Siasat · Deccan Chronicle\n"
    "terrem_db_numbers: none — public regulator orders only\n"
    "as_of: 2026-06-30\n"
    "<!-- provenance:end -->\n"
)


def draw_wrapped(draw, x, y, text, font, fpx, max_width, fill):
    """Draw ``text`` wrapped to ``max_width`` at line advance 1.4*fpx (matches the
    renderer's line spacing so ink bands separate). Return the tight union bbox
    ``[x, y, w, h]`` of the drawn ink."""
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if not cur or draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    advance = round(1.4 * fpx)
    minx = miny = 10 ** 9
    maxx = maxy = -(10 ** 9)
    for i, ln in enumerate(lines):
        ly = y + i * advance
        draw.text((x, ly), ln, font=font, fill=fill, anchor="la")
        l, t, r, b = draw.textbbox((x, ly), ln, font=font, anchor="la")
        minx, miny = min(minx, l), min(miny, t)
        maxx, maxy = max(maxx, r), max(maxy, b)
    return [minx, miny, maxx - minx, maxy - miny]


def element(text, role, fpx, weight, color, bg, bbox):
    return {"text": text, "role": role, "font_px": fpx, "weight": weight,
            "color": color, "bg": bg, "bbox": list(bbox)}


def write_fixture(name, surfaces, images, meta_extra=PROVENANCE, copy_files=None):
    """Create fixtures/<name>/ with render/manifest.json + render/*.png + meta.md."""
    folder = _HERE / name
    if folder.exists():
        shutil.rmtree(folder)
    render_dir = folder / "render"
    render_dir.mkdir(parents=True)
    for png_name, img in images.items():
        img.save(render_dir / png_name)
    manifest = {"schema_version": "1", "slug": name, "surfaces": surfaces}
    (render_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    meta = "# Meta — {}\n\n{}".format(name, meta_extra)
    (folder / "meta.md").write_text(meta, encoding="utf-8")
    for fname, content in (copy_files or {}).items():
        (folder / fname).write_text(content, encoding="utf-8")


# --- Reusable builders ---------------------------------------------------------


def new_canvas(w, h, bg_hex=TOK["bg"]):
    img = Image.new("RGB", (w, h), bg_hex)
    return img, ImageDraw.Draw(img)


def valid_chart_card(has_axis=False, axis_min=None, break_disclosed=None,
                     include_source=True, headline_fpx=44):
    """Render a valid 1080x1920 chart card; return (surface_dict, {png:img})."""
    W, H = 1080, 1920
    img, draw = new_canvas(W, H)
    els = []

    fh = render._font(700, headline_fpx)
    hb = draw_wrapped(draw, 90, 320,
                      "Telangana's regulator hit three builders in nine days.",
                      fh, headline_fpx, 900, TOK["ink"])
    els.append(element("Telangana's regulator hit three builders in nine days.",
                       "headline", headline_fpx, 700, TOK["ink"], TOK["bg"], hb))

    fb = render._font(500, 27)
    bb = draw_wrapped(draw, 90, 720,
                      "Jun 22 — R Homes ordered to refund with interest; sales frozen.",
                      fb, 27, 900, TOK["ink"])
    els.append(element("Jun 22 — R Homes ordered to refund with interest; sales frozen.",
                       "body", 27, 500, TOK["ink"], TOK["bg"], bb))

    if include_source:
        fs = render._font(400, 20)
        stamp = "Source: NewsMeter · Siasat · Deccan Chronicle · orders as of 2026-06-30"
        sb = draw_wrapped(draw, 90, 1380, stamp, fs, 20, 900, TOK["ink-muted"])
        els.append(element(stamp, "source-stamp", 20, 400, TOK["ink-muted"], TOK["bg"], sb))

    fw = render._font(700, 25)
    wb = draw_wrapped(draw, 888, 1800, "TERREM", fw, 25, 200, TOK["accent-deep"])
    els.append(element("TERREM", "wordmark", 25, 700, TOK["accent-deep"], TOK["bg"], wb))

    surface = {"id": "chart-card", "role": "chart-card", "png": "chart-card.png",
               "canvas": {"w": W, "h": H}, "has_axis": has_axis, "axis_min": axis_min,
               "zero_based": None, "break_disclosed": break_disclosed, "elements": els}
    return surface, {"chart-card.png": img}


def carousel_slide(headline_fpx=54, headline_xy=(90, 200), hook_text=None,
                   hook_words=10):
    """Render a valid 1080x1350 carousel slide with a headline (and optional hook)."""
    W, H = 1080, 1350
    img, draw = new_canvas(W, H)
    els = []
    x, y = headline_xy
    fh = render._font(700, headline_fpx)
    text = "Three TGRERA orders in nine days reset builder risk."
    hb = draw_wrapped(draw, x, y, text, fh, headline_fpx, 900, TOK["ink"])
    els.append(element(text, "headline", headline_fpx, 700, TOK["ink"], TOK["bg"], hb))

    if hook_text is not None:
        fk = render._font(700, 48)
        kb = draw_wrapped(draw, 90, 700, hook_text, fk, 48, 900, TOK["ink"])
        els.append(element(hook_text, "hook", 48, 700, TOK["ink"], TOK["bg"], kb))

    surface = {"id": "carousel-01", "role": "carousel-slide", "png": "carousel-01.png",
               "canvas": {"w": W, "h": H}, "has_axis": False, "axis_min": None,
               "zero_based": None, "break_disclosed": None, "elements": els}
    return surface, {"carousel-01.png": img}


# --- Fixtures ------------------------------------------------------------------


def build_all():
    # Positive control: everything passes.
    surf, imgs = valid_chart_card()
    write_fixture("fx-good-min", [surf], imgs)

    # V3: correct manifest over an all-bg (blank) PNG.
    surf, imgs = valid_chart_card()
    blank = {"chart-card.png": Image.new("RGB", (1080, 1920), TOK["bg"])}
    write_fixture("fx-blank-png", [surf], blank)

    # V4: low-contrast token pair #57534e on #0d3d38 (honestly rendered on a panel).
    W, H = 1080, 1920
    img, draw = new_canvas(W, H)
    draw.rectangle([70, 700, 1010, 820], fill=TOK["accent-deep"])
    fb = render._font(500, 27)
    lc = draw_wrapped(draw, 90, 720, "Low contrast body copy on a dark panel.",
                      fb, 27, 900, TOK["ink-muted"])
    els = [element("Low contrast body copy on a dark panel.", "body", 27, 500,
                   TOK["ink-muted"], TOK["accent-deep"], lc)]
    fs = render._font(400, 20)
    stamp = "Source: NewsMeter · orders as of 2026-06-30"
    sb = draw_wrapped(draw, 90, 1380, stamp, fs, 20, 900, TOK["ink-muted"])
    els.append(element(stamp, "source-stamp", 20, 400, TOK["ink-muted"], TOK["bg"], sb))
    fw = render._font(700, 25)
    wb = draw_wrapped(draw, 888, 1800, "TERREM", fw, 25, 200, TOK["accent-deep"])
    els.append(element("TERREM", "wordmark", 25, 700, TOK["accent-deep"], TOK["bg"], wb))
    surf = {"id": "chart-card", "role": "chart-card", "png": "chart-card.png",
            "canvas": {"w": W, "h": H}, "has_axis": False, "axis_min": None,
            "zero_based": None, "break_disclosed": None, "elements": els}
    write_fixture("fx-low-contrast", [surf], {"chart-card.png": img})

    # V5 cross-check: render at real 22px but DECLARE font_px 44 (2x lie).
    W, H = 1080, 1920
    img, draw = new_canvas(W, H)
    f22 = render._font(700, 22)
    real = draw_wrapped(draw, 90, 320, "This headline is really rendered at 22px.",
                        f22, 22, 900, TOK["ink"])
    els = [element("This headline is really rendered at 22px.", "headline", 44, 700,
                   TOK["ink"], TOK["bg"], real)]  # declared 44 == 2x real
    fs = render._font(400, 20)
    stamp = "Source: NewsMeter · orders as of 2026-06-30"
    sb = draw_wrapped(draw, 90, 1380, stamp, fs, 20, 900, TOK["ink-muted"])
    els.append(element(stamp, "source-stamp", 20, 400, TOK["ink-muted"], TOK["bg"], sb))
    fw = render._font(700, 25)
    wb = draw_wrapped(draw, 888, 1800, "TERREM", fw, 25, 200, TOK["accent-deep"])
    els.append(element("TERREM", "wordmark", 25, 700, TOK["accent-deep"], TOK["bg"], wb))
    surf = {"id": "chart-card", "role": "chart-card", "png": "chart-card.png",
            "canvas": {"w": W, "h": H}, "has_axis": False, "axis_min": None,
            "zero_based": None, "break_disclosed": None, "elements": els}
    write_fixture("fx-size-lie", [surf], {"chart-card.png": img})

    # V5 floor: carousel headline rendered AND declared at 30px (< 48).
    surf, imgs = carousel_slide(headline_fpx=30)
    write_fixture("fx-small-headline", [surf], imgs)

    # V6: carousel headline rendered/declared out of the safe zone (top edge < 40).
    surf, imgs = carousel_slide(headline_fpx=54, headline_xy=(90, 10))
    write_fixture("fx-out-of-safezone", [surf], imgs)

    # V7: carousel slide-1 hook of 11 words.
    hook = "This hook has exactly eleven words to trip the counter now"
    surf, imgs = carousel_slide(hook_text=hook)
    write_fixture("fx-11-word-hook", [surf], imgs)

    # V8: chart-card surface with no source-stamp element.
    surf, imgs = valid_chart_card(include_source=False)
    write_fixture("fx-missing-source", [surf], imgs)

    # V9: copy containing a brand-kit §8 blacklist phrase.
    surf, imgs = valid_chart_card()
    phrase = "90% of recall in first 6 seconds"
    copy = "# Chart Spec\n\nHeadline: {}\n".format(phrase)
    write_fixture("fx-blacklist", [surf], imgs, copy_files={"chart-spec.md": copy})

    # V10: chart card with truncated undisclosed axis.
    surf, imgs = valid_chart_card(has_axis=True, axis_min=20, break_disclosed=False)
    write_fixture("fx-truncated-axis", [surf], imgs)

    # V11: asset with no provenance block in meta.md.
    surf, imgs = valid_chart_card()
    write_fixture("fx-no-provenance", [surf], imgs, meta_extra="No attestation here.\n")

    # V2: chart-card PNG rendered 1080x1080 while manifest declares chart-card fmt.
    W = 1080
    img, draw = new_canvas(W, W)
    fh = render._font(700, 44)
    hb = draw_wrapped(draw, 90, 320, "Wrong canvas height.", fh, 44, 900, TOK["ink"])
    els = [element("Wrong canvas height.", "headline", 44, 700, TOK["ink"], TOK["bg"], hb)]
    fs = render._font(400, 20)
    stamp = "Source: NewsMeter · orders as of 2026-06-30"
    sb = draw_wrapped(draw, 90, 900, stamp, fs, 20, 900, TOK["ink-muted"])
    els.append(element(stamp, "source-stamp", 20, 400, TOK["ink-muted"], TOK["bg"], sb))
    fw = render._font(700, 25)
    wb = draw_wrapped(draw, 888, 1000, "TERREM", fw, 25, 200, TOK["accent-deep"])
    els.append(element("TERREM", "wordmark", 25, 700, TOK["accent-deep"], TOK["bg"], wb))
    surf = {"id": "chart-card", "role": "chart-card", "png": "chart-card.png",
            "canvas": {"w": 1080, "h": 1920}, "has_axis": False, "axis_min": None,
            "zero_based": None, "break_disclosed": None, "elements": els}
    write_fixture("fx-canvas-mismatch", [surf], {"chart-card.png": img})

    print("wrote fixtures under {}".format(_HERE))


if __name__ == "__main__":
    build_all()
