"""Integration tests for the Sprint 003 mark_posted CLI (contract s3.4 / s9)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_TOOL_DIR = _TESTS_DIR.parent
_REPO_ROOT = _TOOL_DIR.parent.parent
_MARK = _TOOL_DIR / "mark_posted.py"

_SLUG = "2026-07-03-tgrera-enforcement-wave"


def _seed_queue(path, state="queued"):
    doc = {"schema_version": "1", "rows": [
        {"slug": _SLUG, "channel": "instagram", "state": state, "week": "2026-W27",
         "schedule_slot": "2026-W27/evening/18:00", "package_path": "p/instagram.json",
         "posted_date": None if state == "queued" else "2026-07-01",
         "permalink": None if state == "queued" else "https://ig.example/old"},
        {"slug": _SLUG, "channel": "youtube", "state": "queued", "week": "2026-W27",
         "schedule_slot": "2026-W27/morning/11:00", "package_path": "p/youtube.json",
         "posted_date": None, "permalink": None},
    ]}
    Path(path).write_text(json.dumps(doc))


def mark(slug, channel, queue_path, posted_on="2026-07-04",
         permalink="https://instagram.com/p/xyz"):
    argv = [sys.executable, str(_MARK), slug, channel,
            "--posted-on", posted_on, "--permalink", permalink,
            "--queue", str(queue_path)]
    return subprocess.run(argv, capture_output=True, text=True, cwd=str(_REPO_ROOT))


class TestHappyPath(unittest.TestCase):
    def test_queued_to_posted(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            _seed_queue(qp)
            r = mark(_SLUG, "instagram", qp)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            self.assertEqual(r.stdout.strip(),
                             "posted {} instagram 2026-07-04".format(_SLUG))
            by = {x["channel"]: x for x in json.loads(qp.read_text())["rows"]}
            self.assertEqual(by["instagram"]["state"], "posted")
            self.assertEqual(by["instagram"]["posted_date"], "2026-07-04")
            self.assertEqual(by["instagram"]["permalink"], "https://instagram.com/p/xyz")
            # other row untouched
            self.assertEqual(by["youtube"]["state"], "queued")


class TestRefusals(unittest.TestCase):
    def test_already_posted_exit1_no_write(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            _seed_queue(qp, state="posted")
            before = qp.read_bytes()
            r = mark(_SLUG, "instagram", qp)
            self.assertEqual(r.returncode, 1, msg=(r.stdout, r.stderr))
            self.assertEqual(r.stdout, "")
            self.assertIn("already posted", r.stderr)
            self.assertEqual(qp.read_bytes(), before, "no write on refusal")

    def test_non_idempotent_second_mark_refused(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            _seed_queue(qp)
            self.assertEqual(mark(_SLUG, "instagram", qp).returncode, 0)
            r2 = mark(_SLUG, "instagram", qp)
            self.assertEqual(r2.returncode, 1)

    def test_row_not_found_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            _seed_queue(qp)
            r = mark("nope-slug", "instagram", qp)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(r.stdout, "")

    def test_empty_permalink_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            _seed_queue(qp)
            r = mark(_SLUG, "youtube", qp, permalink="   ")
            self.assertEqual(r.returncode, 2)
            self.assertEqual(r.stdout, "")

    def test_non_url_permalink_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            _seed_queue(qp)
            r = mark(_SLUG, "youtube", qp, permalink="ftp://x")
            self.assertEqual(r.returncode, 2)

    def test_malformed_date_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            _seed_queue(qp)
            self.assertEqual(mark(_SLUG, "youtube", qp, posted_on="2026-7-4").returncode, 2)
            self.assertEqual(mark(_SLUG, "youtube", qp, posted_on="2026-13-40").returncode, 2)

    def test_unknown_channel_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            _seed_queue(qp)
            r = mark(_SLUG, "twitter", qp)
            self.assertEqual(r.returncode, 2)

    def test_missing_queue_exit2(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "does-not-exist.json"
            r = mark(_SLUG, "instagram", qp)
            self.assertEqual(r.returncode, 2)
            self.assertFalse(qp.exists())


class TestImportSafety(unittest.TestCase):
    def test_import_is_silent(self):
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0,'tools/marketing-loops'); import mark_posted"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT))
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.stderr, "")


if __name__ == "__main__":
    unittest.main()
