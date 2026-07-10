"""Unit tests for the Sprint 002 Channels: parser (contract s3.5).

Covers the alias table, dedup, format-word tolerance, unmapped-token surfacing,
empty result, canonical ordering, and the real-asset ground truth.
"""

import sys
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_TOOL_DIR = _TESTS_DIR.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))
import channels  # noqa: E402
import utm        # noqa: E402

_REPO_ROOT = _TOOL_DIR.parent.parent
_CONTENT = _REPO_ROOT / "content"


class TestCanonicalSetIsShared(unittest.TestCase):
    def test_canonical_derived_from_utm_map(self):
        # No forked copy: order + membership come from the Sprint-001 map.
        self.assertEqual(channels.CANONICAL_CHANNELS,
                         tuple(utm.CHANNEL_SOURCE_MAP.keys()))
        # facebook appended last (publish-loop Sprint 001, spec B34).
        self.assertEqual(channels.CANONICAL_CHANNELS,
                         ("instagram", "youtube", "linkedin", "facebook"))


class TestParse(unittest.TestCase):
    def test_aliases_case_insensitive(self):
        ch, un = channels.parse_channels_line("ig, YT, linkedin")
        self.assertEqual(ch, ["instagram", "youtube", "linkedin"])
        self.assertEqual(un, [])

    def test_dedup_across_format_variants(self):
        ch, un = channels.parse_channels_line("IG carousel + reel")
        self.assertEqual(ch, ["instagram"])
        self.assertEqual(un, [])

    def test_format_words_ignored_not_unmapped(self):
        ch, un = channels.parse_channels_line(
            "IG reel, YT short (LinkedIn text post variant included)")
        self.assertEqual(ch, ["instagram", "youtube", "linkedin"])
        self.assertEqual(un, [])

    def test_canonical_order_regardless_of_input_order(self):
        ch, _ = channels.parse_channels_line("LinkedIn, YT, IG")
        self.assertEqual(ch, ["instagram", "youtube", "linkedin"])

    def test_unmapped_platform_surfaced(self):
        ch, un = channels.parse_channels_line("IG reel, Twitter post, YT short")
        self.assertEqual(ch, ["instagram", "youtube"])
        self.assertEqual(un, ["Twitter"])

    def test_facebook_alias_maps(self):
        # spec B34: "Facebook" now maps instead of surfacing as unmapped.
        self.assertEqual(channels.parse_channels_line("Facebook post"),
                         (["facebook"], []))

    def test_fb_alias_case_insensitive(self):
        self.assertEqual(channels.parse_channels_line("FB reel"),
                         (["facebook"], []))

    def test_mixed_facebook_keeps_canonical_order(self):
        ch, un = channels.parse_channels_line("Facebook, IG, LinkedIn")
        self.assertEqual(ch, ["instagram", "linkedin", "facebook"])
        self.assertEqual(un, [])

    def test_facebook_does_not_disable_unmapped_surfacing(self):
        # Adding facebook must not turn off surfacing for other unknown platforms.
        ch, un = channels.parse_channels_line("FB reel, Twitter post")
        self.assertEqual(ch, ["facebook"])
        self.assertEqual(un, ["Twitter"])

    def test_only_format_words_yields_empty(self):
        ch, un = channels.parse_channels_line("carousel reel short PDF")
        self.assertEqual(ch, [])
        self.assertEqual(un, [])

    def test_pure_punctuation_ignored(self):
        ch, un = channels.parse_channels_line("IG + , ( ) reel")
        self.assertEqual(ch, ["instagram"])
        self.assertEqual(un, [])


class TestExtractLine(unittest.TestCase):
    def test_extract_present(self):
        meta = "# x\n```\nChannels: IG reel\n```\n"
        self.assertEqual(channels.extract_channels_line(meta), "IG reel")

    def test_extract_absent(self):
        self.assertIsNone(channels.extract_channels_line("# x\nHook: foo\n"))

    def test_channels_for_asset_no_line(self):
        ch, un, had = channels.channels_for_asset("# x\nHook: foo\n")
        self.assertEqual((ch, un, had), ([], [], False))


class TestRealAssets(unittest.TestCase):
    def test_real_tgrera_three_channels(self):
        meta = (_CONTENT / "2026-07-03-tgrera-enforcement-wave" / "meta.md").read_text()
        ch, un, had = channels.channels_for_asset(meta)
        self.assertTrue(had)
        self.assertEqual(ch, ["instagram", "youtube", "linkedin"])
        self.assertEqual(un, [])

    def test_real_hyd_three_channels(self):
        meta = (_CONTENT / "2026-07-03-hyd-premium-vs-budget" / "meta.md").read_text()
        ch, un, had = channels.channels_for_asset(meta)
        self.assertEqual(ch, ["instagram", "youtube", "linkedin"])
        self.assertEqual(un, [])


if __name__ == "__main__":
    unittest.main()
