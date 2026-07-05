"""Unit tests for the Sprint 004 assetmap module (contract s3.3)."""

import sys
import tempfile
import unittest
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parent.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))
import assetmap  # noqa: E402
import utm       # noqa: E402

_FX = _TOOL_DIR / "fixtures" / "metrics"


class TestHookNumber(unittest.TestCase):
    def test_first_hash_token(self):
        self.assertEqual(
            assetmap.hook_number_from_meta("Hook: hook-bank #11 adapted"), 11)

    def test_first_of_many(self):
        self.assertEqual(
            assetmap.hook_number_from_meta("Hook: bank #13 then #21"), 13)

    def test_no_hook_line(self):
        self.assertIsNone(assetmap.hook_number_from_meta("Channels: IG\n"))

    def test_hook_line_without_number(self):
        self.assertIsNone(assetmap.hook_number_from_meta("Hook: no number here"))


class TestBuildAssetMap(unittest.TestCase):
    def test_full_fixture(self):
        m = assetmap.build_asset_map(_FX / "full" / "content")
        self.assertEqual(set(m), {"tgrera-enforcement-wave",
                                  "rera-refund-timeline"})
        rec = m["tgrera-enforcement-wave"]
        self.assertEqual(rec["slug"], "2026-07-03-tgrera-enforcement-wave")
        self.assertEqual(rec["hook_number"], 11)
        self.assertTrue(rec["utm_valid"])
        self.assertEqual(rec["utm_violations"], [])

    def test_join_key_is_from_utm_module(self):
        m = assetmap.build_asset_map(_FX / "full" / "content")
        for record in m.values():
            self.assertEqual(record["campaign"],
                             utm.campaign_from_slug(record["slug"]))

    def test_wrong_utm_asset_flagged(self):
        m = assetmap.build_asset_map(_FX / "wrong-utm" / "content")
        rec = m["bad-utm-asset"]
        self.assertFalse(rec["utm_valid"])
        self.assertIn(utm.CODE_WRONG_MEDIUM, rec["utm_violations"])

    def test_collision_raises(self):
        root = Path(tempfile.mkdtemp())
        for slug in ("2026-07-03-dup-topic", "2026-07-10-dup-topic"):
            d = root / slug
            d.mkdir()
            (d / "meta.md").write_text(
                "Hook: #1\nFlywheel target: https://x?utm_source=instagram"
                "&utm_medium=social&utm_campaign=dup-topic\n", encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            assetmap.build_asset_map(root)
        self.assertIn("collision", str(ctx.exception))

    def test_non_meta_subdir_skipped(self):
        root = Path(tempfile.mkdtemp())
        (root / "not-an-asset").mkdir()
        (root / "TEMPLATE.md").write_text("x", encoding="utf-8")
        self.assertEqual(assetmap.build_asset_map(root), {})


class TestImportSafety(unittest.TestCase):
    def test_import_is_silent(self):
        import subprocess
        repo = _TOOL_DIR.parent.parent
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0,'tools/marketing-loops'); import assetmap"],
            capture_output=True, text=True, cwd=str(repo))
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.stderr, "")


if __name__ == "__main__":
    unittest.main()
