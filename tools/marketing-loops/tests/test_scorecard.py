#!/usr/bin/env python3
"""Unit + CLI tests for the Sprint-005 scorecard compiler (scorecard.py).

Covers the golden-Markdown byte-equality of all six cases (full / partial /
empty / wrong-utm / wrr-partial / unmatched), the B-A5 WRR no-partial-sum
critical edge, zero-vs-blank craft cells, A/B single-week semantics, exit codes
(inherited corrupt-CSV rejection with NO file written, bad queue, bad week,
--out/--stdout exclusivity), determinism, import safety, and grep-clean for
wall-clock / network.
"""

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_TOOL = _HERE.parent
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))
import scorecard  # noqa: E402

_FX = _TOOL / "fixtures" / "metrics"
_EXPECTED = _FX / "expected"
_SCRIPT = _TOOL / "scorecard.py"


def _run_cli(argv):
    """Invoke scorecard.main(argv) capturing (exit, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = scorecard.main(argv)
    return code, out.getvalue(), err.getvalue()


class GoldenMarkdownTests(unittest.TestCase):
    """Byte-for-byte golden equality for each documented case."""

    def _assert_golden(self, argv, golden_name):
        code, out, err = _run_cli(argv + ["--stdout"])
        self.assertEqual(code, 0, err)
        expected = (_EXPECTED / golden_name).read_text(encoding="utf-8")
        self.assertEqual(out, expected)

    def test_full(self):
        self._assert_golden([
            "--week", "2026-W27",
            "--instagram", str(_FX / "full/ig.csv"),
            "--youtube", str(_FX / "full/yt.csv"),
            "--linkedin", str(_FX / "full/li.csv"),
            "--site", str(_FX / "full/site.csv"),
            "--content-dir", str(_FX / "full/content"),
            "--queue", str(_FX / "full/queue.json"),
        ], "full.md")

    def test_partial_ig_only(self):
        self._assert_golden([
            "--week", "2026-W27",
            "--instagram", str(_FX / "full/ig.csv"),
            "--content-dir", str(_FX / "full/content"),
        ], "partial.md")

    def test_empty(self):
        self._assert_golden([
            "--week", "2026-W27",
            "--content-dir", str(_FX / "full/content"),
        ], "empty.md")

    def test_wrong_utm(self):
        self._assert_golden([
            "--week", "2026-W27",
            "--instagram", str(_FX / "wrong-utm/ig.csv"),
            "--content-dir", str(_FX / "wrong-utm/content"),
        ], "wrong-utm.md")

    def test_wrr_partial(self):
        self._assert_golden([
            "--week", "2026-W27",
            "--site", str(_FX / "wrr-partial/site.csv"),
            "--content-dir", str(_FX / "full/content"),
        ], "wrr-partial.md")

    def test_unmatched(self):
        self._assert_golden([
            "--week", "2026-W27",
            "--instagram", str(_FX / "unmatched/ig.csv"),
            "--content-dir", str(_FX / "full/content"),
        ], "unmatched.md")


class WrrCriticalEdgeTests(unittest.TestCase):
    """B-A5: WRR filled only when all three present; else blank + no partial sum."""

    def test_full_wrr_is_347(self):
        code, out, _ = _run_cli([
            "--week", "2026-W27",
            "--instagram", str(_FX / "full/ig.csv"),
            "--youtube", str(_FX / "full/yt.csv"),
            "--linkedin", str(_FX / "full/li.csv"),
            "--site", str(_FX / "full/site.csv"),
            "--content-dir", str(_FX / "full/content"),
            "--queue", str(_FX / "full/queue.json"),
            "--stdout",
        ])
        self.assertEqual(code, 0)
        wrr_line = [ln for ln in out.splitlines() if "WRR — Weekly" in ln][0]
        self.assertIn("| 347 |", wrr_line)

    def test_wrr_partial_blank_no_partial_sum(self):
        code, out, _ = _run_cli([
            "--week", "2026-W27",
            "--site", str(_FX / "wrr-partial/site.csv"),
            "--content-dir", str(_FX / "full/content"),
            "--stdout",
        ])
        self.assertEqual(code, 0)
        wrr_line = [ln for ln in out.splitlines() if "WRR — Weekly" in ln][0]
        # This-week cell blank.
        self.assertRegex(wrr_line, r"social\)\s*\|\s*\|\s*\|\s*\|\s*$")
        # The forbidden partial sum 95 + 52 = 147 must appear NOWHERE.
        self.assertNotIn("147", out)
        # The absent component is named.
        self.assertIn("WRR component 'returning_viewers' absent", out)
        # The two present components are not surfaced as a running total.
        self.assertNotIn("WRR component 'digest_opens' absent", out)

    def test_no_site_lists_all_three_components(self):
        code, out, _ = _run_cli([
            "--week", "2026-W27",
            "--content-dir", str(_FX / "full/content"),
            "--stdout",
        ])
        self.assertEqual(code, 0)
        for comp in ("returning_viewers", "digest_opens",
                     "returning_visitors_social"):
            self.assertIn("WRR component '{}' absent".format(comp), out)


class CraftCellTests(unittest.TestCase):
    """B-A7: blank != 0; unmatched flagged; hook# blank-not-invented."""

    def test_zero_renders_zero(self):
        code, out, _ = _run_cli([
            "--week", "2026-W27",
            "--instagram", str(_FX / "zero-cell/ig.csv"),
            "--content-dir", str(_FX / "full/content"),
            "--stdout",
        ])
        self.assertEqual(code, 0)
        row = [ln for ln in out.splitlines()
               if "tgrera-enforcement-wave | instagram" in ln][0]
        self.assertEqual(row,
                         "| 2026-07-03-tgrera-enforcement-wave | instagram "
                         "| 31 | 26 | 4 | 0 | 11 |")
        self.assertNotIn("craft Clicks absent", out)

    def test_blank_renders_blank_and_listed(self):
        code, out, _ = _run_cli([
            "--week", "2026-W27",
            "--instagram", str(_FX / "blank-cell/ig.csv"),
            "--content-dir", str(_FX / "full/content"),
            "--stdout",
        ])
        self.assertEqual(code, 0)
        row = [ln for ln in out.splitlines()
               if "tgrera-enforcement-wave | instagram" in ln][0]
        self.assertEqual(row,
                         "| 2026-07-03-tgrera-enforcement-wave | instagram "
                         "| 31 | 26 | 4 | | 11 |")
        self.assertEqual(
            out.count("craft Clicks absent for "
                      "2026-07-03-tgrera-enforcement-wave (instagram)"), 1)

    def test_unmatched_flagged(self):
        code, out, _ = _run_cli([
            "--week", "2026-W27",
            "--instagram", str(_FX / "unmatched/ig.csv"),
            "--content-dir", str(_FX / "full/content"),
            "--stdout",
        ])
        self.assertEqual(code, 0)
        self.assertIn("| ghost-campaign-no-asset (unmatched) | instagram |", out)
        self.assertIn("unmatched-campaign: ghost-campaign-no-asset", out)


class AbTableTests(unittest.TestCase):
    """B-A8: single-week semantics — buckets from queue, verdict blank."""

    def test_full_buckets_from_queue(self):
        code, out, _ = _run_cli([
            "--week", "2026-W27",
            "--instagram", str(_FX / "full/ig.csv"),
            "--youtube", str(_FX / "full/yt.csv"),
            "--linkedin", str(_FX / "full/li.csv"),
            "--site", str(_FX / "full/site.csv"),
            "--content-dir", str(_FX / "full/content"),
            "--queue", str(_FX / "full/queue.json"),
            "--stdout",
        ])
        self.assertEqual(code, 0)
        self.assertIn("| instagram | | 51 | |", out)   # evening bucket
        self.assertIn("| youtube | 30 | | |", out)      # morning bucket
        self.assertIn("| linkedin | | 67 | |", out)     # evening bucket
        # Every verdict is blank + listed.
        for ch in ("instagram", "youtube", "linkedin"):
            self.assertIn("posting-time A/B verdict for {} needs cross-week "
                          "comparison".format(ch), out)

    def test_no_queue_all_blank_single_line(self):
        code, out, _ = _run_cli([
            "--week", "2026-W27",
            "--instagram", str(_FX / "full/ig.csv"),
            "--content-dir", str(_FX / "full/content"),
            "--stdout",
        ])
        self.assertEqual(code, 0)
        self.assertIn("| instagram | | | |", out)
        self.assertEqual(
            out.count("publish queue not provided "
                      "(posting-time A/B table blank)"), 1)
        # No per-channel verdict spam when the queue is absent.
        self.assertNotIn("A/B verdict for", out)


class DecisionsTests(unittest.TestCase):
    """B-A9: hook ranking filled only with >=2 qualifying assets."""

    def test_full_hook_ranking(self):
        code, out, _ = _run_cli([
            "--week", "2026-W27",
            "--instagram", str(_FX / "full/ig.csv"),
            "--youtube", str(_FX / "full/yt.csv"),
            "--linkedin", str(_FX / "full/li.csv"),
            "--site", str(_FX / "full/site.csv"),
            "--content-dir", str(_FX / "full/content"),
            "--queue", str(_FX / "full/queue.json"),
            "--stdout",
        ])
        self.assertEqual(code, 0)
        self.assertIn("top hook #11 (94 clicks); "
                      "retire-candidate hook #7 (54 clicks)", out)
        self.assertNotIn("hook ranking needs", out)

    def test_partial_hook_ranking_blank(self):
        code, out, _ = _run_cli([
            "--week", "2026-W27",
            "--instagram", str(_FX / "full/ig.csv"),
            "--content-dir", str(_FX / "full/content"),
            "--stdout",
        ])
        self.assertEqual(code, 0)
        # IG-only has 2 assets with clicks + hooks -> ranking still fills.
        self.assertIn("top hook #", out)


class DeterminismTests(unittest.TestCase):

    def test_two_runs_identical(self):
        argv = [
            "--week", "2026-W27",
            "--site", str(_FX / "full/site.csv"),
            "--content-dir", str(_FX / "full/content"),
            "--stdout",
        ]
        _, out1, _ = _run_cli(argv)
        _, out2, _ = _run_cli(argv)
        self.assertEqual(out1, out2)

    def test_flag_reorder_stable(self):
        base = _run_cli([
            "--week", "2026-W27",
            "--instagram", str(_FX / "full/ig.csv"),
            "--youtube", str(_FX / "full/yt.csv"),
            "--linkedin", str(_FX / "full/li.csv"),
            "--site", str(_FX / "full/site.csv"),
            "--content-dir", str(_FX / "full/content"),
            "--queue", str(_FX / "full/queue.json"),
            "--stdout",
        ])[1]
        reordered = _run_cli([
            "--week", "2026-W27",
            "--youtube", str(_FX / "full/yt.csv"),
            "--site", str(_FX / "full/site.csv"),
            "--instagram", str(_FX / "full/ig.csv"),
            "--linkedin", str(_FX / "full/li.csv"),
            "--queue", str(_FX / "full/queue.json"),
            "--content-dir", str(_FX / "full/content"),
            "--stdout",
        ])[1]
        self.assertEqual(base, reordered)

    def test_trailing_newline_single(self):
        _, out, _ = _run_cli([
            "--week", "2026-W27",
            "--content-dir", str(_FX / "full/content"),
            "--stdout",
        ])
        self.assertTrue(out.endswith("\n"))
        self.assertFalse(out.endswith("\n\n"))


class ExitCodeTests(unittest.TestCase):
    """Corrupt CSV / bad queue / bad week / --out+--stdout -> exit 2, no file."""

    def test_bad_week(self):
        for bad in ("2026-27", "26-W27", "notaweek"):
            code, _, err = _run_cli([
                "--week", bad,
                "--content-dir", str(_FX / "full/content"),
                "--stdout",
            ])
            self.assertEqual(code, 2, bad)
            self.assertIn("--week", err)

    def test_out_and_stdout_mutually_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "x.md"
            code, _, err = _run_cli([
                "--week", "2026-W27",
                "--content-dir", str(_FX / "full/content"),
                "--out", str(out), "--stdout",
            ])
        self.assertEqual(code, 2)
        self.assertIn("mutually exclusive", err)

    def test_corrupt_csv_no_file_written(self):
        for case in ("truncated", "wrong-header", "wrong-colcount",
                     "non-numeric", "blank-join"):
            csv_dir = _FX / case
            site = csv_dir / "site.csv"
            if not site.is_file():
                site = csv_dir / "ig.csv"
            flag = "--site" if site.name == "site.csv" else "--instagram"
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "2026-W27.md"
                code, sout, err = _run_cli([
                    "--week", "2026-W27",
                    flag, str(site),
                    "--content-dir", str(_FX / "full/content"),
                    "--out", str(out),
                ])
                self.assertEqual(code, 2, case)
                self.assertEqual(sout, "", case)
                self.assertTrue(err.strip(), case)
                self.assertFalse(out.exists(),
                                 "{}: no scorecard must be written".format(case))

    def test_bad_queue_path(self):
        code, _, err = _run_cli([
            "--week", "2026-W27",
            "--content-dir", str(_FX / "full/content"),
            "--queue", "/no/such/queue.json",
            "--stdout",
        ])
        self.assertEqual(code, 2)
        self.assertIn("--queue file not found", err)

    def test_malformed_queue_json(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "queue.json"
            bad.write_text("{ not valid json", encoding="utf-8")
            out = Path(td) / "sc.md"
            code, sout, err = _run_cli([
                "--week", "2026-W27",
                "--content-dir", str(_FX / "full/content"),
                "--queue", str(bad), "--out", str(out),
            ])
            self.assertEqual(code, 2)
            self.assertEqual(sout, "")
            self.assertTrue(err.strip())
            self.assertFalse(out.exists())

    def test_missing_source_path(self):
        code, _, err = _run_cli([
            "--week", "2026-W27",
            "--site", "/no/such/site.csv",
            "--content-dir", str(_FX / "full/content"),
            "--stdout",
        ])
        self.assertEqual(code, 2)
        self.assertIn("not found", err)


class WriteBehaviorTests(unittest.TestCase):

    def test_default_out_and_explicit_out(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "sub" / "2026-W27.md"
            code, sout, _ = _run_cli([
                "--week", "2026-W27",
                "--site", str(_FX / "full/site.csv"),
                "--content-dir", str(_FX / "full/content"),
                "--out", str(out),
            ])
            self.assertEqual(code, 0)
            self.assertTrue(out.is_file())
            self.assertIn(str(out), sout)  # path printed
            text = out.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# Weekly Scorecard — 2026-W27"))


class SafetyTests(unittest.TestCase):

    def test_import_is_side_effect_free(self):
        proc = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, {!r}); import scorecard; "
             "print('ok')".format(str(_TOOL))],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "ok")

    def test_no_wallclock_or_network_tokens(self):
        src = _SCRIPT.read_text(encoding="utf-8")
        # Strip the module docstring's prose mentions before scanning code.
        for token in ("datetime.now", "urlopen", "requests", "socket.",
                      "urllib.request"):
            self.assertNotIn(token, src, token)


if __name__ == "__main__":
    unittest.main()
