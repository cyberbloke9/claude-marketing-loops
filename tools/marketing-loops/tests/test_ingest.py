"""Unit tests for the Sprint 004 ingest builder + CLI (contract s3.4/s3.5/s3.6)."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parent.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))
import ingest    # noqa: E402
import assetmap  # noqa: E402

_REPO = _TOOL_DIR.parent.parent
_FX = _TOOL_DIR / "fixtures" / "metrics"
_FULL_CONTENT = _FX / "full" / "content"
_CLI = _TOOL_DIR / "ingest.py"


def _run(*args):
    return subprocess.run([sys.executable, str(_CLI), *args],
                          capture_output=True, text=True, cwd=str(_REPO))


def _load(cp):
    return json.loads(cp.stdout)


class TestBuilderPure(unittest.TestCase):
    def setUp(self):
        self.amap = assetmap.build_asset_map(_FULL_CONTENT)

    def test_empty_run_shape(self):
        d = ingest.build_ingest(
            "2026-W27",
            {"instagram": None, "youtube": None, "linkedin": None, "site": None},
            self.amap)
        self.assertEqual(d["schema_version"], "1")
        self.assertFalse(any(d["sources_provided"].values()))
        self.assertEqual(d["flywheel_clicks_by_campaign"], [])
        self.assertEqual(d["craft"], [])
        self.assertTrue(all(not v["present"]
                            for v in d["wrr_components"].values()))
        self.assertEqual(len(d["assets"]), 2)

    def test_empty_run_absences_are_exactly_four_sources(self):
        # Contract s4/s3.5: the empty state has exactly one absence per
        # not-provided source (4) — NO wrr-component absences when site is absent.
        d = ingest.build_ingest(
            "2026-W27",
            {"instagram": None, "youtube": None, "linkedin": None, "site": None},
            self.amap)
        self.assertEqual(
            d["absences"],
            [{"kind": "source", "detail": "instagram export not provided"},
             {"kind": "source", "detail": "linkedin export not provided"},
             {"kind": "source", "detail": "site analytics export not provided"},
             {"kind": "source", "detail": "youtube export not provided"}])

    def test_no_wrr_sum_key_anywhere(self):
        d = ingest.build_ingest(
            "2026-W27",
            {"instagram": None, "youtube": None, "linkedin": None, "site": None},
            self.amap)
        blob = json.dumps(d).lower()
        self.assertNotIn("\"wrr\":", blob)
        self.assertNotIn("wrr_value", blob)
        self.assertNotIn("wrr_sum", blob)


class TestFullHappyPath(unittest.TestCase):
    def test_exit0_and_content(self):
        cp = _run("--week", "2026-W27",
                  "--instagram", str(_FX / "full" / "ig.csv"),
                  "--youtube", str(_FX / "full" / "yt.csv"),
                  "--linkedin", str(_FX / "full" / "li.csv"),
                  "--site", str(_FX / "full" / "site.csv"),
                  "--content-dir", str(_FULL_CONTENT))
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        d = _load(cp)
        self.assertTrue(all(d["sources_provided"].values()))
        # 2 assets x 3 channels = 6 craft rows.
        self.assertEqual(len(d["craft"]), 6)
        fly = {f["campaign"]: f["clicks"]
               for f in d["flywheel_clicks_by_campaign"]}
        self.assertEqual(fly["tgrera-enforcement-wave"], 42)
        self.assertEqual(fly["rera-refund-timeline"], 18)
        self.assertEqual(d["wrr_components"]["returning_viewers"]["value"], 200)
        self.assertEqual(d["wrr_components"]["digest_opens"]["value"], 95)
        self.assertEqual(
            d["wrr_components"]["returning_visitors_social"]["value"], 52)
        self.assertEqual(d["absences"], [])

    def test_join_resolves_slug_and_hook(self):
        cp = _run("--week", "2026-W27",
                  "--instagram", str(_FX / "full" / "ig.csv"),
                  "--content-dir", str(_FULL_CONTENT))
        d = _load(cp)
        tg = [c for c in d["craft"]
              if c["campaign"] == "tgrera-enforcement-wave"][0]
        self.assertEqual(tg["slug"], "2026-07-03-tgrera-enforcement-wave")
        self.assertEqual(tg["hook_number"], 11)

    def test_craft_ordering(self):
        cp = _run("--week", "2026-W27",
                  "--instagram", str(_FX / "full" / "ig.csv"),
                  "--youtube", str(_FX / "full" / "yt.csv"),
                  "--content-dir", str(_FULL_CONTENT))
        d = _load(cp)
        keys = [(c["campaign"], c["channel"]) for c in d["craft"]]
        self.assertEqual(keys, sorted(keys))


class TestBlankVsZero(unittest.TestCase):
    def test_blank_cell_is_null(self):
        cp = _run("--week", "2026-W27",
                  "--instagram", str(_FX / "blank-cell" / "ig.csv"),
                  "--content-dir", str(_FULL_CONTENT))
        d = _load(cp)
        tg = [c for c in d["craft"]
              if c["campaign"] == "tgrera-enforcement-wave"][0]
        self.assertIsNone(tg["clicks"])

    def test_zero_cell_is_zero(self):
        cp = _run("--week", "2026-W27",
                  "--instagram", str(_FX / "zero-cell" / "ig.csv"),
                  "--content-dir", str(_FULL_CONTENT))
        d = _load(cp)
        tg = [c for c in d["craft"]
              if c["campaign"] == "tgrera-enforcement-wave"][0]
        self.assertEqual(tg["clicks"], 0)


class TestFlags(unittest.TestCase):
    def test_unmatched_campaign(self):
        cp = _run("--week", "2026-W27",
                  "--instagram", str(_FX / "unmatched" / "ig.csv"),
                  "--content-dir", str(_FULL_CONTENT))
        d = _load(cp)
        ghost = [c for c in d["craft"]
                 if c["campaign"] == "ghost-campaign-no-asset"][0]
        self.assertIsNone(ghost["slug"])
        self.assertIsNone(ghost["hook_number"])
        self.assertIn({"kind": "unmatched-campaign",
                       "detail": "ghost-campaign-no-asset"}, d["absences"])

    def test_wrong_utm_flag(self):
        cp = _run("--week", "2026-W27",
                  "--instagram", str(_FX / "wrong-utm" / "ig.csv"),
                  "--content-dir", str(_FX / "wrong-utm" / "content"))
        d = _load(cp)
        bad = d["assets"][0]
        self.assertFalse(bad["utm_valid"])
        self.assertEqual(bad["utm_violations"], ["wrong-medium"])
        self.assertTrue(any(a["kind"] == "wrong-utm" for a in d["absences"]))

    def test_wrr_partial_component(self):
        # Blank one component's whole column -> that component absent, others present.
        content = str(_FULL_CONTENT)
        import tempfile
        p = Path(tempfile.mkdtemp()) / "site.csv"
        p.write_text(
            "utm_source,utm_medium,utm_campaign,clicks,returning_viewers,"
            "digest_opens,returning_visitors_social\n"
            "instagram,social,tgrera-enforcement-wave,42,120,,30\n",
            encoding="utf-8")
        cp = _run("--week", "2026-W27", "--site", str(p),
                  "--content-dir", content)
        d = _load(cp)
        self.assertFalse(d["wrr_components"]["digest_opens"]["present"])
        self.assertIsNone(d["wrr_components"]["digest_opens"]["value"])
        self.assertTrue(d["wrr_components"]["returning_viewers"]["present"])
        self.assertTrue(
            d["wrr_components"]["returning_visitors_social"]["present"])
        # site IS provided -> the blank component IS a wrr-component absence.
        self.assertIn(
            {"kind": "wrr-component",
             "detail": "digest_opens (WRR component) absent"},
            d["absences"])


class TestRejections(unittest.TestCase):
    def _reject(self, *args):
        cp = _run(*args)
        self.assertEqual(cp.returncode, 2, msg=cp.stdout)
        self.assertEqual(cp.stdout, "")           # no partial JSON
        self.assertTrue(cp.stderr.startswith("ERROR:"), msg=cp.stderr)
        return cp

    def test_truncated(self):
        self._reject("--week", "2026-W27",
                     "--site", str(_FX / "truncated" / "site.csv"),
                     "--content-dir", str(_FULL_CONTENT))

    def test_wrong_header(self):
        cp = self._reject("--week", "2026-W27",
                          "--site", str(_FX / "wrong-header" / "site.csv"),
                          "--content-dir", str(_FULL_CONTENT))
        self.assertIn("digest_opens", cp.stderr)

    def test_wrong_colcount(self):
        self._reject("--week", "2026-W27",
                     "--instagram", str(_FX / "wrong-colcount" / "ig.csv"),
                     "--content-dir", str(_FULL_CONTENT))

    def test_non_numeric(self):
        self._reject("--week", "2026-W27",
                     "--instagram", str(_FX / "non-numeric" / "ig.csv"),
                     "--content-dir", str(_FULL_CONTENT))

    def test_blank_join(self):
        self._reject("--week", "2026-W27",
                     "--site", str(_FX / "blank-join" / "site.csv"),
                     "--content-dir", str(_FULL_CONTENT))

    def test_bad_path_not_absent_source(self):
        self._reject("--week", "2026-W27", "--youtube", "/no/such/file.csv",
                     "--content-dir", str(_FULL_CONTENT))

    def test_bad_week(self):
        for bad in ("2026-27", "26-W27", "2026-W5", "2026W27"):
            self._reject("--week", bad, "--content-dir", str(_FULL_CONTENT))

    def test_bad_content_dir(self):
        self._reject("--week", "2026-W27", "--content-dir", "/no/such/dir")


class TestNoWriteOnCorrupt(unittest.TestCase):
    def test_out_not_written_on_corrupt(self):
        import tempfile
        out = Path(tempfile.mkdtemp()) / "sub" / "ingest.json"
        cp = _run("--week", "2026-W27",
                  "--site", str(_FX / "truncated" / "site.csv"),
                  "--content-dir", str(_FULL_CONTENT), "--out", str(out))
        self.assertEqual(cp.returncode, 2)
        self.assertFalse(out.exists())

    def test_out_written_on_success(self):
        import tempfile
        out = Path(tempfile.mkdtemp()) / "sub" / "ingest.json"
        cp = _run("--week", "2026-W27", "--content-dir", str(_FULL_CONTENT),
                  "--out", str(out))
        self.assertEqual(cp.returncode, 0)
        self.assertTrue(out.exists())
        self.assertEqual(cp.stdout, "")           # went to file, not stdout
        json.loads(out.read_text(encoding="utf-8"))


class TestDeterminism(unittest.TestCase):
    def test_byte_identical(self):
        args = ("--week", "2026-W27", "--site", str(_FX / "full" / "site.csv"),
                "--content-dir", str(_FULL_CONTENT))
        a = _run(*args)
        b = _run(*args)
        self.assertEqual(a.stdout, b.stdout)
        self.assertTrue(a.stdout.endswith("\n"))


class TestImportSafety(unittest.TestCase):
    def test_import_is_silent(self):
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0,'tools/marketing-loops'); import ingest"],
            capture_output=True, text=True, cwd=str(_REPO))
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.stderr, "")


if __name__ == "__main__":
    unittest.main()
