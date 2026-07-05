"""Unit tests for the Sprint 003 schedule module (contract s3.2)."""

import sys
import unittest
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parent.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))
import schedule  # noqa: E402
import utm       # noqa: E402


class TestW27GroundTruth(unittest.TestCase):
    """Reproduce the contract s3.2 worked table exactly (WW=27)."""

    def test_instagram(self):
        self.assertEqual(schedule.slot_for("2026-W27", "instagram"),
                         "2026-W27/evening/18:00")

    def test_youtube(self):
        self.assertEqual(schedule.slot_for("2026-W27", "youtube"),
                         "2026-W27/morning/11:00")

    def test_linkedin(self):
        self.assertEqual(schedule.slot_for("2026-W27", "linkedin"),
                         "2026-W27/evening/17:30")


class TestFormula(unittest.TestCase):
    def test_bucket_alternates_by_week(self):
        # instagram ordinal 0: even WW -> morning, odd WW -> evening.
        self.assertEqual(schedule.bucket_for("2026-W28", "instagram"), "morning")
        self.assertEqual(schedule.bucket_for("2026-W29", "instagram"), "evening")

    def test_slot_string_format(self):
        slot = schedule.slot_for("2026-W28", "instagram")
        week, bucket, time = slot.split("/")
        self.assertEqual(week, "2026-W28")
        self.assertEqual(bucket, "morning")
        self.assertEqual(time, "09:00")

    def test_deterministic(self):
        self.assertEqual(schedule.slot_for("2026-W05", "linkedin"),
                         schedule.slot_for("2026-W05", "linkedin"))


class TestValidation(unittest.TestCase):
    def test_bad_week_raises(self):
        for bad in ("2026-Q3", "2026-W2", "26-W02", "2026W02", ""):
            with self.assertRaises(ValueError):
                schedule.slot_for(bad, "instagram")

    def test_unknown_channel_raises(self):
        with self.assertRaises(ValueError):
            schedule.slot_for("2026-W27", "twitter")


class TestNoFork(unittest.TestCase):
    def test_channel_order_is_derived_from_utm(self):
        self.assertEqual(schedule.CANONICAL_CHANNELS,
                         tuple(utm.CHANNEL_SOURCE_MAP.keys()))


class TestImportSafety(unittest.TestCase):
    def test_import_is_silent(self):
        import subprocess
        repo = _TOOL_DIR.parent.parent
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0,'tools/marketing-loops'); import schedule"],
            capture_output=True, text=True, cwd=str(repo))
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.stderr, "")


if __name__ == "__main__":
    unittest.main()
