"""Unit tests for the Sprint 003 captions module (contract s3.1)."""

import sys
import unittest
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parent.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))
import captions  # noqa: E402


class TestParse(unittest.TestCase):
    def test_single_all_block(self):
        text = ("<!-- caption:all:start -->\n"
                "Body line one.\nBody line two.\n"
                "<!-- caption:all:end -->\n")
        self.assertEqual(captions.parse_captions(text),
                         {"all": "Body line one.\nBody line two."})

    def test_blank_edges_stripped_interior_preserved(self):
        text = ("<!-- caption:all:start -->\n"
                "\n\n  indented interior  \n\ninterior2\n\n"
                "<!-- caption:all:end -->\n")
        # Leading/trailing blank lines stripped; interior (incl. the blank line
        # between the two content lines and the interior whitespace) preserved.
        self.assertEqual(captions.parse_captions(text)["all"],
                         "  indented interior  \n\ninterior2")

    def test_multiple_blocks(self):
        text = ("<!-- caption:all:start -->\nshared\n<!-- caption:all:end -->\n"
                "\n"
                "<!-- caption:instagram:start -->\nig\n<!-- caption:instagram:end -->\n")
        self.assertEqual(captions.parse_captions(text),
                         {"all": "shared", "instagram": "ig"})

    def test_unknown_key_block_is_not_an_error(self):
        # Forward-looking / unknown key parses harmlessly (permissive).
        text = ("<!-- caption:all:start -->\nshared\n<!-- caption:all:end -->\n"
                "<!-- caption:twitter:start -->\ntw\n<!-- caption:twitter:end -->\n")
        blocks = captions.parse_captions(text)
        self.assertEqual(blocks["all"], "shared")
        self.assertEqual(blocks["twitter"], "tw")

    def test_empty_text_no_blocks(self):
        self.assertEqual(captions.parse_captions(""), {})


class TestParseErrors(unittest.TestCase):
    def test_start_without_end_raises(self):
        with self.assertRaises(ValueError):
            captions.parse_captions("<!-- caption:all:start -->\nbody\n")

    def test_nested_start_raises(self):
        text = ("<!-- caption:all:start -->\n"
                "<!-- caption:instagram:start -->\nx\n"
                "<!-- caption:instagram:end -->\n")
        with self.assertRaises(ValueError):
            captions.parse_captions(text)

    def test_end_without_start_raises(self):
        with self.assertRaises(ValueError):
            captions.parse_captions("<!-- caption:all:end -->\n")

    def test_mismatched_end_key_raises(self):
        text = "<!-- caption:all:start -->\nx\n<!-- caption:instagram:end -->\n"
        with self.assertRaises(ValueError):
            captions.parse_captions(text)

    def test_duplicate_key_raises(self):
        text = ("<!-- caption:all:start -->\na\n<!-- caption:all:end -->\n"
                "<!-- caption:all:start -->\nb\n<!-- caption:all:end -->\n")
        with self.assertRaises(ValueError):
            captions.parse_captions(text)


class TestBodyFor(unittest.TestCase):
    def test_channel_specific_wins(self):
        blocks = {"all": "shared", "instagram": "ig"}
        self.assertEqual(captions.body_for(blocks, "instagram"), "ig")

    def test_falls_back_to_all(self):
        blocks = {"all": "shared"}
        self.assertEqual(captions.body_for(blocks, "youtube"), "shared")

    def test_absent_returns_none(self):
        blocks = {"instagram": "ig"}
        self.assertIsNone(captions.body_for(blocks, "youtube"))

    def test_no_blocks_returns_none(self):
        self.assertIsNone(captions.body_for({}, "linkedin"))

    def test_unknown_channel_raises(self):
        with self.assertRaises(ValueError):
            captions.body_for({"all": "x"}, "twitter")


class TestLoadCaptions(unittest.TestCase):
    def test_missing_file_raises_filenotfound(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                captions.load_captions(Path(d) / "captions.md")

    def test_real_asset_captions_has_all_body(self):
        repo = _TOOL_DIR.parent.parent
        p = repo / "content" / "2026-07-03-tgrera-enforcement-wave" / "captions.md"
        blocks = captions.load_captions(p)
        self.assertIn("all", blocks)
        self.assertTrue(blocks["all"].strip())
        # Fallback resolves every channel to the single all block.
        for c in ("instagram", "youtube", "linkedin"):
            self.assertEqual(captions.body_for(blocks, c), blocks["all"])


class TestImportSafety(unittest.TestCase):
    def test_import_is_silent(self):
        import subprocess
        repo = _TOOL_DIR.parent.parent
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0,'tools/marketing-loops'); import captions"],
            capture_output=True, text=True, cwd=str(repo))
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.stderr, "")


if __name__ == "__main__":
    unittest.main()
