"""Integration tests for the Sprint 002 enqueue CLI (contract s3.3 / s9).

Runs enqueue.py as a subprocess (mirroring Sprint 001's CLI tests) to assert
exit codes, stdout/stderr content, on-disk queue JSON, idempotency, no-regress,
and the two negatives the Evaluator probes: NO write on refusal, and EMPTY
stdout on usage errors.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_TOOL_DIR = _TESTS_DIR.parent
_REPO_ROOT = _TOOL_DIR.parent.parent
_ENQUEUE = _TOOL_DIR / "enqueue.py"
_FX = _TOOL_DIR / "fixtures" / "publish"
_CONTENT = _REPO_ROOT / "content"
_TGRERA = _CONTENT / "2026-07-03-tgrera-enforcement-wave"
_HYD = _CONTENT / "2026-07-03-hyd-premium-vs-budget"


def enqueue(asset_dir, queue_path, week="2026-W27", extra=None):
    argv = [sys.executable, str(_ENQUEUE), str(asset_dir), "--week", week,
            "--queue", str(queue_path)]
    if extra:
        argv = [sys.executable, str(_ENQUEUE)] + extra
    return subprocess.run(argv, capture_output=True, text=True, cwd=str(_REPO_ROOT))


class TestSuccessPath(unittest.TestCase):
    def test_tgrera_enqueues_three_rows(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            r = enqueue(_TGRERA, qp)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            data = json.loads(qp.read_text())
            self.assertEqual(data["schema_version"], "1")
            self.assertEqual(len(data["rows"]), 3)
            self.assertEqual(sorted(row["channel"] for row in data["rows"]),
                             ["instagram", "linkedin", "youtube"])
            for row in data["rows"]:
                self.assertEqual(row["state"], "queued")
                self.assertEqual(row["week"], "2026-W27")
                for k in ("schedule_slot", "package_path", "posted_date", "permalink"):
                    self.assertIsNone(row[k])

    def test_idempotent_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            r1 = enqueue(_TGRERA, qp)
            first = qp.read_bytes()
            out1 = r1.stdout
            r2 = enqueue(_TGRERA, qp)
            self.assertEqual(qp.read_bytes(), first)  # byte-identical
            self.assertEqual(r2.stdout, out1)         # identical stdout
            self.assertEqual(len(json.loads(qp.read_text())["rows"]), 3)  # no dupes

    def test_one_channel_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            r = enqueue(_FX / "pass-one-channel", qp)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            self.assertEqual(len(json.loads(qp.read_text())["rows"]), 1)

    def test_no_regress_posted_row(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            seed = {"schema_version": "1", "rows": [{
                "slug": _TGRERA.name, "channel": "instagram", "state": "posted",
                "week": "2026-W27", "schedule_slot": None, "package_path": None,
                "posted_date": "2026-07-04", "permalink": "https://ig.example/p/1",
            }]}
            qp.write_text(json.dumps(seed))
            r = enqueue(_TGRERA, qp)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            by = {(x["slug"], x["channel"]): x for x in json.loads(qp.read_text())["rows"]}
            ig = by[(_TGRERA.name, "instagram")]
            self.assertEqual(ig["state"], "posted")
            self.assertEqual(ig["posted_date"], "2026-07-04")
            self.assertEqual(ig["permalink"], "https://ig.example/p/1")
            self.assertEqual(by[(_TGRERA.name, "youtube")]["state"], "queued")
            self.assertIn("kept-posted", r.stdout)

    def test_determinism_two_assets_either_order(self):
        with tempfile.TemporaryDirectory() as d:
            q1 = Path(d) / "q1.json"
            q2 = Path(d) / "q2.json"
            enqueue(_TGRERA, q1)
            enqueue(_FX / "pass-one-channel", q1)
            enqueue(_FX / "pass-one-channel", q2)
            enqueue(_TGRERA, q2)
            self.assertEqual(q1.read_bytes(), q2.read_bytes())


class TestGateRefusalNoWrite(unittest.TestCase):
    def _refuse(self, asset, expect_codes):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"  # deliberately does not exist yet
            r = enqueue(asset, qp)
            self.assertEqual(r.returncode, 1, msg=(r.stdout, r.stderr))
            self.assertFalse(qp.exists(), "queue must NOT be created on refusal")
            self.assertEqual(r.stdout, "")
            for code in expect_codes:
                self.assertIn("[{}]".format(code), r.stderr)
            # order of codes as they appear in stderr
            positions = [r.stderr.index("[{}]".format(c)) for c in expect_codes]
            self.assertEqual(positions, sorted(positions))

    def test_missing_verdict(self):
        self._refuse(_FX / "missing-verdict", ["missing-verdict"])

    def test_unparseable_verdict(self):
        self._refuse(_FX / "unparseable-verdict", ["missing-verdict"])

    def test_verdict_fail(self):
        self._refuse(_FX / "verdict-fail", ["verdict-not-pass"])

    def test_failed_checks_nonempty(self):
        self._refuse(_FX / "failed-checks-nonempty", ["failed-checks-nonempty"])

    def test_killed(self):
        self._refuse(_FX / "killed", ["killed"])

    def test_real_hyd_two_reasons_in_order(self):
        self._refuse(_HYD, ["missing-verdict", "killed"])


class TestUsageErrorsEmptyStdout(unittest.TestCase):
    def _usage(self, argv):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            full = argv + ["--queue", str(qp)]
            r = subprocess.run([sys.executable, str(_ENQUEUE)] + full,
                               capture_output=True, text=True, cwd=str(_REPO_ROOT))
            self.assertEqual(r.returncode, 2, msg=(r.stdout, r.stderr))
            self.assertEqual(r.stdout, "", "usage errors must have empty stdout")
            self.assertNotEqual(r.stderr, "")
            self.assertFalse(qp.exists(), "no queue write on usage error")

    def test_missing_asset(self):
        self._usage(["content/does-not-exist", "--week", "2026-W27"])

    def test_malformed_week(self):
        self._usage([str(_TGRERA), "--week", "2026-Q3"])

    def test_unmapped_channel_token(self):
        self._usage([str(_FX / "unmapped-channel"), "--week", "2026-W27"])

    def test_no_channel_only_format_words(self):
        self._usage([str(_FX / "no-channel"), "--week", "2026-W27"])

    def test_missing_week_arg(self):
        # argparse itself exits 2 when a required arg is absent.
        r = subprocess.run(
            [sys.executable, str(_ENQUEUE), str(_TGRERA)],
            capture_output=True, text=True, cwd=str(_REPO_ROOT))
        self.assertEqual(r.returncode, 2)


class TestImportSafety(unittest.TestCase):
    def test_imports_print_nothing(self):
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, 'tools/marketing-loops'); "
             "import gate, queue, channels; sys.stdout.write(queue.SCHEMA_VERSION)"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT))
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout, "1")  # only the explicit print, no import noise


if __name__ == "__main__":
    unittest.main()
