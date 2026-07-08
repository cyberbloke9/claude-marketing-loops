#!/usr/bin/env python3
"""Deterministic v2 (format-slide) adversarial fixture generator (Sprint 005).

Mirrors make_fixtures.py discipline: each fixture is a content/-shaped folder
with a hand-crafted schema-v2 manifest + real vendored-Inter PNG(s) + a meta.md
carrying VALID provenance AND VALID cover-pattern/one_dataset blocks — except the
one fixture that intentionally breaks exactly one of them. Every fixture trips
EXACTLY ONE V13-V19 check (one-fixture-one-check); fx-v2-good is a clean PASS.

Element sizes are pinned from the empirical V15 probe (generator_trace.log):
headline 56 -> 360px band 19 (>=13); dominant 100 -> band 24 (>=21); the
illegible fixture renders its headline at REAL 34px (declared 48) -> full band 33
(V5-crosscheck eff ~39.8, inside [36,60]) but 360px band 10 (<13 -> V15 fails).

Run:  python3 tools/marketing-render/fixtures/make_v2_fixtures.py
Writes only under tools/marketing-render/fixtures/fx-v2-*/. No network.
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
import render   # noqa: E402  (vendored-Inter font loader only)

TOK = measure.TOKENS

PROVENANCE = (
    "<!-- provenance:start -->\n"
    "sources: NewsMeter · Siasat · Deccan Chronicle\n"
    "terrem_db_numbers: none — public regulator orders only\n"
    "as_of: 2026-06-30\n"
    "<!-- provenance:end -->\n"
)
COVER_VALID = (
    "<!-- cover-pattern:start -->\n"
    "pattern: BIG-NUMBER\n"
    "one_dataset: TGRERA enforcement orders, Jun 2026\n"
    "<!-- cover-pattern:end -->\n"
)
COVER_BAD_PATTERN = (          # invalid pattern value, one_dataset PRESENT (V17 only)
    "<!-- cover-pattern:start -->\n"
    "pattern: TIMELINE\n"
    "one_dataset: TGRERA enforcement orders, Jun 2026\n"
    "<!-- cover-pattern:end -->\n"
)
COVER_NO_DATASET = (           # valid pattern (V17 ok), NO one_dataset line (V19 only)
    "<!-- cover-pattern:start -->\n"
    "pattern: BIG-NUMBER\n"
    "<!-- cover-pattern:end -->\n"
)

# Copy is short + single-line so each ink band is one clean line; texts avoid
# blacklist phrases (public regulator wording only).
HEADLINE_TXT = "Three builders, nine days"
DOMINANT_TXT = "14.95L"
BODY_TXT = "R Homes ordered to refund"
SOWHAT_TXT = "Check the RERA number before you pay - intel.terrem.in"


def element(text, role, fpx, weight, color, bg, bbox):
    return {"text": text, "role": role, "font_px": fpx, "weight": weight,
            "color": color, "bg": bg, "bbox": list(bbox)}


def _draw(draw, x, y, text, fpx_real, weight, color):
    """Render one line of real vendored-Inter glyphs; return tight bbox [x,y,w,h]."""
    font = render._font(weight, fpx_real)
    draw.text((x, y), text, font=font, fill=color, anchor="la")
    l, t, r, b = draw.textbbox((x, y), text, font=font, anchor="la")
    return [l, t, r - l, b - t]


def content_slide(sid="format-01", png_name="format-01.png", fmt="BIG-NUMBER",
                  headline_declared=56, headline_real=None,
                  dominant_fpx=100, body_fpx=30,
                  include_headline=True, include_dominant=True,
                  include_body=True, include_sowhat=True, include_wordmark=True):
    """Build (surface, {png:img}) for one valid-by-default v2 content slide."""
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), TOK["bg"])
    d = ImageDraw.Draw(img)
    els = []
    if include_headline:
        hr = headline_real if headline_real is not None else headline_declared
        bb = _draw(d, 90, 180, HEADLINE_TXT, hr, 700, TOK["ink"])
        els.append(element(HEADLINE_TXT, "headline", headline_declared, 700,
                           TOK["ink"], TOK["bg"], bb))
    if include_dominant:
        bb = _draw(d, 90, 360, DOMINANT_TXT, dominant_fpx, 700, TOK["accent"])
        els.append(element(DOMINANT_TXT, "dominant", dominant_fpx, 700,
                           TOK["accent"], TOK["bg"], bb))
    if include_body:
        bb = _draw(d, 90, 620, BODY_TXT, body_fpx, 500, TOK["ink-muted"])
        els.append(element(BODY_TXT, "body", body_fpx, 500,
                           TOK["ink-muted"], TOK["bg"], bb))
    if include_sowhat:
        bb = _draw(d, 90, 900, SOWHAT_TXT, 30, 500, TOK["ink"])
        els.append(element(SOWHAT_TXT, "so-what", 30, 500,
                           TOK["ink"], TOK["bg"], bb))
    if include_wordmark:
        bb = _draw(d, 840, 1250, "TERREM", 26, 700, TOK["accent-deep"])
        els.append(element("TERREM", "wordmark", 26, 700,
                           TOK["accent-deep"], TOK["bg"], bb))
    surf = {"id": sid, "role": "format-slide", "format": fmt, "png": png_name,
            "canvas": {"w": W, "h": H}, "has_axis": False, "elements": els}
    return surf, {png_name: img}


def write_fixture(name, surfaces, images, cover_block=COVER_VALID):
    folder = _HERE / name
    if folder.exists():
        shutil.rmtree(folder)
    render_dir = folder / "render"
    render_dir.mkdir(parents=True)
    for png_name, img in images.items():
        img.save(render_dir / png_name)
    manifest = {"schema_version": "2", "slug": name, "surfaces": surfaces,
                "pdf": "carousel.pdf"}
    (render_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    meta = "# Meta — {}\n\n{}\n{}".format(name, PROVENANCE, cover_block)
    (folder / "meta.md").write_text(meta, encoding="utf-8")


def build_all():
    # Positive control — clean PASS (exit 0). headline 56, dominant 100, body 30
    # (ratio 100/30 = 3.33), so-what + wordmark; valid meta blocks.
    s, i = content_slide()
    write_fixture("fx-v2-good", [s], i)

    # V13 — dominant too small. dominant 100 clears V15 (band 24>=21) but body 40
    # forces ratio 100/40 = 2.5 < 3.
    s, i = content_slide(dominant_fpx=100, body_fpx=40)
    write_fixture("fx-v2-dominant-small", [s], i)

    # V14-type-floor — body at 24px (<26). dominant 100/body_ref 24 = 4.17 (V13 ok).
    s, i = content_slide(dominant_fpx=100, body_fpx=24)
    write_fixture("fx-v2-body-24", [s], i)

    # V14-wordmark — zero wordmark element.
    s, i = content_slide(include_wordmark=False)
    write_fixture("fx-v2-no-wordmark", [s], i)

    # V15 — thumbnail-illegible headline: declared 48 (V14 floor ok, V5-crosscheck
    # ok) but rendered at 34px so its 360px band (10) < 13. Dominant left honest
    # (band 24>=21) so V15 fires on exactly the headline.
    s, i = content_slide(headline_declared=48, headline_real=34)
    write_fixture("fx-v2-thumb-illegible", [s], i)

    # V16 — no so-what anywhere.
    s, i = content_slide(include_sowhat=False)
    write_fixture("fx-v2-no-so-what", [s], i)

    # V17 — cover-pattern present but invalid value (TIMELINE); one_dataset present
    # (isolates V17 from V19).
    s, i = content_slide()
    write_fixture("fx-v2-bad-cover", [s], i, cover_block=COVER_BAD_PATTERN)

    # V19 — cover-pattern valid (V17 ok) but no one_dataset line.
    s, i = content_slide()
    write_fixture("fx-v2-no-dataset", [s], i, cover_block=COVER_NO_DATASET)

    # V18 — 11 format-slide surfaces (>10). One rendered valid slide reused across
    # 11 distinct ids/pngs (identical bytes); each carries a so-what so V16 holds.
    base_surf, base_imgs = content_slide()
    base_img = list(base_imgs.values())[0]
    surfaces = []
    images = {}
    for n in range(1, 12):
        sid = "format-{:02d}".format(n)
        png_name = "{}.png".format(sid)
        surf = dict(base_surf)
        surf["id"] = sid
        surf["png"] = png_name
        surfaces.append(surf)
        images[png_name] = base_img
    write_fixture("fx-v2-11-slides", surfaces, images)

    print("wrote v2 fixtures under {}".format(_HERE))


if __name__ == "__main__":
    build_all()
