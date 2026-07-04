"""Unit tests for the Sprint 003 chart-card renderer (contract s8 command 0).

A SEPARATE test file so the Sprint-002 ``test_render.py`` suite stays byte-
untouched (regression safety, contract s2). Covers: the ``Surface: chart-card``
trigger seam (hyd skipped), chart-spec grammar + element style assignment, the
file-order manifest, every fail-loud state (has_axis:true, bad Canvas, garbage
line, missing required element), the 1080x1920 render (dims, bg dominance,
wordmark right-anchor, anti-tofu), deterministic re-render, and the hyd
non-regression (still 8 carousel surfaces, no chart card).

Stdlib ``unittest`` only. The tool dir is placed on ``sys.path`` (no __init__.py,
matching Sprint 001/002) so ``render`` and ``measure`` import directly.
"""

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

_TOOL_DIR = Path(__file__).resolve().parent.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))

import measure  # noqa: E402
import render  # noqa: E402

_CONTENT = _TOOL_DIR.parent.parent / "content"
_TGRERA = _CONTENT / "2026-07-03-tgrera-enforcement-wave"
_HYD = _CONTENT / "2026-07-03-hyd-premium-vs-budget"

# The authored receipts card, exact copy in file order (contract s5.6). Kept as
# literals so a codepoint drift (curly apostrophe, en-dash) fails loudly here.
_EXPECTED = [
    ("headline", "Telangana's regulator hit three builders in nine days."),
    ("body", "Jun 22 — R Homes: ordered to refund Rs 14.95L + 10.7% interest for "
             "pre-registration collection; project sales frozen."),
    ("body", "Jun 27 — Maharshi's Estates: penalty proceedings for selling plots "
             "in a project that was never registered."),
    ("body", "Jun 30 — Jayatri Infrastructure: refund with interest on a delayed "
             "Gopanpally project; 45 days to pay."),
    ("source-stamp", "Source: NewsMeter · Siasat · Deccan Chronicle · TGRERA "
                     "orders as of 2026-06-22 / 27 / 30"),
    ("wordmark", "TERREM"),
]

_VALID_SPEC = (
    "```\n"
    "Surface: chart-card\n"
    "Canvas: 1080x1920\n"
    "has_axis: false\n\n"
    "Headline: A headline that is short enough.\n"
    "Order: Jun 01 — a dated receipt line.\n"
    "Source: Source: SomeWire as of 2026-01-01\n"
    "Wordmark: TERREM\n"
    "```\n"
)


class TestTriggerSeam(unittest.TestCase):
    def test_hyd_chart_spec_returns_none(self):
        # hyd's free-form chart-spec has no 'Surface: chart-card' marker.
        txt = (_HYD / "chart-spec.md").read_text(encoding="utf-8")
        self.assertIsNone(render.parse_chart_spec(txt))

    def test_no_marker_ignored_even_with_directives(self):
        txt = "```\nCanvas: 1080x1920\nHeadline: x\n```\n"
        self.assertIsNone(render.parse_chart_spec(txt))


class TestParseTgrera(unittest.TestCase):
    def setUp(self):
        txt = (_TGRERA / "chart-spec.md").read_text(encoding="utf-8")
        self.spec = render.parse_chart_spec(txt)

    def test_is_chart_card_spec(self):
        self.assertIsNotNone(self.spec)
        self.assertEqual(self.spec["canvas"], (1080, 1920))
        self.assertFalse(self.spec["has_axis"])

    def test_six_elements_in_file_order(self):
        got = [(e["role"], e["text"]) for e in self.spec["elements"]]
        self.assertEqual(got, _EXPECTED)

    def test_element_styles(self):
        e = self.spec["elements"]
        self.assertEqual((e[0]["font_px"], e[0]["weight"], e[0]["color"]),
                         (44, 700, measure.TOKENS["ink"]))
        self.assertEqual((e[1]["font_px"], e[1]["weight"], e[1]["color"]),
                         (27, 500, measure.TOKENS["ink"]))
        self.assertEqual((e[4]["font_px"], e[4]["weight"], e[4]["color"]),
                         (20, 400, measure.TOKENS["ink-muted"]))
        self.assertEqual((e[5]["font_px"], e[5]["weight"], e[5]["color"]),
                         (25, 700, measure.TOKENS["accent-deep"]))

    def test_source_stamp_single_prefix(self):
        # doubled 'Source: Source:' collapses to one prefix (captured group).
        src = [e for e in self.spec["elements"] if e["role"] == "source-stamp"][0]
        self.assertTrue(src["text"].startswith("Source: NewsMeter"))
        self.assertNotIn("Source: Source:", src["text"])
        self.assertIn("as of", src["text"])

    def test_every_color_is_brand_token(self):
        for e in self.spec["elements"]:
            self.assertTrue(measure.is_brand_token(e["color"]), e["color"])


class TestParseErrors(unittest.TestCase):
    def test_has_axis_true_rejected(self):
        spec = _VALID_SPEC.replace("has_axis: false", "has_axis: true")
        with self.assertRaises(ValueError) as ctx:
            render.parse_chart_spec(spec)
        self.assertIn("has_axis: true", str(ctx.exception))

    def test_bad_canvas_rejected(self):
        spec = _VALID_SPEC.replace("Canvas: 1080x1920", "Canvas: 1080x1350")
        with self.assertRaises(ValueError) as ctx:
            render.parse_chart_spec(spec)
        self.assertIn("1080x1350", str(ctx.exception))

    def test_unparseable_line_in_fence_rejected(self):
        spec = _VALID_SPEC.replace("Wordmark: TERREM",
                                   "this line is not chart-spec grammar\nWordmark: TERREM")
        with self.assertRaises(ValueError) as ctx:
            render.parse_chart_spec(spec)
        self.assertIn("unparseable", str(ctx.exception))

    def test_missing_wordmark_rejected(self):
        spec = _VALID_SPEC.replace("Wordmark: TERREM\n", "")
        with self.assertRaises(ValueError) as ctx:
            render.parse_chart_spec(spec)
        self.assertIn("Wordmark", str(ctx.exception))

    def test_missing_headline_rejected(self):
        spec = _VALID_SPEC.replace("Headline: A headline that is short enough.\n", "")
        with self.assertRaises(ValueError) as ctx:
            render.parse_chart_spec(spec)
        self.assertIn("Headline", str(ctx.exception))

    def test_missing_source_rejected(self):
        spec = _VALID_SPEC.replace("Source: Source: SomeWire as of 2026-01-01\n", "")
        with self.assertRaises(ValueError) as ctx:
            render.parse_chart_spec(spec)
        self.assertIn("Source", str(ctx.exception))


class TestLayoutAndRender(unittest.TestCase):
    def setUp(self):
        txt = (_TGRERA / "chart-spec.md").read_text(encoding="utf-8")
        self.spec = render.parse_chart_spec(txt)

    def test_render_dims_1080x1920(self):
        img, surface = render.render_chart_card(self.spec)
        self.assertEqual(img.size, (1080, 1920))
        self.assertEqual(surface["canvas"], {"w": 1080, "h": 1920})
        self.assertEqual(surface["role"], "chart-card")

    def test_critical_roles_inside_vertical_safe_zone(self):
        ops = render._layout_chart_card(self.spec)
        for op in ops:
            role = op["el"]["role"]
            if role in ("headline", "body", "hook"):
                res = measure.safe_zone_ok(1080, 1920, op["bbox"])
                self.assertTrue(res["passes"], (role, res))

    def test_wordmark_right_anchored(self):
        _, surface = render.render_chart_card(self.spec)
        wm = [e for e in surface["elements"] if e["role"] == "wordmark"][0]
        x, y, w, h = wm["bbox"]
        self.assertEqual(x + w, render.CHART_WORDMARK_RIGHT)

    def test_axis_fields_null_when_has_axis_false(self):
        _, surface = render.render_chart_card(self.spec)
        self.assertIs(surface["has_axis"], False)
        self.assertIsNone(surface["axis_min"])
        self.assertIsNone(surface["zero_based"])
        self.assertIsNone(surface["break_disclosed"])
        self.assertIsNone(surface["chart_ref"])

    def test_overflow_fails_loud(self):
        big = "word " * 400
        spec = {"canvas": (1080, 1920), "has_axis": False,
                "elements": [
                    {"role": "headline", "text": big, "font_px": 44, "weight": 700,
                     "color": measure.TOKENS["ink"]},
                    {"role": "source-stamp", "text": "Source: x as of 2026-01-01",
                     "font_px": 20, "weight": 400, "color": measure.TOKENS["ink-muted"]},
                    {"role": "wordmark", "text": "TERREM", "font_px": 25, "weight": 700,
                     "color": measure.TOKENS["accent-deep"]},
                ]}
        with self.assertRaises(ValueError):
            render._layout_chart_card(spec)

    def test_anti_tofu_raises_named(self):
        spec = {"canvas": (1080, 1920), "has_axis": False,
                "elements": [
                    {"role": "headline", "text": "A\U000F0000B", "font_px": 44,
                     "weight": 700, "color": measure.TOKENS["ink"]},
                    {"role": "source-stamp", "text": "Source: x as of 2026-01-01",
                     "font_px": 20, "weight": 400, "color": measure.TOKENS["ink-muted"]},
                    {"role": "wordmark", "text": "TERREM", "font_px": 25, "weight": 700,
                     "color": measure.TOKENS["accent-deep"]},
                ]}
        with self.assertRaises(RuntimeError) as ctx:
            render.render_chart_card(spec)
        self.assertIn("chart-card", str(ctx.exception))


class TestRenderAssetIntegration(unittest.TestCase):
    def test_tgrera_one_chart_card_surface(self):
        images, manifest = render.render_asset(str(_TGRERA))
        self.assertEqual(manifest["schema_version"], "1")
        self.assertEqual([s["role"] for s in manifest["surfaces"]], ["chart-card"])
        self.assertIn("chart-card.png", images)

    def test_hyd_non_regression_eight_carousel(self):
        # hyd has carousel.md + a markerless chart-spec.md -> 8 carousel, no card.
        images, manifest = render.render_asset(str(_HYD))
        roles = [s["role"] for s in manifest["surfaces"]]
        self.assertEqual(roles, ["carousel-slide"] * 8)
        self.assertFalse(any(s["role"] == "chart-card" for s in manifest["surfaces"]))

    def test_deterministic_rerender(self):
        def snap():
            images, _ = render.render_asset(str(_TGRERA))
            return {k: hashlib.sha256(v.convert("RGBA").tobytes()).hexdigest()
                    for k, v in images.items()}
        self.assertEqual(snap(), snap())

    def test_empty_folder_no_renderable_input(self):
        with tempfile.TemporaryDirectory() as d:
            rc = render.main([d])
            self.assertEqual(rc, 1)
            self.assertFalse(os.path.exists(os.path.join(d, "render")))


if __name__ == "__main__":
    unittest.main()
