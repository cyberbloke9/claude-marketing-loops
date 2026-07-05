"""Unit tests for the Sprint 004 csvspec module (contract s3.1/s3.2)."""

import sys
import tempfile
import unittest
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parent.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))
import csvspec  # noqa: E402

_FX = _TOOL_DIR / "fixtures" / "metrics"
_PLATFORM = csvspec.CONTRACTS["instagram"]
_SITE = csvspec.CONTRACTS["site"]


def _write(text):
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8")
    tmp.write(text)
    tmp.close()
    return Path(tmp.name)


class TestContracts(unittest.TestCase):
    def test_four_named_contracts(self):
        self.assertEqual(set(csvspec.CONTRACTS), {"instagram", "youtube",
                                                  "linkedin", "site"})

    def test_platform_contracts_share_shape(self):
        for kind in ("instagram", "youtube", "linkedin"):
            self.assertEqual(csvspec.CONTRACTS[kind]["headers"],
                             ["utm_campaign", "three_s_hold_pct",
                              "completion_pct", "shares", "clicks"])

    def test_site_headers_include_three_wrr_components(self):
        for comp in ("returning_viewers", "digest_opens",
                     "returning_visitors_social"):
            self.assertIn(comp, _SITE["headers"])

    def test_schema_version_declared_once(self):
        self.assertEqual(csvspec.CSV_SCHEMA_VERSION, "1")
        for c in csvspec.CONTRACTS.values():
            self.assertEqual(c["schema_version"], "1")


class TestHappyParse(unittest.TestCase):
    def test_platform_types(self):
        rows = csvspec.read_csv(_FX / "full" / "ig.csv", _PLATFORM)
        self.assertEqual(len(rows), 2)
        r = rows[0]
        self.assertEqual(r["utm_campaign"], "tgrera-enforcement-wave")
        self.assertEqual(r["shares"], 4)          # int
        self.assertIsInstance(r["three_s_hold_pct"], float)  # num

    def test_extra_columns_ignored(self):
        p = _write("utm_campaign,three_s_hold_pct,completion_pct,shares,clicks,extra\n"
                   "c,1,2,3,4,ignored\n")
        rows = csvspec.read_csv(p, _PLATFORM)
        self.assertNotIn("extra", rows[0])
        self.assertEqual(rows[0]["clicks"], 4)

    def test_header_only_is_present_not_malformed(self):
        rows = csvspec.read_csv(_FX / "header-only" / "site.csv", _SITE)
        self.assertEqual(rows, [])

    def test_trailing_blank_line_tolerated(self):
        p = _write("utm_campaign,three_s_hold_pct,completion_pct,shares,clicks\n"
                   "c,1,2,3,4\n\n")
        rows = csvspec.read_csv(p, _PLATFORM)
        self.assertEqual(len(rows), 1)


class TestBlankVsZero(unittest.TestCase):
    def test_blank_numeric_is_none(self):
        rows = csvspec.read_csv(_FX / "blank-cell" / "ig.csv", _PLATFORM)
        self.assertIsNone(rows[0]["clicks"])

    def test_zero_is_present_zero(self):
        rows = csvspec.read_csv(_FX / "zero-cell" / "ig.csv", _PLATFORM)
        self.assertEqual(rows[0]["clicks"], 0)
        self.assertIsNotNone(rows[0]["clicks"])


class TestRejections(unittest.TestCase):
    def test_missing_header(self):
        with self.assertRaises(csvspec.CsvError) as ctx:
            csvspec.read_csv(_FX / "wrong-header" / "site.csv", _SITE)
        self.assertIn("digest_opens", str(ctx.exception))

    def test_wrong_colcount(self):
        with self.assertRaises(csvspec.CsvError) as ctx:
            csvspec.read_csv(_FX / "wrong-colcount" / "ig.csv", _PLATFORM)
        self.assertIn("columns, expected", str(ctx.exception))

    def test_truncated(self):
        with self.assertRaises(csvspec.CsvError):
            csvspec.read_csv(_FX / "truncated" / "site.csv", _SITE)

    def test_non_numeric_int(self):
        with self.assertRaises(csvspec.CsvError) as ctx:
            csvspec.read_csv(_FX / "non-numeric" / "ig.csv", _PLATFORM)
        self.assertIn("shares", str(ctx.exception))

    def test_non_numeric_num(self):
        p = _write("utm_campaign,three_s_hold_pct,completion_pct,shares,clicks\n"
                   "c,1,2x,3,4\n")
        with self.assertRaises(csvspec.CsvError):
            csvspec.read_csv(p, _PLATFORM)

    def test_comma_decimal_rejected(self):
        p = _write("utm_campaign,three_s_hold_pct,completion_pct,shares,clicks\n"
                   "c,1,2,3,4\nc2,1,2,3,\"1,2\"\n")
        with self.assertRaises(csvspec.CsvError):
            csvspec.read_csv(p, _PLATFORM)

    def test_blank_join(self):
        with self.assertRaises(csvspec.CsvError) as ctx:
            csvspec.read_csv(_FX / "blank-join" / "site.csv", _SITE)
        self.assertIn("utm_campaign", str(ctx.exception))

    def test_empty_file(self):
        p = _write("")
        with self.assertRaises(csvspec.CsvError) as ctx:
            csvspec.read_csv(p, _PLATFORM)
        self.assertIn("missing required header", str(ctx.exception))

    def test_row_number_is_one_based_data_index(self):
        # Header not counted: the bad row is data-row 2.
        p = _write("utm_campaign,three_s_hold_pct,completion_pct,shares,clicks\n"
                   "c,1,2,3,4\n"
                   "c2,1,2,bad,4\n")
        with self.assertRaises(csvspec.CsvError) as ctx:
            csvspec.read_csv(p, _PLATFORM)
        self.assertIn("row 2", str(ctx.exception))

    def test_negative_int_allowed(self):
        p = _write("utm_campaign,three_s_hold_pct,completion_pct,shares,clicks\n"
                   "c,1,2,-3,4\n")
        rows = csvspec.read_csv(p, _PLATFORM)
        self.assertEqual(rows[0]["shares"], -3)


class TestImportSafety(unittest.TestCase):
    def test_import_is_silent(self):
        import subprocess
        repo = _TOOL_DIR.parent.parent
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0,'tools/marketing-loops'); import csvspec"],
            capture_output=True, text=True, cwd=str(repo))
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.stderr, "")


if __name__ == "__main__":
    unittest.main()
