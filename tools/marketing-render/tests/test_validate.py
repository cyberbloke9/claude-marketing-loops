"""Fail-path unit tests for the Sprint 004 validator (contract s8).

Each check V2-V12 is proven to PASS on good input AND FAIL on its specific
violation, feeding crafted manifest dicts + tiny generated PNGs (no network).
The real TGRERA render is used for the V3/V5 pixel calibration + positive path.
Run the whole suite (no S001/002/003 regression):

    python3 -m unittest discover -s tools/marketing-render/tests -v
"""

import ast
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

_TESTS_DIR = Path(__file__).resolve().parent
_RENDER_DIR = _TESTS_DIR.parent
if str(_RENDER_DIR) not in sys.path:
    sys.path.insert(0, str(_RENDER_DIR))
import measure   # noqa: E402
import render    # noqa: E402
import validate  # noqa: E402

_REPO_ROOT = _RENDER_DIR.parent.parent
_TGRERA = _REPO_ROOT / "content" / "2026-07-03-tgrera-enforcement-wave"
TOK = measure.TOKENS
PROV = ("<!-- provenance:start -->\nsources: NewsMeter · Siasat\n"
        "terrem_db_numbers: none\nas_of: 2026-06-30\n<!-- provenance:end -->\n")


def el(text, role, fpx, weight, color, bg, bbox):
    return {"text": text, "role": role, "font_px": fpx, "weight": weight,
            "color": color, "bg": bg, "bbox": list(bbox)}


def _draw(draw, x, y, text, fpx, weight, color):
    font = render._font(weight, fpx)
    draw.text((x, y), text, font=font, fill=color, anchor="la")
    l, t, r, b = draw.textbbox((x, y), text, font=font, anchor="la")
    return [l, t, r - l, b - t]


class Harness:
    """Build a temp content asset folder with a rendered chart card + manifest."""

    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="fxtest-"))

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, surfaces, images, meta=PROV, copy=None):
        rd = self.dir / "render"
        rd.mkdir(parents=True, exist_ok=True)
        for name, img in images.items():
            img.save(rd / name)
        manifest = {"schema_version": "1", "slug": self.dir.name, "surfaces": surfaces}
        (rd / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (self.dir / "meta.md").write_text("# meta\n\n" + meta, encoding="utf-8")
        for fname, content in (copy or {}).items():
            (self.dir / fname).write_text(content, encoding="utf-8")
        return self.dir


def valid_card():
    """A rendered valid chart card: (surfaces, images). Passes all checks."""
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), TOK["bg"])
    d = ImageDraw.Draw(img)
    els = []
    els.append(el("Telangana's regulator hit three builders in nine days.",
                  "headline", 44, 700, TOK["ink"], TOK["bg"],
                  _draw(d, 90, 320, "Telangana's regulator hit three builders.",
                        44, 700, TOK["ink"])))
    stamp = "Source: NewsMeter · orders as of 2026-06-30"
    els.append(el(stamp, "source-stamp", 20, 400, TOK["ink-muted"], TOK["bg"],
                  _draw(d, 90, 1380, stamp, 20, 400, TOK["ink-muted"])))
    els.append(el("TERREM", "wordmark", 25, 700, TOK["accent-deep"], TOK["bg"],
                  _draw(d, 888, 1800, "TERREM", 25, 700, TOK["accent-deep"])))
    surf = {"id": "chart-card", "role": "chart-card", "png": "chart-card.png",
            "canvas": {"w": W, "h": H}, "has_axis": False, "axis_min": None,
            "zero_based": None, "break_disclosed": None, "elements": els}
    return [surf], {"chart-card.png": img}


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.h = Harness()

    def tearDown(self):
        self.h.cleanup()

    def verdict(self, surfaces, images, **kw):
        folder = self.h.write(surfaces, images, **kw)
        code = validate.run(str(folder), "2026-07-04", "validator-cli")
        doc = json.loads((folder / "render" / "qa-verdict.json").read_text())
        return code, doc

    def statuses(self, doc, cid):
        return [c["status"] for c in doc["checks"] if c["id"] == cid]


class TestV2Canvas(BaseCase):
    def test_match(self):
        s, i = valid_card()
        _, doc = self.verdict(s, i)
        self.assertIn("PASS", self.statuses(doc, "V2-canvas"))

    def test_mismatch(self):
        s, i = valid_card()
        i["chart-card.png"] = i["chart-card.png"].resize((1080, 1080))
        _, doc = self.verdict(s, i)
        self.assertIn("V2-canvas", [f["id"] for f in doc["failed_checks"]])


class TestV3Ink(BaseCase):
    def test_real_ink_passes_blank_fails_and_calibration(self):
        s, i = valid_card()
        _, doc = self.verdict(s, i)
        self.assertNotIn("V3-ink", [f["id"] for f in doc["failed_checks"]])
        # Blank PNG -> every element 0 ink -> FAIL.
        blank = {"chart-card.png": Image.new("RGB", (1080, 1920), TOK["bg"])}
        _, doc2 = self.verdict(s, blank)
        self.assertTrue(all(f["id"] == "V3-ink" for f in doc2["failed_checks"]))
        self.assertTrue(doc2["failed_checks"])

    def test_real_tgrera_elements_clear_ink_min_with_margin(self):
        mani = json.loads((_TGRERA / "render" / "manifest.json").read_text())
        png = Image.open(_TGRERA / "render" / "chart-card.png").convert("RGB")
        for elem in mani["surfaces"][0]["elements"]:
            rgb = validate._hex_rgb(elem["color"])
            ink, _ = validate._crop_rows_ink(png, elem["bbox"], rgb)
            self.assertGreater(ink, validate.INK_MIN_PX * 2,
                               "element {} ink {} not clearing margin".format(
                                   elem["role"], ink))


class TestV4Contrast(BaseCase):
    def test_pass_and_fail(self):
        self.assertTrue(measure.contrast_check(TOK["ink"], TOK["bg"], 44, 700)["passes"])
        s, i = valid_card()
        # Inject low-contrast body honestly rendered on a dark panel.
        img = i["chart-card.png"]
        d = ImageDraw.Draw(img)
        d.rectangle([70, 700, 1010, 780], fill=TOK["accent-deep"])
        bb = _draw(d, 90, 710, "low contrast copy", 27, 500, TOK["ink-muted"])
        s[0]["elements"].append(
            el("low contrast copy", "body", 27, 500, TOK["ink-muted"],
               TOK["accent-deep"], bb))
        _, doc = self.verdict(s, i)
        self.assertIn("V4-contrast", [f["id"] for f in doc["failed_checks"]])


class TestV5(BaseCase):
    def test_floor(self):
        self.assertFalse(measure.type_min_ok("carousel-slide", "headline", 30)["passes"])
        self.assertTrue(measure.type_min_ok("carousel-slide", "headline", 48)["passes"])
        self.assertTrue(measure.type_min_ok("chart-card", "headline", 36)["passes"])
        self.assertTrue(measure.type_min_ok("chart-card", "source-stamp", 8)["passes"])

    def test_crosscheck_real_2x_half(self):
        mani = json.loads((_TGRERA / "render" / "manifest.json").read_text())
        png = Image.open(_TGRERA / "render" / "chart-card.png").convert("RGB")
        for elem in mani["surfaces"][0]["elements"]:
            rgb = validate._hex_rgb(elem["color"])
            _, rows = validate._crop_rows_ink(png, elem["bbox"], rgb)
            band = validate._median_band_height(rows)
            eff = band / validate.K_INTER
            fpx = elem["font_px"]
            self.assertTrue(measure.size_consistent(fpx, eff, 0.25),
                            "real {} eff {:.1f} not within 25% of {}".format(
                                elem["role"], eff, fpx))
            self.assertFalse(measure.size_consistent(fpx * 2, eff, 0.25))
            self.assertFalse(measure.size_consistent(fpx * 0.5, eff, 0.25))

    def test_k_inter_value(self):
        self.assertEqual(validate.K_INTER, 0.83)


class TestV6(BaseCase):
    def test_in_out_exempt(self):
        self.assertTrue(measure.safe_zone_ok(1080, 1920, [90, 320, 900, 100])["passes"])
        self.assertFalse(measure.safe_zone_ok(1080, 1920, [90, 10, 900, 100])["passes"])
        s, i = valid_card()
        _, doc = self.verdict(s, i)
        # source-stamp + wordmark are exempt -> skipped for V6.
        self.assertIn("skipped", self.statuses(doc, "V6-safezone"))


class TestV7(BaseCase):
    def _carousel(self, hook_text):
        W, H = 1080, 1350
        img = Image.new("RGB", (W, H), TOK["bg"])
        d = ImageDraw.Draw(img)
        bb = _draw(d, 90, 700, hook_text, 48, 700, TOK["ink"])
        surf = {"id": "carousel-01", "role": "carousel-slide", "png": "c.png",
                "canvas": {"w": W, "h": H}, "has_axis": False, "axis_min": None,
                "zero_based": None, "break_disclosed": None,
                "elements": [el(hook_text, "hook", 48, 700, TOK["ink"], TOK["bg"], bb)]}
        return [surf], {"c.png": img}

    def test_ten_passes_eleven_fails(self):
        s, i = self._carousel("one two three four five six seven eight nine ten")
        _, doc = self.verdict(s, i)
        self.assertIn("PASS", self.statuses(doc, "V7-hook-words"))
        s, i = self._carousel("one two three four five six seven eight nine ten more")
        _, doc = self.verdict(s, i)
        self.assertIn("V7-hook-words", [f["id"] for f in doc["failed_checks"]])

    def test_no_hook_skipped(self):
        s, i = valid_card()
        _, doc = self.verdict(s, i)
        self.assertIn("skipped", self.statuses(doc, "V7-hook-words"))


class TestV8(BaseCase):
    def test_valid_missing_date_absent(self):
        s, i = valid_card()
        _, doc = self.verdict(s, i)
        self.assertIn("PASS", self.statuses(doc, "V8-source-stamp"))
        # stamp missing date.
        s, i = valid_card()
        for e in s[0]["elements"]:
            if e["role"] == "source-stamp":
                e["text"] = "Source: NewsMeter (no date here)"
        _, doc = self.verdict(s, i)
        self.assertIn("V8-source-stamp", [f["id"] for f in doc["failed_checks"]])
        # stamp absent entirely.
        s, i = valid_card()
        s[0]["elements"] = [e for e in s[0]["elements"] if e["role"] != "source-stamp"]
        _, doc = self.verdict(s, i)
        self.assertIn("V8-source-stamp", [f["id"] for f in doc["failed_checks"]])


class TestV9(BaseCase):
    def test_clean_and_hit(self):
        s, i = valid_card()
        _, doc = self.verdict(s, i)
        self.assertIn("PASS", self.statuses(doc, "V9-blacklist"))
        s, i = valid_card()
        copy = {"chart-spec.md": "90% of recall in first 6 seconds"}
        _, doc = self.verdict(s, i, copy=copy)
        fails = [f for f in doc["failed_checks"] if f["id"] == "V9-blacklist"]
        self.assertTrue(fails)
        self.assertIn("recall", fails[0]["detail"])


class TestV10(BaseCase):
    def test_skipped_fail_pass(self):
        s, i = valid_card()  # has_axis False
        _, doc = self.verdict(s, i)
        self.assertIn("skipped", self.statuses(doc, "V10-chart-integrity"))
        s, i = valid_card()
        s[0]["has_axis"] = True
        s[0]["axis_min"] = 20
        s[0]["break_disclosed"] = False
        _, doc = self.verdict(s, i)
        self.assertIn("V10-chart-integrity", [f["id"] for f in doc["failed_checks"]])
        s, i = valid_card()
        s[0]["has_axis"] = True
        s[0]["axis_min"] = 20
        s[0]["break_disclosed"] = True
        _, doc = self.verdict(s, i)
        self.assertIn("PASS", self.statuses(doc, "V10-chart-integrity"))


class TestV11(BaseCase):
    def test_present_missing_missingkey(self):
        s, i = valid_card()
        _, doc = self.verdict(s, i)
        self.assertIn("PASS", self.statuses(doc, "V11-provenance"))
        s, i = valid_card()
        _, doc = self.verdict(s, i, meta="no block here")
        self.assertIn("V11-provenance", [f["id"] for f in doc["failed_checks"]])
        s, i = valid_card()
        bad = ("<!-- provenance:start -->\nsources: X\nas_of: 2026-06-30\n"
               "<!-- provenance:end -->\n")  # missing terrem_db_numbers
        _, doc = self.verdict(s, i, meta=bad)
        self.assertIn("V11-provenance", [f["id"] for f in doc["failed_checks"]])


class TestVerdictAndStates(BaseCase):
    def test_pass_exit0_fail_exit1_shape(self):
        s, i = valid_card()
        folder = self.h.write(s, i)
        self.assertEqual(validate.run(str(folder), "2026-07-04", "validator-cli"), 0)
        doc = json.loads((folder / "render" / "qa-verdict.json").read_text())
        for k in ("schema_version", "slug", "verdict", "checked_on", "checked_by",
                  "checks", "failed_checks", "needs_review"):
            self.assertIn(k, doc)
        self.assertEqual(doc["verdict"], "PASS")
        for c in doc["checks"]:
            self.assertIn(c["status"], ("PASS", "FAIL", "skipped"))
        # A single FAIL flips verdict + exit 1.
        s, i = valid_card()
        s[0]["elements"] = [e for e in s[0]["elements"] if e["role"] != "source-stamp"]
        folder2 = Harness()
        try:
            fp = folder2.write(s, i)
            self.assertEqual(validate.run(str(fp), "2026-07-04", "validator-cli"), 1)
            d2 = json.loads((fp / "render" / "qa-verdict.json").read_text())
            self.assertEqual(d2["verdict"], "FAIL")
            self.assertTrue(d2["failed_checks"])
        finally:
            folder2.cleanup()

    def test_meta_idempotent(self):
        s, i = valid_card()
        folder = self.h.write(s, i)
        validate.run(str(folder), "2026-07-04", "validator-cli")
        validate.run(str(folder), "2026-07-04", "validator-cli")
        text = (folder / "meta.md").read_text()
        self.assertEqual(text.count(validate._VERDICT_START), 1)
        self.assertEqual(text.count(validate._PROV_START), 1)

    def test_missing_folder_exit2(self):
        self.assertEqual(validate.main(["/no/such/folder"]), 2)

    def test_missing_manifest_exit2(self):
        (self.h.dir / "meta.md").write_text("x", encoding="utf-8")
        self.assertEqual(validate.main([str(self.h.dir)]), 2)

    def test_bad_token_exit2_names_field(self):
        s, i = valid_card()
        s[0]["elements"][0]["color"] = "#123456"
        with self.assertRaises(validate.PreconditionError) as ctx:
            self.h.write(s, i)
            validate.load_asset(str(self.h.dir))
        self.assertIn("color", str(ctx.exception))

    def test_extra_field_tolerated(self):
        s, i = valid_card()
        s[0]["chart_ref"] = None  # unknown extra field from S003 manifest
        code, _ = self.verdict(s, i)
        self.assertEqual(code, 0)

    def test_determinism_fixed_date(self):
        s, i = valid_card()
        folder = self.h.write(s, i)
        validate.run(str(folder), "2026-07-04", "validator-cli")
        a = (folder / "render" / "qa-verdict.json").read_bytes()
        validate.run(str(folder), "2026-07-04", "validator-cli")
        b = (folder / "render" / "qa-verdict.json").read_bytes()
        self.assertEqual(a, b)


class TestPurity(unittest.TestCase):
    def test_no_network_import(self):
        src = (_RENDER_DIR / "validate.py").read_text()
        tree = ast.parse(src)
        banned = {"socket", "urllib", "http", "requests", "ssl", "ftplib",
                  "telnetlib", "smtplib", "asyncio"}
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    found.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module.split(".")[0])
        self.assertFalse(banned & found, "network import in validate.py: {}".format(
            banned & found))


class TestTgreraPositivePath(unittest.TestCase):
    def test_tgrera_passes_end_to_end(self):
        tmp = Path(tempfile.mkdtemp(prefix="tgrera-"))
        try:
            dst = tmp / "asset"
            shutil.copytree(_TGRERA, dst)
            code = validate.run(str(dst), "2026-07-04", "validator-cli")
            self.assertEqual(code, 0)
            doc = json.loads((dst / "render" / "qa-verdict.json").read_text())
            self.assertEqual(doc["verdict"], "PASS")
            self.assertEqual(doc["failed_checks"], [])
            self.assertIn("skipped", [c["status"] for c in doc["checks"]
                                      if c["id"] == "V7-hook-words"])
            self.assertIn("skipped", [c["status"] for c in doc["checks"]
                                      if c["id"] == "V10-chart-integrity"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
