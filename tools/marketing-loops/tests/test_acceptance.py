#!/usr/bin/env python3
"""Unit tests for the Sprint-006 cross-gap acceptance runner's PURE decision
logic, isolated from subprocess timing, plus a smoke test that the runner exits 0.

The pure functions are the runner's judgement: a wrong-reason nonzero exit must
NOT satisfy a refusal row (attack #2), coverage must catch stray/deleted fixtures
(attack #8), and the seam assertion must be driven by the queue slot (attack #6).
"""

import subprocess
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_TOOL = _HERE.parent
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))

import acceptance as A  # noqa: E402


class ReasonRowTests(unittest.TestCase):
    def test_exit_and_reason_match(self):
        ok, _ = A.reason_row_ok(1, ["[killed]"], 1, "REFUSED\n  [killed] marker")
        self.assertTrue(ok)

    def test_wrong_exit_fails(self):
        ok, detail = A.reason_row_ok(1, ["[killed]"], 2, "  [killed] marker")
        self.assertFalse(ok)
        self.assertIn("exit 2 != expected 1", detail)

    def test_right_exit_wrong_reason_fails(self):
        # attack #2: a nonzero exit for the WRONG reason does not satisfy the row.
        ok, detail = A.reason_row_ok(1, ["[killed]"], 1, "  [verdict-not-pass] nope")
        self.assertFalse(ok)
        self.assertIn("[killed]", detail)

    def test_all_reasons_required(self):
        ok, _ = A.reason_row_ok(1, ["wrong-medium", "unknown-source"], 1,
                                "wrong-medium, unknown-source — ...")
        self.assertTrue(ok)
        ok2, _ = A.reason_row_ok(1, ["wrong-medium", "unknown-source"], 1, "wrong-medium only")
        self.assertFalse(ok2)


class GoldenAndInvariantTests(unittest.TestCase):
    def test_golden_byte_equal(self):
        self.assertTrue(A.golden_ok("abc", "abc")[0])
        self.assertFalse(A.golden_ok("abc", "abd")[0])

    def test_forbidden_partial_sum(self):
        # attack #5: the partial sum 147 must be absent.
        ok, detail = A.content_invariants_ok("WRR blank; component absent",
                                             required=["WRR", "absent"],
                                             forbidden=["147"])
        self.assertTrue(ok)
        bad, bdetail = A.content_invariants_ok("WRR = 147", forbidden=["147"])
        self.assertFalse(bad)
        self.assertIn("147", bdetail)

    def test_required_absent_fails(self):
        ok, _ = A.content_invariants_ok("nothing here", required=["expected-token"])
        self.assertFalse(ok)


class PackageInvariantTests(unittest.TestCase):
    def _pkg(self, **over):
        base = {
            "channel": "instagram",
            "utm_link": "https://x/y?utm_source=instagram&utm_medium=social&utm_campaign=slug",
            "caption": "body\n\nhttps://x/y?utm_source=instagram&utm_medium=social&utm_campaign=slug",
            "attachments": ["a/one.png", "b/two.png"],
        }
        base.update(over)
        return base

    def test_valid_package(self):
        ok, _ = A.package_invariants_ok(self._pkg(), "instagram", "slug", ["one.png", "two.png"])
        self.assertTrue(ok)

    def test_wrong_source_in_link(self):
        ok, d = A.package_invariants_ok(
            self._pkg(utm_link="https://x/y?utm_source=youtube&utm_medium=social&utm_campaign=slug"),
            "instagram", "slug", ["one.png", "two.png"])
        self.assertFalse(ok)

    def test_caption_not_ending_with_link(self):
        ok, d = A.package_invariants_ok(self._pkg(caption="body only"),
                                        "instagram", "slug", ["one.png", "two.png"])
        self.assertFalse(ok)
        self.assertIn("caption", d)

    def test_attachment_order_mismatch(self):
        ok, d = A.package_invariants_ok(self._pkg(), "instagram", "slug", ["two.png", "one.png"])
        self.assertFalse(ok)


class SeamTests(unittest.TestCase):
    AB = ("| Channel | Morning slot perf | Evening (3–8pm IST) perf | Verdict so far |\n"
          "|---|---|---|---|\n"
          "| instagram | | 51 | |\n"
          "| youtube | | | |\n")

    def test_bucket_from_slot(self):
        self.assertEqual(A.bucket_from_slot("2026-W27/evening/18:00"), "evening")
        self.assertEqual(A.bucket_from_slot("2026-W27/morning/09:00"), "morning")

    def test_parse_ab_row(self):
        self.assertEqual(A.parse_ab_row(self.AB, "instagram"), ("", "51"))
        self.assertEqual(A.parse_ab_row(self.AB, "youtube"), ("", ""))

    def test_seam_evening_bucket_matches(self):
        ok, _ = A.seam_ab_ok(self.AB, "instagram", "2026-W27/evening/18:00")
        self.assertTrue(ok)

    def test_seam_fails_when_queue_bucket_contradicts_column(self):
        # attack #6: if the queue says morning but the column is evening, FAIL.
        ok, d = A.seam_ab_ok(self.AB, "instagram", "2026-W27/morning/09:00")
        self.assertFalse(ok)
        self.assertIn("morning", d)

    def test_seam_morning_when_column_is_morning(self):
        ab = self.AB.replace("| instagram | | 51 | |", "| instagram | 51 | | |")
        ok, _ = A.seam_ab_ok(ab, "instagram", "2026-W27/morning/09:00")
        self.assertTrue(ok)


class CoverageTests(unittest.TestCase):
    def test_exact_coverage(self):
        self.assertIsNone(A.table_coverage_error(["a", "b"], ["a", "b"], "fam"))

    def test_stray_on_disk_fixture(self):
        # attack #8: a fixture dir not named by the table is an error.
        msg = A.table_coverage_error(["a", "b", "stray"], ["a", "b"], "fam")
        self.assertIn("stray", msg)

    def test_deleted_named_fixture(self):
        msg = A.table_coverage_error(["a"], ["a", "gone"], "fam")
        self.assertIn("gone", msg)

    def test_real_tables_cover_disk(self):
        # The committed tables must exactly cover the on-disk fixtures right now.
        self.assertEqual(A.coverage_errors(), [])


class SmokeTest(unittest.TestCase):
    def test_runner_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, str(_TOOL / "acceptance.py")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(proc.returncode, 0,
                         "acceptance runner did not exit 0:\n{}\n{}".format(
                             proc.stdout, proc.stderr))
        self.assertIn("ACCEPTANCE: PASS", proc.stdout)


if __name__ == "__main__":
    unittest.main()
