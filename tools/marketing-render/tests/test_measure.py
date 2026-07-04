"""Unit tests for the Sprint 001 measurement core (stdlib unittest only).

Run from repo root:
    python3 -m unittest discover -s tools/marketing-render/tests -v

No package markers exist (parent dir has a hyphen); we put the tool dir on
sys.path before importing, matching the Evaluator attack script.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import measure as m  # noqa: E402

# Repo root, used to reach brand/brand-kit.md deterministically regardless of cwd.
REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
BRAND_KIT = os.path.join(REPO_ROOT, "brand", "brand-kit.md")


class TestTokens(unittest.TestCase):
    def test_exactly_nine_tokens(self):
        self.assertEqual(len(m.TOKENS), 9)
        self.assertEqual(len(m.TOKEN_HEXES), 9)

    def test_token_values_lowercase_and_expected(self):
        self.assertEqual(m.TOKENS["bg"], "#faf8f3")
        self.assertEqual(m.TOKENS["ink"], "#1c1917")
        self.assertEqual(m.TOKENS["accent-deep"], "#0d3d38")
        for hex_val in m.TOKENS.values():
            self.assertEqual(hex_val, hex_val.lower())

    def test_is_brand_token(self):
        self.assertTrue(m.is_brand_token("#FAF8F3"))
        self.assertTrue(m.is_brand_token("faf8f3"))
        self.assertFalse(m.is_brand_token("#123456"))

    def test_token_name(self):
        self.assertEqual(m.token_name("#0f766e"), "accent")
        self.assertEqual(m.token_name("#1c1917"), "ink")
        self.assertIsNone(m.token_name("#123456"))


class TestNormalizeHex(unittest.TestCase):
    def test_accepts_forms(self):
        self.assertEqual(m.normalize_hex("#FAF8F3"), "#faf8f3")
        self.assertEqual(m.normalize_hex("faf8f3"), "#faf8f3")
        self.assertEqual(m.normalize_hex("#1C1917"), "#1c1917")

    def test_rejects_bad(self):
        for bad in ("#12", " zzz", "#1234567", "12g4f6", "#fff", "fff", "", 123, None):
            with self.assertRaises(ValueError):
                m.normalize_hex(bad)


class TestContrast(unittest.TestCase):
    def test_ink_on_bg_wcag(self):
        r = m.contrast_ratio("#1c1917", "#faf8f3")
        self.assertGreaterEqual(r, 16.0)
        self.assertLessEqual(r, 17.0)

    def test_accent_on_bg(self):
        r = m.contrast_ratio("#0f766e", "#faf8f3")
        self.assertGreaterEqual(r, 5.0)
        self.assertLessEqual(r, 5.3)

    def test_symmetric(self):
        self.assertEqual(
            m.contrast_ratio("#1c1917", "#faf8f3"),
            m.contrast_ratio("#faf8f3", "#1c1917"),
        )

    def test_identical_is_one(self):
        self.assertAlmostEqual(m.contrast_ratio("#111111", "#111111"), 1.0, places=9)

    def test_white_black_is_21(self):
        self.assertAlmostEqual(m.contrast_ratio("#ffffff", "#000000"), 21.0, places=2)

    def test_luminance_bounds(self):
        self.assertAlmostEqual(m.relative_luminance("#000000"), 0.0, places=9)
        self.assertAlmostEqual(m.relative_luminance("#ffffff"), 1.0, places=9)


class TestIsLargeText(unittest.TestCase):
    def test_boundaries(self):
        self.assertTrue(m.is_large_text(24, 400))
        self.assertFalse(m.is_large_text(23.9, 400))
        self.assertTrue(m.is_large_text(18.5, 700))
        self.assertFalse(m.is_large_text(18.5, 400))
        self.assertFalse(m.is_large_text(18.4, 700))


class TestContrastCheck(unittest.TestCase):
    def test_accent_passes_normal(self):
        res = m.contrast_check("#0f766e", "#faf8f3", 24, 400)
        self.assertTrue(res["passes"])
        self.assertEqual(res["threshold"], 3.0)  # 24px is large

    def test_accent_passes_as_normal_when_small(self):
        res = m.contrast_check("#0f766e", "#faf8f3", 20, 400)
        self.assertEqual(res["threshold"], 4.5)
        self.assertTrue(res["passes"])  # ~5.15 >= 4.5

    def test_chart_up_small_fails_normal(self):
        res = m.contrast_check("#0d9488", "#faf8f3", 20, 400)
        self.assertEqual(res["threshold"], 4.5)
        self.assertFalse(res["passes"])

    def test_chart_up_large_passes(self):
        res = m.contrast_check("#0d9488", "#faf8f3", 30, 400)
        self.assertEqual(res["threshold"], 3.0)
        self.assertTrue(res["passes"])

    def test_passes_uses_raw_not_rounded(self):
        # ratio field is display-rounded to 2 decimals
        res = m.contrast_check("#1c1917", "#faf8f3", 24, 400)
        self.assertEqual(res["ratio"], round(res["ratio"], 2))


class TestTypeMin(unittest.TestCase):
    def test_carousel_headline(self):
        self.assertTrue(m.type_min_ok("carousel-slide", "headline", 48)["passes"])
        self.assertFalse(m.type_min_ok("carousel-slide", "headline", 47)["passes"])
        self.assertEqual(m.type_min_ok("carousel-slide", "headline", 48)["minimum"], 48)

    def test_chart_card_headline(self):
        self.assertTrue(m.type_min_ok("chart-card", "headline", 36)["passes"])
        self.assertFalse(m.type_min_ok("chart-card", "headline", 35)["passes"])

    def test_hook_takes_headline_minimum(self):
        self.assertTrue(m.type_min_ok("carousel-slide", "hook", 48)["passes"])
        self.assertFalse(m.type_min_ok("carousel-slide", "hook", 47)["passes"])

    def test_body(self):
        self.assertTrue(m.type_min_ok("carousel-slide", "body", 24)["passes"])
        self.assertFalse(m.type_min_ok("carousel-slide", "body", 23)["passes"])

    def test_exempt_roles(self):
        for role in ("source-stamp", "wordmark", "chart-label"):
            res = m.type_min_ok("chart-card", role, 12)
            self.assertIsNone(res["minimum"])
            self.assertTrue(res["passes"])

    def test_unknown_roles_raise(self):
        with self.assertRaises(ValueError):
            m.type_min_ok("banner", "headline", 48)
        with self.assertRaises(ValueError):
            m.type_min_ok("carousel-slide", "caption", 48)


class TestSizeConsistent(unittest.TestCase):
    def test_truthful_passes(self):
        self.assertTrue(m.size_consistent(48, 45))
        self.assertTrue(m.size_consistent(48, 48))
        self.assertTrue(m.size_consistent(48, 36))  # exactly -25%
        self.assertTrue(m.size_consistent(48, 60))  # exactly +25%

    def test_lie_fails(self):
        self.assertFalse(m.size_consistent(48, 24))  # 2x lie
        self.assertFalse(m.size_consistent(48, 35))  # below band
        self.assertFalse(m.size_consistent(48, 61))  # above band


class TestSafeZone(unittest.TestCase):
    def test_carousel_fits(self):
        self.assertTrue(m.safe_zone_ok(1080, 1350, [40, 40, 1000, 1270])["passes"])

    def test_carousel_one_px_over_bottom(self):
        res = m.safe_zone_ok(1080, 1350, [40, 40, 1000, 1271])
        self.assertFalse(res["passes"])
        self.assertIn("bottom", res["reason"])

    def test_carousel_left_of_xmin(self):
        res = m.safe_zone_ok(1080, 1350, [39, 40, 10, 10])
        self.assertFalse(res["passes"])
        self.assertIn("left", res["reason"])

    def test_vertical_fits(self):
        self.assertTrue(m.safe_zone_ok(1080, 1920, [100, 250, 800, 1230])["passes"])

    def test_vertical_above_ymin(self):
        res = m.safe_zone_ok(1080, 1920, [100, 249, 800, 10])
        self.assertFalse(res["passes"])
        self.assertIn("top", res["reason"])

    def test_vertical_below_ymax(self):
        res = m.safe_zone_ok(1080, 1920, [100, 300, 800, 1181])
        self.assertFalse(res["passes"])
        self.assertIn("bottom", res["reason"])

    def test_unknown_canvas_raises(self):
        with self.assertRaises(ValueError):
            m.safe_zone_ok(1200, 627, [0, 0, 10, 10])

    def test_bad_bbox_raises(self):
        with self.assertRaises(ValueError):
            m.safe_zone_ok(1080, 1350, [0, 0, 10])
        with self.assertRaises(ValueError):
            m.safe_zone_ok(1080, 1350, [0, 0, -10, 10])


class TestBlacklist(unittest.TestCase):
    def test_parses_exactly_five_from_real_file(self):
        ph = m.parse_blacklist(BRAND_KIT)
        self.assertEqual(len(ph), 5, ph)

    def test_phrases_verbatim(self):
        ph = m.parse_blacklist(BRAND_KIT)
        self.assertEqual(ph[0], "90% of recall in first 6 seconds")
        self.assertEqual(ph[1], "TikTok-native ads drive 3.3x actions")
        self.assertEqual(ph[2], "hooked ads 2x engagement / +43% purchase intent")
        self.assertEqual(ph[3], "best slots are Wed 4pm / Fri 3–4pm")  # en-dash preserved
        self.assertEqual(ph[4], "professionals scroll LinkedIn on the evening commute")

    def test_not_hardcoded_parses_synthetic_section(self):
        # Hostile check: a different '## 8' section yields different phrases,
        # proving parse_blacklist reads the file rather than returning a constant.
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tf:
            tf.write(
                '## 7. Prev\n\nfiller\n\n'
                '## 8. Blacklist\n\n'
                'Banned: "alpha claim one" · "beta claim two" · "gamma claim three".\n'
            )
            path = tf.name
        try:
            ph = m.parse_blacklist(path)
            self.assertEqual(ph, ["alpha claim one", "beta claim two", "gamma claim three"])
        finally:
            os.unlink(path)

    def test_missing_section_raises(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as tf:
            tf.write("## 1. Intro\n\nno blacklist here\n")
            path = tf.name
        try:
            with self.assertRaises(ValueError):
                m.parse_blacklist(path)
        finally:
            os.unlink(path)

    def test_scan_hit(self):
        ph = m.parse_blacklist(BRAND_KIT)
        hits = m.scan_blacklist(
            "Our data shows 90% of recall in first 6 seconds, allegedly.", ph
        )
        self.assertIn("90% of recall in first 6 seconds", hits)

    def test_scan_clean(self):
        ph = m.parse_blacklist(BRAND_KIT)
        self.assertEqual(
            m.scan_blacklist("Clean copy: RERA Karnataka orders as of 2026-06-30.", ph),
            [],
        )

    def test_scan_dash_case_insensitive(self):
        ph = m.parse_blacklist(BRAND_KIT)
        # ascii dash + lowercase still matches the en-dash phrase
        hits = m.scan_blacklist("the BEST slots are wed 4pm / fri 3-4pm they said", ph)
        self.assertTrue(hits)

    def test_normalize_for_scan(self):
        # collapse runs of whitespace to a single space (no strip per contract)
        self.assertEqual(m.normalize_for_scan("A  B\tC"), "a b c")
        self.assertEqual(m.normalize_for_scan("3–4pm"), "3-4pm")
        self.assertEqual(m.normalize_for_scan("3—4pm"), "3-4pm")


class TestConstants(unittest.TestCase):
    def test_size_tolerance(self):
        self.assertEqual(m.SIZE_TOLERANCE, 0.25)

    def test_safe_zones(self):
        self.assertEqual(
            m.SAFE_ZONES[(1080, 1350)],
            {"x_min": 40, "y_min": 40, "x_max": 1040, "y_max": 1310},
        )
        self.assertEqual(
            m.SAFE_ZONES[(1080, 1920)],
            {"x_min": 0, "y_min": 250, "x_max": 1080, "y_max": 1480},
        )


if __name__ == "__main__":
    unittest.main()
