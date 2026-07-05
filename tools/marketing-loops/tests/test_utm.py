"""Unit tests for the Sprint 001 shared UTM module + verifier CLI (contract s8).

Every violation code is proven to fire on its dedicated fixture, and OK on the
positive control. The real content assets are positive controls too. Run:

    python3 -m unittest discover -s tools/marketing-loops/tests -v
"""

import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_TOOL_DIR = _TESTS_DIR.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))
import utm            # noqa: E402
import verify_utm     # noqa: E402

_REPO_ROOT = _TOOL_DIR.parent.parent
_FIXTURES = _TOOL_DIR / "fixtures"
_CONTENT = _REPO_ROOT / "content"
_VERIFY = _TOOL_DIR / "verify_utm.py"


def fx(name):
    return _FIXTURES / name


def codes(asset_dir):
    return [v["code"] for v in utm.validate_asset(asset_dir)["violations"]]


class TestChannelMap(unittest.TestCase):
    def test_exactly_three_channels(self):
        self.assertEqual(
            sorted(utm.CHANNEL_SOURCE_MAP), ["instagram", "linkedin", "youtube"])

    def test_allowed_sources_derived_from_map(self):
        self.assertEqual(
            utm.ALLOWED_SOURCES, frozenset(utm.CHANNEL_SOURCE_MAP.values()))

    def test_youtube_maps_to_youtube_source(self):
        self.assertEqual(utm.CHANNEL_SOURCE_MAP["youtube"], "youtube")


class TestCampaignFromSlug(unittest.TestCase):
    def test_strips_date_prefix(self):
        self.assertEqual(
            utm.campaign_from_slug("2026-07-03-hyd-premium-vs-budget"),
            "hyd-premium-vs-budget")

    def test_no_prefix_unchanged(self):
        self.assertEqual(utm.campaign_from_slug("plain-slug"), "plain-slug")

    def test_only_leading_prefix_stripped(self):
        # A date-looking token later in the name must not be stripped.
        self.assertEqual(
            utm.campaign_from_slug("2026-01-01-recap-2025-12-31"),
            "recap-2025-12-31")

    def test_accepts_path(self):
        self.assertEqual(
            utm.campaign_from_slug(Path("/x/2026-07-03-foo")), "foo")


class TestParseFlywheelLine(unittest.TestCase):
    def test_missing_line_returns_none(self):
        self.assertIsNone(utm.parse_flywheel_line("no flywheel here\n"))

    def test_parses_params(self):
        text = ("Flywheel target: https://intel.terrem.in/markets?"
                "utm_source=instagram&utm_medium=social&utm_campaign=foo\n")
        p = utm.parse_flywheel_line(text)
        self.assertTrue(p["query_parsed"])
        self.assertEqual(p["utm_source"], "instagram")
        self.assertEqual(p["utm_medium"], "social")
        self.assertEqual(p["utm_campaign"], "foo")

    def test_ignores_per_channel_continuation_line(self):
        # Only the primary URL is parsed; the continuation must not leak in.
        text = ("Flywheel target: https://intel.terrem.in/markets?"
                "utm_source=instagram&utm_medium=social&utm_campaign=foo\n"
                "  (per-channel: utm_source=youtube / linkedin)\n")
        p = utm.parse_flywheel_line(text)
        self.assertEqual(p["utm_source"], "instagram")

    def test_no_query_string_flagged_not_parsed(self):
        p = utm.parse_flywheel_line("Flywheel target: https://intel.terrem.in/markets\n")
        self.assertFalse(p["query_parsed"])
        self.assertIsNone(p["utm_source"])


class TestValidateAssetFixtures(unittest.TestCase):
    """Each fixture fires exactly its intended code(s) (contract s9)."""

    def test_valid_asset_ok(self):
        r = utm.validate_asset(fx("2026-07-03-valid-asset"))
        self.assertTrue(r["ok"])
        self.assertEqual(r["violations"], [])

    def test_missing_line(self):
        self.assertEqual(codes(fx("2026-07-03-missing-line")),
                         [utm.CODE_MISSING_LINE])

    def test_malformed_query(self):
        self.assertEqual(codes(fx("2026-07-03-malformed-query")),
                         [utm.CODE_MALFORMED_QUERY])

    def test_wrong_medium(self):
        self.assertEqual(codes(fx("2026-07-03-wrong-medium")),
                         [utm.CODE_WRONG_MEDIUM])

    def test_campaign_mismatch(self):
        self.assertEqual(codes(fx("2026-07-03-campaign-mismatch")),
                         [utm.CODE_CAMPAIGN_MISMATCH])

    def test_unknown_source(self):
        self.assertEqual(codes(fx("2026-07-03-unknown-source")),
                         [utm.CODE_UNKNOWN_SOURCE])

    def test_absent_source_is_unknown_source(self):
        self.assertEqual(codes(fx("2026-07-03-absent-source")),
                         [utm.CODE_UNKNOWN_SOURCE])

    def test_multi_defect_order(self):
        # wrong-medium and unknown-source both fire; campaign is correct.
        self.assertEqual(codes(fx("2026-07-03-multi-defect")),
                         [utm.CODE_WRONG_MEDIUM, utm.CODE_UNKNOWN_SOURCE])

    def test_message_is_specific(self):
        r = utm.validate_asset(fx("2026-07-03-wrong-medium"))
        self.assertIn("paid", r["violations"][0]["message"])
        self.assertIn("social", r["violations"][0]["message"])


class TestRealContent(unittest.TestCase):
    """Both real assets are UTM-valid positive controls (contract s4)."""

    def test_tgrera_ok(self):
        r = utm.validate_asset(_CONTENT / "2026-07-03-tgrera-enforcement-wave")
        self.assertTrue(r["ok"], r["violations"])

    def test_killed_hyd_ok(self):
        # KILLED is orthogonal to UTM validity; the scan must still pass it.
        r = utm.validate_asset(_CONTENT / "2026-07-03-hyd-premium-vs-budget")
        self.assertTrue(r["ok"], r["violations"])


class TestValidateAssetPrecondition(unittest.TestCase):
    def test_missing_meta_raises(self):
        with self.assertRaises(FileNotFoundError):
            utm.validate_asset(_TOOL_DIR)  # no meta.md here


class TestCliRun(unittest.TestCase):
    def _run(self, path):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = verify_utm.run(str(path))
        return rc, buf.getvalue()

    def test_content_root_exit_zero(self):
        rc, out = self._run(_CONTENT)
        self.assertEqual(rc, 0)
        self.assertIn("OK  2026-07-03-tgrera-enforcement-wave", out)
        self.assertIn("OK  2026-07-03-hyd-premium-vs-budget", out)

    def test_single_valid_asset_exit_zero(self):
        rc, out = self._run(_CONTENT / "2026-07-03-tgrera-enforcement-wave")
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "OK  2026-07-03-tgrera-enforcement-wave")

    def test_fixtures_root_exit_one(self):
        rc, out = self._run(_FIXTURES)
        self.assertEqual(rc, 1)
        # Every intended code appears on the right slug line.
        expect = {
            "2026-07-03-missing-line": "missing-flywheel-line",
            "2026-07-03-malformed-query": "malformed-query",
            "2026-07-03-wrong-medium": "wrong-medium",
            "2026-07-03-campaign-mismatch": "campaign-mismatch",
            "2026-07-03-unknown-source": "unknown-source",
            "2026-07-03-absent-source": "unknown-source",
        }
        lines = {ln.split()[1]: ln for ln in out.splitlines() if ln.startswith("FAIL")}
        for slug, code in expect.items():
            self.assertIn(slug, lines)
            self.assertIn(code, lines[slug])
        self.assertIn("OK  2026-07-03-valid-asset", out)

    def test_lexicographic_order(self):
        rc, out = self._run(_FIXTURES)
        slugs = [ln.split()[1] for ln in out.splitlines()]
        self.assertEqual(slugs, sorted(slugs))

    def test_determinism(self):
        _, a = self._run(_FIXTURES)
        _, b = self._run(_FIXTURES)
        self.assertEqual(a, b)


class TestCliPrecondition(unittest.TestCase):
    def test_nonexistent_path(self):
        with self.assertRaises(verify_utm.PreconditionError):
            verify_utm.resolve_targets(str(_CONTENT / "does-not-exist"))

    def test_empty_root(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(verify_utm.PreconditionError):
                verify_utm.resolve_targets(d)


class TestSubprocessBehaviour(unittest.TestCase):
    """Exercise the CLI as a real subprocess (exit codes + stderr/stdout)."""

    def _cli(self, *args):
        return subprocess.run(
            [sys.executable, str(_VERIFY), *args],
            capture_output=True, text=True, cwd=str(_REPO_ROOT))

    def test_content_exit_zero(self):
        r = self._cli("content")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_fixtures_exit_one(self):
        r = self._cli("tools/marketing-loops/fixtures")
        self.assertEqual(r.returncode, 1)

    def test_nonexistent_exit_two_stderr_only(self):
        r = self._cli("content/does-not-exist")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")
        self.assertIn("ERROR", r.stderr)

    def test_import_utm_no_stdout(self):
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, 'tools/marketing-loops'); "
             "import utm; assert utm.CHANNEL_SOURCE_MAP"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "")

    def test_no_network_or_wallclock_imports(self):
        # Parse via AST so that documentation prose in module docstrings does
        # not false-positive; assert on real imports and call sites only.
        import ast
        for fname in ("utm.py", "verify_utm.py"):
            tree = ast.parse((_TOOL_DIR / fname).read_text())
            imported = set()
            calls = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(a.name for a in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imported.add(node.module or "")
                elif isinstance(node, ast.Attribute):
                    calls.add(node.attr)
            self.assertNotIn("datetime", imported, fname)
            self.assertNotIn("requests", imported, fname)
            self.assertNotIn("urllib.request", imported, fname)
            self.assertNotIn("socket", imported, fname)
            self.assertNotIn("now", calls, fname)
            self.assertNotIn("urlopen", calls, fname)


if __name__ == "__main__":
    unittest.main()
