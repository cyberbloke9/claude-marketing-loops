"""Unit tests for the Sprint 002 publish gate (contract s3.1 / s9).

Proves each of the four reason codes fires on its dedicated fixture, the
terminal (missing-verdict) vs independent structure, the fixed multi-reason
order, and the real-asset ground truth. Run:

    python3 -m unittest discover -s tools/marketing-loops/tests -v
"""

import sys
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_TOOL_DIR = _TESTS_DIR.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))
import gate  # noqa: E402

_REPO_ROOT = _TOOL_DIR.parent.parent
_FX = _TOOL_DIR / "fixtures" / "publish"
_CONTENT = _REPO_ROOT / "content"


def codes(asset_dir):
    return [r["code"] for r in gate.gate_asset(asset_dir)["reasons"]]


class TestPassingGate(unittest.TestCase):
    def test_pass_three_channels_ok(self):
        r = gate.gate_asset(_FX / "pass-three-channels")
        self.assertTrue(r["ok"])
        self.assertEqual(r["reasons"], [])
        self.assertEqual(r["slug"], "pass-three-channels")

    def test_real_tgrera_passes(self):
        r = gate.gate_asset(_CONTENT / "2026-07-03-tgrera-enforcement-wave")
        self.assertTrue(r["ok"], msg=r["reasons"])
        self.assertEqual(r["reasons"], [])

    def test_populated_needs_review_and_checks_are_ignored(self):
        # tgrera carries a long checks[] and a 3-item needs_review[]; the gate
        # reads ONLY verdict + failed_checks, so it must still be ok.
        r = gate.gate_asset(_CONTENT / "2026-07-03-tgrera-enforcement-wave")
        self.assertTrue(r["ok"])


class TestSingleReasonCodes(unittest.TestCase):
    def test_missing_verdict_absent_file(self):
        self.assertEqual(codes(_FX / "missing-verdict"), ["missing-verdict"])

    def test_missing_verdict_unparseable(self):
        self.assertEqual(codes(_FX / "unparseable-verdict"), ["missing-verdict"])

    def test_verdict_not_pass_fires_alone(self):
        self.assertEqual(codes(_FX / "verdict-fail"), ["verdict-not-pass"])

    def test_failed_checks_nonempty_fires_alone(self):
        # Proves BOTH halves of FAIL-free PASS: verdict is PASS but failed_checks
        # populated still refuses, with failed-checks-nonempty (not verdict-not-pass).
        self.assertEqual(codes(_FX / "failed-checks-nonempty"), ["failed-checks-nonempty"])

    def test_killed_fires_alone(self):
        # killed fixture has a valid PASS verdict, so ONLY killed should fire.
        self.assertEqual(codes(_FX / "killed"), ["killed"])


class TestTerminalAndOrder(unittest.TestCase):
    def test_missing_verdict_is_terminal_for_verdict_branch(self):
        # An absent verdict must NOT additionally emit verdict-not-pass /
        # failed-checks-nonempty. Only missing-verdict + (independently) killed.
        self.assertEqual(codes(_FX / "missing-verdict-and-killed"),
                         ["missing-verdict", "killed"])

    def test_multi_reason_fixed_order(self):
        r = gate.gate_asset(_FX / "missing-verdict-and-killed")
        self.assertFalse(r["ok"])
        self.assertEqual([c["code"] for c in r["reasons"]],
                         ["missing-verdict", "killed"])

    def test_real_hyd_ground_truth(self):
        # Real KILLED asset with no qa-verdict.json -> [missing-verdict, killed].
        r = gate.gate_asset(_CONTENT / "2026-07-03-hyd-premium-vs-budget")
        self.assertFalse(r["ok"])
        self.assertEqual([c["code"] for c in r["reasons"]],
                         ["missing-verdict", "killed"])


class TestKilledMatch(unittest.TestCase):
    def test_qa_pass_line_not_killed(self):
        # tgrera's "QA: PASS" must not false-trip the killed regex.
        r = gate.gate_asset(_CONTENT / "2026-07-03-tgrera-enforcement-wave")
        self.assertNotIn("killed", [c["code"] for c in r["reasons"]])

    def test_lowercase_prose_not_killed(self):
        # hyd's line 25 'killed assets are data' must not match; killed here
        # comes ONLY from the QA: **KILLED** line, alongside missing-verdict.
        r = gate.gate_asset(_CONTENT / "2026-07-03-hyd-premium-vs-budget")
        self.assertEqual([c["code"] for c in r["reasons"]].count("killed"), 1)


class TestPreconditionAndPurity(unittest.TestCase):
    def test_missing_meta_raises(self):
        with self.assertRaises(FileNotFoundError):
            gate.gate_asset(_TOOL_DIR)  # a dir with no meta.md

    def test_gate_writes_nothing(self):
        # Calling the gate must not create any file under the fixture folder.
        before = sorted(p.name for p in (_FX / "missing-verdict").rglob("*"))
        gate.gate_asset(_FX / "missing-verdict")
        after = sorted(p.name for p in (_FX / "missing-verdict").rglob("*"))
        self.assertEqual(before, after)

    def test_message_is_specific(self):
        r = gate.gate_asset(_FX / "verdict-fail")
        msg = r["reasons"][0]["message"]
        self.assertIn("'FAIL'", msg)
        self.assertIn("PASS", msg)


if __name__ == "__main__":
    unittest.main()
