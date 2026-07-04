"""Unit tests for the Sprint 002 carousel renderer (contract s8 command 0).

Covers: carousel.md parsing, per-element style assignment, deterministic layout
math, token validation, the anti-tofu glyph guard, font vendoring (existence +
SHA-256 pin), and every fail-loud error state (missing folder/carousel/font,
unparseable line, tofu, overflow) with the atomic no-partial-write guarantee.

Stdlib ``unittest`` only. The tool dir is placed on ``sys.path`` (no __init__.py,
matching Sprint 001) so ``render`` and ``measure`` import directly.
"""

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parent.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))

import measure  # noqa: E402
import render  # noqa: E402

_FONTS = _TOOL_DIR / "fonts"

# Reference SHA-256 (first 16 hex) pinned by the contract s2.1. Inter raster is
# version-sensitive; determinism depends on these exact bytes.
_FONT_SHA16 = {
    "Inter-Regular.ttf": "3127f0b873387ee3",
    "Inter-Medium.ttf": "a645f55492d1c8cd",
    "Inter-SemiBold.ttf": "b0b540e69bf67170",
    "Inter-Bold.ttf": "412c068eab6f36e6",
}


class TestFontVendoring(unittest.TestCase):
    def test_all_five_files_present(self):
        for name in list(_FONT_SHA16) + ["OFL.txt"]:
            self.assertTrue((_FONTS / name).exists(), "missing vendored file: " + name)

    def test_font_sha256_pinned(self):
        for name, want16 in _FONT_SHA16.items():
            data = (_FONTS / name).read_bytes()
            got16 = hashlib.sha256(data).hexdigest()[:16]
            self.assertEqual(got16, want16, "SHA-256 drift for " + name)

    def test_ofl_names_inter(self):
        text = (_FONTS / "OFL.txt").read_text(encoding="utf-8")
        self.assertIn("Inter Project Authors", text)
        self.assertIn("SIL OPEN FONT LICENSE", text)


class TestParse(unittest.TestCase):
    def setUp(self):
        md = _TOOL_DIR.parent.parent / "content" / "2026-07-03-hyd-premium-vs-budget" / "carousel.md"
        self.slides = render.parse_carousel(md.read_text(encoding="utf-8"))

    def test_eight_slides_ascending(self):
        self.assertEqual([s["n"] for s in self.slides], [1, 2, 3, 4, 5, 6, 7, 8])

    def test_slide1_has_exactly_one_hook(self):
        s1 = self.slides[0]
        hooks = [e for e in s1["elements"] if e["role"] == "hook"]
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0]["font_px"], 61)
        self.assertEqual(hooks[0]["weight"], 700)
        self.assertEqual(hooks[0]["color"], measure.TOKENS["ink"])

    def test_no_hook_on_other_slides(self):
        for s in self.slides[1:]:
            self.assertFalse(any(e["role"] == "hook" for e in s["elements"]), s["n"])

    def test_headlines_are_49_700_ink(self):
        s2 = self.slides[1]
        h = [e for e in s2["elements"] if e["role"] == "headline"][0]
        self.assertEqual((h["font_px"], h["weight"], h["color"]),
                         (49, 700, measure.TOKENS["ink"]))

    def test_body_drops_marker_and_is_muted(self):
        s1 = self.slides[0]
        body = [e for e in s1["elements"] if e["role"] == "body"][0]
        self.assertEqual(body["text"], "Same city. Same 3 months.")
        self.assertEqual((body["font_px"], body["weight"], body["color"]),
                         (25, 400, measure.TOKENS["ink-muted"]))

    def test_source_stamp_keeps_prefix(self):
        s3 = self.slides[2]
        src = [e for e in s3["elements"] if e["role"] == "source-stamp"][0]
        self.assertTrue(src["text"].startswith("Source:"))
        self.assertIn("as of", src["text"])
        self.assertEqual(src["font_px"], 20)

    def test_s3_chart_ref_recorded_no_element(self):
        s3 = self.slides[2]
        self.assertEqual(s3["chart_ref"], "chart-spec.md")
        # bracket line produced no element; only body + source-stamp
        self.assertEqual(len(s3["elements"]), 2)

    def test_cta_link_is_accent_when_no_wordmark(self):
        s7 = self.slides[6]
        link = [e for e in s7["elements"] if e["text"] == "intel.terrem.in/markets"][0]
        self.assertEqual(link["color"], measure.TOKENS["accent"])
        self.assertEqual(link["weight"], 500)
        self.assertEqual(link["role"], "body")

    def test_source_slide_link_is_muted_because_wordmark_present(self):
        s8 = self.slides[7]
        link = [e for e in s8["elements"] if e["text"] == "intel.terrem.in/markets"][0]
        self.assertEqual(link["color"], measure.TOKENS["ink-muted"])
        wm = [e for e in s8["elements"] if e["role"] == "wordmark"][0]
        self.assertEqual(wm["text"], "TERREM")
        self.assertEqual(wm["color"], measure.TOKENS["accent-deep"])

    def test_html_comments_stripped(self):
        # S7 link had a UTM comment; it must not appear in any rendered text.
        for s in self.slides:
            for e in s["elements"]:
                self.assertNotIn("UTM", e["text"])
                self.assertNotIn("<!--", e["text"])

    def test_every_color_is_brand_token(self):
        for s in self.slides:
            for e in s["elements"]:
                self.assertTrue(measure.is_brand_token(e["color"]), e["color"])


class TestParseErrors(unittest.TestCase):
    def test_no_slides_raises(self):
        with self.assertRaises(ValueError):
            render.parse_carousel("no headers here\njust prose\n")

    def test_unparseable_line_names_slide(self):
        md = "**S1 — X**\n> a hook line\nthis line is not recognized grammar\n"
        with self.assertRaises(ValueError) as ctx:
            render.parse_carousel(md)
        self.assertIn("slide 1", str(ctx.exception))


class TestLayout(unittest.TestCase):
    def test_wrap_single_long_word_placed_alone(self):
        font = render._font(400, 25)
        long = "x" * 400
        lines = render._wrap(long + " short", font)
        self.assertEqual(lines[0], long)

    def test_measure_single_line_height_is_em_height(self):
        # h of a one-line element == round(1.2*font_px) (glyph-size seam, Risk 4).
        el = {"role": "body", "text": "hi", "font_px": 25, "weight": 400,
              "color": measure.TOKENS["ink-muted"]}
        lines, w, h, adv, em = render._measure_element(el)
        self.assertEqual(len(lines), 1)
        self.assertEqual(h, round(25 * 1.2))
        self.assertEqual(adv, round(25 * 1.4))

    def test_layout_bboxes_inside_safe_zone(self):
        md = _TOOL_DIR.parent.parent / "content" / "2026-07-03-hyd-premium-vs-budget" / "carousel.md"
        slides = render.parse_carousel(md.read_text(encoding="utf-8"))
        for slide in slides:
            ops = render._layout_slide(slide)
            for op in ops:
                role = op["el"]["role"]
                if role in ("headline", "body", "hook"):
                    res = measure.safe_zone_ok(1080, 1350, op["bbox"])
                    self.assertTrue(res["passes"], (slide["n"], role, res))

    def test_overflow_fails_loud(self):
        # A slide with an absurd number of tall lines exceeds the band -> ValueError.
        big_text = " ".join(["word"] * 400)
        slide = {"n": 9, "chart_ref": None,
                 "elements": [{"role": "headline", "text": big_text, "font_px": 49,
                               "weight": 700, "color": measure.TOKENS["ink"]}]}
        with self.assertRaises(ValueError):
            render._layout_slide(slide)


class TestGlyphGuard(unittest.TestCase):
    def test_present_glyphs_pass(self):
        font = render._font(400, 25)
        # all special chars used in the asset copy resolve to real glyphs
        render._assert_glyphs("₹−≠·—–≥× ABC", font, 400, 25, 1, "body")

    def test_tofu_raises_named(self):
        font = render._font(400, 25)
        with self.assertRaises(RuntimeError) as ctx:
            render._assert_glyphs("A\U000F0000B", font, 400, 25, 3, "headline")
        msg = str(ctx.exception)
        self.assertIn("slide 3", msg)
        self.assertIn("headline", msg)


class TestRenderErrorStatesAtomic(unittest.TestCase):
    """Every error state exits without creating a render/ dir (no partial write)."""

    def test_missing_folder(self):
        with tempfile.TemporaryDirectory() as d:
            missing = os.path.join(d, "nope")
            rc = render.main([missing])
            self.assertEqual(rc, 1)
            self.assertFalse(os.path.exists(os.path.join(missing, "render")))

    def test_missing_carousel(self):
        with tempfile.TemporaryDirectory() as d:
            rc = render.main([d])
            self.assertEqual(rc, 1)
            self.assertFalse(os.path.exists(os.path.join(d, "render")))

    def test_unparseable_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "carousel.md"), "w", encoding="utf-8") as fh:
                fh.write("**S1 — X**\n> hook\nUNRECOGNIZED GRAMMAR LINE\n")
            rc = render.main([d])
            self.assertEqual(rc, 1)
            self.assertFalse(os.path.exists(os.path.join(d, "render")))


class TestRenderOutputAtomic(unittest.TestCase):
    def test_render_asset_writes_only_render_dir(self):
        # Render into a copy so the real asset dir is untouched by the test.
        with tempfile.TemporaryDirectory() as d:
            asset = Path(d) / "2026-07-03-hyd-premium-vs-budget"
            asset.mkdir()
            src_md = _TOOL_DIR.parent.parent / "content" / "2026-07-03-hyd-premium-vs-budget" / "carousel.md"
            (asset / "carousel.md").write_text(src_md.read_text(encoding="utf-8"),
                                               encoding="utf-8")
            rc = render.main([str(asset)])
            self.assertEqual(rc, 0)
            entries = sorted(os.listdir(asset))
            self.assertEqual(entries, ["carousel.md", "render"])
            pngs = sorted(f for f in os.listdir(asset / "render") if f.endswith(".png"))
            self.assertEqual(len(pngs), 8)
            self.assertIn("manifest.json", os.listdir(asset / "render"))


if __name__ == "__main__":
    unittest.main()
