#!/usr/bin/env python3
"""Unit tests for acceptance.py decision logic (contract sprint_005 s3).

These prove the runner's comparison/exit logic in isolation, so a green
end-to-end run cannot be a false positive from broken comparison logic.
The runner's *invocation* of the real CLIs is exercised by the acceptance
run itself (contract s7 step 2), not here.
"""

import ast
import unittest
from pathlib import Path

import sys
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))  # tools/marketing-render/

import acceptance as A  # noqa: E402


NAMED_FIXTURES = {
    "fx-11-word-hook", "fx-truncated-axis", "fx-low-contrast", "fx-missing-source",
    "fx-blank-png", "fx-good-min", "fx-size-lie", "fx-small-headline",
    "fx-out-of-safezone", "fx-blacklist", "fx-no-provenance", "fx-canvas-mismatch",
}


class TestExpectationTable(unittest.TestCase):
    def test_table_has_exactly_the_twelve_named_rows(self):
        names = [r["fixture"] for r in A.EXPECTATIONS]
        self.assertEqual(len(names), 12)
        self.assertEqual(set(names), NAMED_FIXTURES)
        self.assertEqual(len(names), len(set(names)), "no duplicate fixture rows")

    def test_good_min_is_the_positive_control(self):
        good = next(r for r in A.EXPECTATIONS if r["fixture"] == "fx-good-min")
        self.assertEqual(good["expected_exit"], 0)
        self.assertIsNone(good["expected_check_id"])
        self.assertIsNone(good["expected_rule_substring"])

    def test_every_fail_row_has_a_check_and_rule(self):
        for r in A.EXPECTATIONS:
            if r["expected_exit"] == 1:
                self.assertTrue(r["expected_check_id"], r["fixture"])
                self.assertTrue(r["expected_rule_substring"], r["fixture"])

    def test_table_covers_committed_fixtures_on_disk(self):
        # The real committed fixtures dir must be exactly covered.
        self.assertIsNone(A.table_coverage_error(A.FIXTURES_DIR))

    def test_extra_fixture_dir_not_in_table_is_an_error(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            for name in NAMED_FIXTURES:
                os.mkdir(os.path.join(d, name))
            os.mkdir(os.path.join(d, "fx-brand-new-uncovered"))
            err = A.table_coverage_error(d)
            self.assertIsNotNone(err)
            self.assertIn("fx-brand-new-uncovered", err)

    def test_table_row_without_fixture_dir_is_an_error(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            # only 11 of 12 present
            for name in list(NAMED_FIXTURES)[:-1]:
                os.mkdir(os.path.join(d, name))
            err = A.table_coverage_error(d)
            self.assertIsNotNone(err)


class TestPassDetection(unittest.TestCase):
    def test_clean_pass_is_pass(self):
        self.assertTrue(A.verdict_is_pass({"verdict": "PASS", "failed_checks": []}))

    def test_fail_verdict_is_not_pass(self):
        self.assertFalse(A.verdict_is_pass(
            {"verdict": "FAIL", "failed_checks": [{"id": "V4-contrast"}]}))

    def test_pass_verdict_with_lingering_failed_checks_is_not_pass(self):
        self.assertFalse(A.verdict_is_pass(
            {"verdict": "PASS", "failed_checks": [{"id": "V4-contrast"}]}))

    def test_none_is_not_pass(self):
        self.assertFalse(A.verdict_is_pass(None))


class TestFailDetection(unittest.TestCase):
    def _verdict(self, cid, rule):
        return {"verdict": "FAIL",
                "failed_checks": [{"id": cid, "detail": "x", "rule": rule}]}

    def test_named_check_with_rule_matches(self):
        v = self._verdict("V7-hook-words", "qa-checklist.md §Carousel")
        self.assertTrue(A.failed_check_matches(v, "V7-hook-words", "qa-checklist.md §Carousel"))

    def test_wrong_check_id_does_not_match(self):
        # a FAIL on the wrong check (V4 when V7 expected) must be rejected.
        v = self._verdict("V4-contrast", "brand-kit.md §3")
        self.assertFalse(A.failed_check_matches(v, "V7-hook-words", "qa-checklist.md §Carousel"))

    def test_right_check_wrong_rule_does_not_match(self):
        v = self._verdict("V7-hook-words", "some-other-rule")
        self.assertFalse(A.failed_check_matches(v, "V7-hook-words", "qa-checklist.md §Carousel"))

    def test_substring_rule_match(self):
        v = self._verdict("V4-contrast", "brand-kit.md §3 (contrast tokens)")
        self.assertTrue(A.failed_check_matches(v, "V4-contrast", "brand-kit.md §3"))

    def test_named_check_among_several(self):
        v = {"verdict": "FAIL", "failed_checks": [
            {"id": "V3-ink", "rule": "spec §5.2 V3"},
            {"id": "V4-contrast", "rule": "brand-kit.md §3"},
        ]}
        self.assertTrue(A.failed_check_matches(v, "V4-contrast", "brand-kit.md §3"))


class TestEvaluateRow(unittest.TestCase):
    def test_pass_row_met(self):
        row = {"expected_exit": 0, "expected_check_id": None, "expected_rule_substring": None}
        ok, _ = A.evaluate_row(row, 0, {"verdict": "PASS", "failed_checks": []})
        self.assertTrue(ok)

    def test_pass_row_wrong_exit_unmet(self):
        row = {"expected_exit": 0, "expected_check_id": None, "expected_rule_substring": None}
        ok, _ = A.evaluate_row(row, 1, {"verdict": "FAIL", "failed_checks": [{"id": "x"}]})
        self.assertFalse(ok)

    def test_pass_expected_but_fail_verdict_unmet(self):
        # exit 0 but verdict is not clean PASS
        row = {"expected_exit": 0, "expected_check_id": None, "expected_rule_substring": None}
        ok, _ = A.evaluate_row(row, 0, {"verdict": "FAIL", "failed_checks": [{"id": "x"}]})
        self.assertFalse(ok)

    def test_fail_row_named_check_met(self):
        row = {"expected_exit": 1, "expected_check_id": "V7-hook-words",
               "expected_rule_substring": "qa-checklist.md §Carousel"}
        v = {"verdict": "FAIL", "failed_checks": [
            {"id": "V7-hook-words", "rule": "qa-checklist.md §Carousel"}]}
        ok, _ = A.evaluate_row(row, 1, v)
        self.assertTrue(ok)

    def test_fail_row_wrong_check_unmet(self):
        # right exit code, wrong check -> the gate must reject "some FAIL".
        row = {"expected_exit": 1, "expected_check_id": "V7-hook-words",
               "expected_rule_substring": "qa-checklist.md §Carousel"}
        v = {"verdict": "FAIL", "failed_checks": [
            {"id": "V4-contrast", "rule": "brand-kit.md §3"}]}
        ok, detail = A.evaluate_row(row, 1, v)
        self.assertFalse(ok)
        self.assertIn("V7-hook-words", detail)

    def test_fail_row_wrong_exit_unmet(self):
        row = {"expected_exit": 1, "expected_check_id": "V7-hook-words",
               "expected_rule_substring": "qa-checklist.md §Carousel"}
        ok, _ = A.evaluate_row(row, 0, {"verdict": "PASS", "failed_checks": []})
        self.assertFalse(ok)


class TestPurity(unittest.TestCase):
    def test_no_network_imports(self):
        path = A.SCRIPT_DIR / "acceptance.py"
        tree = ast.parse(path.read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
        network = {"socket", "urllib", "http", "requests", "ssl", "httplib", "ftplib"}
        self.assertEqual(network & imports, set(),
                         "acceptance.py must not import network modules")


if __name__ == "__main__":
    unittest.main()
