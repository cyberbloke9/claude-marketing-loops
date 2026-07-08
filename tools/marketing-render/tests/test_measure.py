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


# =============================================================================
# Sprint 001 (run 003) — Renderer V2 measurement core (contract §8 rows 1-21)
# =============================================================================


def _el(role, fpx=30):
    """Minimal element dict for the V13 helpers (only role/font_px are read)."""
    return {"role": role, "font_px": fpx}


class TestBodyReference(unittest.TestCase):
    def test_max_of_body_elements(self):
        els = [_el("body", 26), _el("body", 30), _el("dominant", 96)]
        self.assertEqual(m.body_reference(els), 30)

    def test_fallback_26_when_no_body(self):  # row 8
        self.assertEqual(m.body_reference([_el("dominant", 96)]), 26)
        self.assertEqual(m.body_reference([]), 26)


class TestCountDominant(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(m.count_dominant([]), 0)
        self.assertEqual(m.count_dominant([_el("dominant"), _el("body")]), 1)
        self.assertEqual(m.count_dominant([_el("dominant"), _el("dominant")]), 2)


class TestIsUtilitySlide(unittest.TestCase):
    def test_pure_utility(self):  # rows 5, 6
        self.assertTrue(m.is_utility_slide([_el("so-what"), _el("wordmark")]))
        self.assertTrue(m.is_utility_slide([_el("source-stamp"), _el("wordmark")]))
        self.assertTrue(m.is_utility_slide([_el("so-what")]))

    def test_content_role_disqualifies(self):  # row 7
        self.assertFalse(m.is_utility_slide([_el("so-what"), _el("body")]))
        self.assertFalse(m.is_utility_slide([_el("dominant")]))
        self.assertFalse(m.is_utility_slide([_el("headline")]))

    def test_empty_is_not_utility(self):
        self.assertFalse(m.is_utility_slide([]))


class TestDominantRatioOk(unittest.TestCase):
    def test_boundary_pass_3x(self):  # row 1
        r = m.dominant_ratio_ok([_el("body", 26), _el("dominant", 78)])
        self.assertTrue(r["passes"])
        self.assertEqual(r["ratio"], 3.0)
        self.assertFalse(r["exempt"])
        self.assertEqual(r["dominant_count"], 1)
        self.assertEqual(r["body_reference"], 26)

    def test_boundary_fail_below_3x(self):  # row 2
        r = m.dominant_ratio_ok([_el("body", 26), _el("dominant", 77)])
        self.assertFalse(r["passes"])
        self.assertLess(r["ratio"], 3.0)

    def test_zero_dominant_with_body_fails(self):  # row 3
        r = m.dominant_ratio_ok([_el("body", 26), _el("headline", 48)])
        self.assertFalse(r["passes"])
        self.assertFalse(r["exempt"])
        self.assertIn("no dominant", r["reason"])

    def test_two_dominants_fail(self):  # row 4
        r = m.dominant_ratio_ok([_el("dominant", 96), _el("dominant", 90)])
        self.assertFalse(r["passes"])
        self.assertEqual(r["dominant_count"], 2)
        self.assertIn("2 dominant", r["reason"])
        self.assertIn("exactly one", r["reason"])

    def test_utility_exempt(self):  # rows 5, 6
        r = m.dominant_ratio_ok([_el("so-what"), _el("wordmark")])
        self.assertTrue(r["exempt"])
        self.assertTrue(r["passes"])

    def test_empty_is_content_no_dominant(self):
        r = m.dominant_ratio_ok([])
        self.assertFalse(r["exempt"])
        self.assertEqual(r["dominant_count"], 0)
        self.assertFalse(r["passes"])
        self.assertIn("no dominant", r["reason"])

    def test_fallback_ref_when_no_body(self):
        # dominant 78, no body -> ref 26 -> ratio exactly 3.0 -> pass.
        r = m.dominant_ratio_ok([_el("dominant", 78)])
        self.assertEqual(r["body_reference"], 26)
        self.assertTrue(r["passes"])


class TestFormatSlideTypeMin(unittest.TestCase):
    def test_body_floor_26(self):  # row 9
        self.assertTrue(m.format_slide_type_min("body", 26)["passes"])
        self.assertFalse(m.format_slide_type_min("body", 25)["passes"])
        self.assertEqual(m.format_slide_type_min("body", 26)["minimum"], 26)

    def test_source_stamp_floor_24(self):  # row 10
        self.assertTrue(m.format_slide_type_min("source-stamp", 24)["passes"])
        self.assertFalse(m.format_slide_type_min("source-stamp", 23)["passes"])
        self.assertFalse(m.format_slide_type_min("source-stamp", 20)["passes"])

    def test_headline_floor_48(self):  # row 11
        self.assertTrue(m.format_slide_type_min("headline", 48)["passes"])
        self.assertFalse(m.format_slide_type_min("headline", 47)["passes"])

    def test_wordmark_exempt(self):  # row 12
        r = m.format_slide_type_min("wordmark", 8)
        self.assertIsNone(r["minimum"])
        self.assertTrue(r["passes"])

    def test_contract_decision_floors(self):
        self.assertEqual(m.format_slide_type_min("so-what", 26)["minimum"], 26)
        self.assertEqual(m.format_slide_type_min("dominant", 48)["minimum"], 48)
        self.assertEqual(m.format_slide_type_min("hook", 48)["minimum"], 48)
        self.assertEqual(m.format_slide_type_min("chart-label", 26)["minimum"], 26)

    def test_unknown_role_raises(self):  # row 13
        with self.assertRaises(ValueError) as ctx:
            m.format_slide_type_min("banana", 40)
        self.assertIn("banana", str(ctx.exception))

    def test_v1_type_minimums_untouched(self):
        # Isolation: the v1 table is byte-for-byte unchanged.
        self.assertEqual(m._TYPE_MINIMUMS["body"]["carousel-slide"], 24)
        self.assertIsNone(m._TYPE_MINIMUMS["source-stamp"]["carousel-slide"])


class TestThumbnail(unittest.TestCase):
    def test_scale_band(self):  # row 17
        self.assertAlmostEqual(m.thumbnail_scale_band(39.84), 13.28, places=6)
        self.assertAlmostEqual(m.thumbnail_scale_band(1080.0), 360.0, places=6)

    def test_headline_boundary(self):  # row 14
        self.assertTrue(m.thumbnail_ink_ok("headline", 13.0)["passes"])
        self.assertFalse(m.thumbnail_ink_ok("headline", 12.99)["passes"])
        self.assertTrue(m.thumbnail_ink_ok("hook", 13.0)["passes"])

    def test_dominant_boundary(self):  # row 15
        self.assertTrue(m.thumbnail_ink_ok("dominant", 21.0)["passes"])
        self.assertFalse(m.thumbnail_ink_ok("dominant", 20.99)["passes"])

    def test_unknown_role_raises(self):  # row 16
        with self.assertRaises(ValueError):
            m.thumbnail_ink_ok("body", 30)
        with self.assertRaises(ValueError):
            m.thumbnail_ink_ok("source-stamp", 30)

    def test_pinned_constants(self):
        self.assertEqual(m.THUMB_W, 360)
        self.assertEqual(m.CANVAS_W, 1080)
        self.assertEqual(m.THUMB_HEADLINE_MIN_PX, 13)
        self.assertEqual(m.THUMB_DOMINANT_MIN_PX, 21)


_VALID_BLOCK = (
    "# meta\n\n"
    "<!-- cover-pattern:start -->\n"
    "pattern: BIG-NUMBER            # or CHART-FIRST  (V17)\n"
    "one_dataset: TGRERA enforcement orders, Jun 2026   # (V19)\n"
    "<!-- cover-pattern:end -->\n"
)


class TestCoverPatternBlock(unittest.TestCase):
    def test_parse_valid_block(self):  # row 18
        parsed = m.parse_cover_pattern_block(_VALID_BLOCK)
        self.assertEqual(parsed["pattern"], "BIG-NUMBER")
        self.assertEqual(parsed["one_dataset"], "TGRERA enforcement orders, Jun 2026")

    def test_parse_absent_block(self):  # row 21
        self.assertIsNone(m.parse_cover_pattern_block("# meta\n\nno block here\n"))

    def test_cover_pattern_valid_true(self):  # row 19
        parsed = m.parse_cover_pattern_block(
            _VALID_BLOCK.replace("BIG-NUMBER", "CHART-FIRST"))
        self.assertTrue(m.cover_pattern_valid(parsed))

    def test_cover_pattern_invalid_value(self):  # row 20
        parsed = m.parse_cover_pattern_block(
            _VALID_BLOCK.replace("BIG-NUMBER", "TIMELINE"))
        self.assertIsNotNone(parsed)
        self.assertFalse(m.cover_pattern_valid(parsed))

    def test_none_predicates(self):  # row 21
        self.assertFalse(m.cover_pattern_valid(None))
        self.assertFalse(m.one_dataset_present(None))

    def test_one_dataset_present(self):
        parsed = m.parse_cover_pattern_block(_VALID_BLOCK)
        self.assertTrue(m.one_dataset_present(parsed))

    def test_one_dataset_missing(self):
        block = (
            "<!-- cover-pattern:start -->\n"
            "pattern: BIG-NUMBER\n"
            "<!-- cover-pattern:end -->\n"
        )
        parsed = m.parse_cover_pattern_block(block)
        self.assertFalse(m.one_dataset_present(parsed))
        self.assertTrue(m.cover_pattern_valid(parsed))

    def test_valid_patterns_set(self):
        self.assertEqual(m.VALID_COVER_PATTERNS,
                         frozenset({"BIG-NUMBER", "CHART-FIRST"}))


if __name__ == "__main__":
    unittest.main()
