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


class TestFacebookChannel(unittest.TestCase):
    """spec B35: facebook is ordinal 3; slot_for must not KeyError."""

    def test_facebook_w27_morning(self):
        # ordinal 3: bucket = morning if (WW + 3) % 2 == 0. WW=27 -> (30)%2==0.
        self.assertEqual(schedule.slot_for("2026-W27", "facebook"),
                         "2026-W27/morning/10:00")

    def test_facebook_w28_evening(self):
        # (28+3)%2 == 1 -> evening.
        self.assertEqual(schedule.slot_for("2026-W28", "facebook"),
                         "2026-W28/evening/19:00")

    def test_facebook_no_keyerror_either_bucket(self):
        for wk in ("2026-W27", "2026-W28"):
            self.assertTrue(schedule.slot_for(wk, "facebook").startswith(wk + "/"))

    def test_original_three_unchanged_after_facebook(self):
        # Ordinals 0/1/2 preserved -> byte-identical slots (contract s3.2 table).
        self.assertEqual(schedule.slot_for("2026-W27", "instagram"),
                         "2026-W27/evening/18:00")
        self.assertEqual(schedule.slot_for("2026-W27", "youtube"),
                         "2026-W27/morning/11:00")
        self.assertEqual(schedule.slot_for("2026-W27", "linkedin"),
                         "2026-W27/evening/17:30")


if __name__ == "__main__":
    unittest.main()
