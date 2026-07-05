"""Integration tests for the Sprint 003 package CLI (contract s3.3 / s9).

Runs package.py as a subprocess to assert exit codes, stdout/stderr, on-disk
PACKAGE + QUEUE JSON, per-channel UTM links, attachments, idempotency,
no-regress/no-overwrite of posted rows, and the cross-command regression with the
Sprint-002 enqueue CLI.
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
_PACKAGE = _TOOL_DIR / "package.py"
_ENQUEUE = _TOOL_DIR / "enqueue.py"
_FX = _TOOL_DIR / "fixtures" / "publish"
_CONTENT = _REPO_ROOT / "content"
_TGRERA = _CONTENT / "2026-07-03-tgrera-enforcement-wave"
_HYD = _CONTENT / "2026-07-03-hyd-premium-vs-budget"


def package(asset_dir, queue_path, publish_dir, week="2026-W27"):
    argv = [sys.executable, str(_PACKAGE), str(asset_dir), "--week", week,
            "--queue", str(queue_path), "--publish-dir", str(publish_dir)]
    return subprocess.run(argv, capture_output=True, text=True, cwd=str(_REPO_ROOT))


class TestSuccessPath(unittest.TestCase):
    def test_pkg_pass_three_packages_and_rows(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            pd = Path(d) / "pub"
            r = package(_FX / "pkg-pass", qp, pd)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            for c in ("instagram", "youtube", "linkedin"):
                pkg = json.loads((pd / "{}.json".format(c)).read_text())
                self.assertEqual(pkg["schema_version"], "1")
                self.assertEqual(pkg["channel"], c)
                self.assertEqual(pkg["utm_source"], c)
                self.assertIn("utm_source={}".format(c), pkg["utm_link"])
                self.assertIn("utm_medium=social", pkg["utm_link"])
                self.assertIn("utm_campaign=pkg-pass", pkg["utm_link"])
                # caption = body + blank line + link
                self.assertTrue(pkg["caption"].endswith("\n\n" + pkg["utm_link"]))
            rows = json.loads(qp.read_text())["rows"]
            self.assertEqual(len(rows), 3)
            for row in rows:
                self.assertEqual(row["state"], "queued")
                self.assertIsNotNone(row["schedule_slot"])
                self.assertIsNotNone(row["package_path"])

    def test_real_tgrera_ground_truth(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            pd = Path(d) / "pub"
            r = package(_TGRERA, qp, pd)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            ig = json.loads((pd / "instagram.json").read_text())
            self.assertEqual(
                ig["attachments"],
                ["content/2026-07-03-tgrera-enforcement-wave/render/chart-card.png"])
            self.assertEqual(ig["schedule_slot"], "2026-W27/evening/18:00")
            self.assertIn("utm_campaign=tgrera-enforcement-wave", ig["utm_link"])
            yt = json.loads((pd / "youtube.json").read_text())
            self.assertEqual(yt["schedule_slot"], "2026-W27/morning/11:00")
            li = json.loads((pd / "linkedin.json").read_text())
            self.assertEqual(li["schedule_slot"], "2026-W27/evening/17:30")

    def test_multi_surface_ordered_attachments(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            pd = Path(d) / "pub"
            r = package(_FX / "pkg-multi-surface", qp, pd)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            att = json.loads((pd / "instagram.json").read_text())["attachments"]
            self.assertEqual(len(att), 3)
            self.assertTrue(att[0].endswith("carousel-01.png"))
            self.assertTrue(att[2].endswith("carousel-03.png"))

    def test_per_channel_caption_override(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            pd = Path(d) / "pub"
            package(_FX / "pkg-per-channel-caption", qp, pd)
            ig = json.loads((pd / "instagram.json").read_text())["caption"]
            yt = json.loads((pd / "youtube.json").read_text())["caption"]
            self.assertTrue(ig.startswith("Instagram-specific override body."))
            self.assertTrue(yt.startswith("Shared body used by youtube and linkedin."))

    def test_idempotent_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            pd = Path(d) / "pub"
            r1 = package(_TGRERA, qp, pd)
            q_first = qp.read_bytes()
            pkgs_first = {p.name: p.read_bytes() for p in pd.glob("*.json")}
            r2 = package(_TGRERA, qp, pd)
            self.assertEqual(qp.read_bytes(), q_first)
            self.assertEqual({p.name: p.read_bytes() for p in pd.glob("*.json")},
                             pkgs_first)
            self.assertEqual(r2.stdout, r1.stdout)
            self.assertEqual(len(json.loads(qp.read_text())["rows"]), 3)


class TestGateNeverBypassed(unittest.TestCase):
    def _refuse(self, asset, codes):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            pd = Path(d) / "pub"
            r = package(asset, qp, pd)
            self.assertEqual(r.returncode, 1, msg=(r.stdout, r.stderr))
            self.assertEqual(r.stdout, "")
            self.assertFalse(qp.exists(), "queue must NOT be written on gate refusal")
            for c in codes:
                self.assertIn("[{}]".format(c), r.stderr)

    def test_real_hyd_missing_verdict_and_killed(self):
        self._refuse(_HYD, ["missing-verdict", "killed"])

    def test_killed_fixture(self):
        self._refuse(_FX / "killed", ["killed"])

    def test_verdict_fail_fixture(self):
        self._refuse(_FX / "verdict-fail", ["verdict-not-pass"])


class TestPreconditionExit2NoWrite(unittest.TestCase):
    def _usage(self, asset, needle=None, week="2026-W27"):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            pd = Path(d) / "pub"
            r = package(asset, qp, pd, week=week)
            self.assertEqual(r.returncode, 2, msg=(r.stdout, r.stderr))
            self.assertEqual(r.stdout, "", "usage errors must have empty stdout")
            self.assertFalse(qp.exists(), "no queue write on precondition error")
            if needle:
                self.assertIn(needle, r.stderr)

    def test_no_captions(self):
        self._usage(_FX / "pkg-no-captions", needle="no captions.md")

    def test_missing_channel_caption_names_youtube(self):
        self._usage(_FX / "pkg-missing-channel-caption", needle="'youtube'")

    def test_bad_utm_cites_code(self):
        self._usage(_FX / "pkg-bad-utm", needle="[campaign-mismatch]")

    def test_no_manifest(self):
        self._usage(_FX / "pkg-no-manifest", needle="manifest.json not found")

    def test_empty_surfaces(self):
        self._usage(_FX / "pkg-empty-surfaces", needle="'surfaces'")

    def test_malformed_week(self):
        self._usage(_TGRERA, week="2026-Q3")

    def test_missing_asset(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            pd = Path(d) / "pub"
            r = package("content/does-not-exist", qp, pd)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(r.stdout, "")
            self.assertFalse(qp.exists())


class TestNoRegressPosted(unittest.TestCase):
    def test_posted_row_and_package_survive_repackage(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            pd = Path(d) / "pub"
            package(_TGRERA, qp, pd)
            # mark instagram posted directly in the queue.
            data = json.loads(qp.read_text())
            for row in data["rows"]:
                if row["channel"] == "instagram":
                    row["state"] = "posted"
                    row["posted_date"] = "2026-07-04"
                    row["permalink"] = "https://ig.example/p/1"
            qp.write_text(json.dumps(data))
            ig_before = (pd / "instagram.json").read_bytes()
            r = package(_TGRERA, qp, pd)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            self.assertIn("kept-posted 2026-07-03-tgrera-enforcement-wave instagram",
                          r.stdout)
            self.assertIn("packaged 2026-07-03-tgrera-enforcement-wave youtube",
                          r.stdout)
            self.assertEqual((pd / "instagram.json").read_bytes(), ig_before,
                             "posted channel's package must not be rewritten")
            by = {row["channel"]: row for row in json.loads(qp.read_text())["rows"]}
            self.assertEqual(by["instagram"]["state"], "posted")
            self.assertEqual(by["instagram"]["posted_date"], "2026-07-04")
            self.assertEqual(by["instagram"]["permalink"], "https://ig.example/p/1")


class TestFullyPostedRepackage(unittest.TestCase):
    """A re-package where every channel is already posted needs no captions."""

    def test_all_posted_kept_without_captions(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            pd = Path(d) / "pub"
            # seed a queue with all three channels already posted.
            rows = []
            for c in ("instagram", "youtube", "linkedin"):
                rows.append({
                    "slug": "pkg-pass", "channel": c, "state": "posted",
                    "week": "2026-W27", "schedule_slot": "2026-W27/x/00:00",
                    "package_path": "p/{}.json".format(c),
                    "posted_date": "2026-07-04", "permalink": "https://x/{}".format(c),
                })
            qp.write_text(json.dumps({"schema_version": "1", "rows": rows}))
            before = qp.read_bytes()
            # even if pkg-pass HAD no captions this must succeed — but pkg-pass does
            # have captions.md, so we assert the stronger property: no writes at all
            # and all-kept-posted stdout.
            r = package(_FX / "pkg-pass", qp, pd)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            self.assertEqual(
                set(r.stdout.split("\n")) - {""},
                {"kept-posted pkg-pass {}".format(c)
                 for c in ("instagram", "youtube", "linkedin")})
            self.assertFalse(list(pd.glob("*.json")),
                             "no package files rewritten for posted channels")
            # queue keeps the posted rows wholesale (compare by (slug,channel);
            # the file is rewritten in deterministic sorted order).
            after_by = {(r["slug"], r["channel"]): r
                        for r in json.loads(qp.read_text())["rows"]}
            before_by = {(r["slug"], r["channel"]): r
                         for r in json.loads(before)["rows"]}
            self.assertEqual(after_by, before_by)


class TestCrossCommandRegression(unittest.TestCase):
    """Probe #11: enqueue -> package -> enqueue; slot/package_path survive."""

    def test_enqueue_package_enqueue(self):
        with tempfile.TemporaryDirectory() as d:
            qp = Path(d) / "q.json"
            pd = Path(d) / "pub"
            subprocess.run(
                [sys.executable, str(_ENQUEUE), str(_TGRERA), "--week",
                 "2026-W27", "--queue", str(qp)],
                capture_output=True, text=True, cwd=str(_REPO_ROOT))
            # after enqueue: slots null
            rows = json.loads(qp.read_text())["rows"]
            self.assertTrue(all(r["schedule_slot"] is None for r in rows))
            package(_TGRERA, qp, pd)
            after_pkg = qp.read_bytes()
            rows = json.loads(qp.read_text())["rows"]
            self.assertTrue(all(r["schedule_slot"] is not None for r in rows))
            # re-enqueue must NOT wipe the slot/package_path package.py set.
            subprocess.run(
                [sys.executable, str(_ENQUEUE), str(_TGRERA), "--week",
                 "2026-W27", "--queue", str(qp)],
                capture_output=True, text=True, cwd=str(_REPO_ROOT))
            self.assertEqual(qp.read_bytes(), after_pkg, "enqueue must keep the "
                             "queued row (incl. slot/package_path) wholesale")


if __name__ == "__main__":
    unittest.main()
