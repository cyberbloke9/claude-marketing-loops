"""Unit tests for the Sprint 002 Renderer V2 format library (contract s7-s8).

Covers the three batch-A format-slide templates (BIG-NUMBER, RECEIPTS,
CHECKLIST): formats.md parsing, per-format required-role enforcement, 1080x1350
canvas, the exactly-one-dominant + raised-floor + one-wordmark invariants
(cross-checked through the frozen Sprint-001 measure functions), schema-v2
manifest emission, deterministic re-render (decoded-RGBA + manifest bytes), every
fail-loud error state with atomic no-partial-write, brand-token discipline, the
anti-tofu guard, and the v1 byte-freeze (carousel + chart-card unchanged).

Stdlib ``unittest`` + Pillow only. The tool dir is placed on ``sys.path`` (no
__init__.py, matching Sprint 001) so ``render``/``measure`` import directly.
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

_TOOL_DIR = Path(__file__).resolve().parent.parent
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))

import measure  # noqa: E402
import render  # noqa: E402

_INPUTS = _TOOL_DIR / "tests" / "inputs"
_REPO = _TOOL_DIR.parent.parent
# Sprint-006 CONSCIOUS RELOCATION (Risk 2/C): the live TGRERA content folder is
# now a schema-v2 carousel, so the frozen "tgrera stays schema 1 / emits no pdf"
# invariants below are re-proven against a byte-identical retained v1 chart-card
# snapshot (same chart-spec copy, same render). The assertions are preserved
# verbatim; only the asset PATH moves — no freeze guarantee weakened.
_TGRERA_V1 = _TOOL_DIR / "tests" / "data" / "2026-07-03-tgrera-enforcement-wave"
_BATCH_A = ("fmt-big-number", "fmt-receipts", "fmt-checklist")
_BATCH_B = ("fmt-timeline", "fmt-vs-contrast", "fmt-leaderboard", "fmt-chart")
_ALL_FIXTURES = _BATCH_A + _BATCH_B
_FORMAT_BY_FIXTURE = {
    "fmt-big-number": "BIG-NUMBER",
    "fmt-receipts": "RECEIPTS",
    "fmt-checklist": "CHECKLIST",
    "fmt-timeline": "TIMELINE",
    "fmt-vs-contrast": "VS-CONTRAST",
    "fmt-leaderboard": "LEADERBOARD",
    "fmt-chart": "CHART",
}


def _rgba_sha(img):
    return hashlib.sha256(img.convert("RGBA").tobytes()).hexdigest()


def _render_fixture(name):
    """Render a batch-A input fixture in a temp copy; return (images, manifest)."""
    src = _INPUTS / name
    return render.render_asset(str(src))


def _write_asset(tmp, text, filename="formats.md"):
    """Create a throwaway asset folder holding one authored spec file."""
    folder = Path(tmp) / "asset"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / filename).write_text(text, encoding="utf-8")
    return folder


# --- Happy path: canvas, schema, format tag (matrix rows 1-3) ------------------


class TestCanvasAndSchema(unittest.TestCase):
    def test_each_fixture_renders_one_format_slide_1080x1350(self):
        for name in _BATCH_A:
            images, manifest = _render_fixture(name)
            self.assertEqual(manifest["schema_version"], "2", name)
            surfs = manifest["surfaces"]
            self.assertEqual(len(surfs), 1, name)
            s = surfs[0]
            self.assertEqual(s["role"], "format-slide", name)
            self.assertEqual(s["format"], _FORMAT_BY_FIXTURE[name], name)
            self.assertEqual(s["canvas"], {"w": 1080, "h": 1350}, name)
            self.assertIs(s["has_axis"], False, name)
            self.assertEqual(s["png"], "format-01.png", name)
            self.assertEqual(images[s["png"]].size, (1080, 1350), name)

    def test_no_pdf_key_this_sprint(self):
        # Sprint-004 conscious re-point (contract s0 / adversarial row 17): the
        # carousel PDF now lands, so a v2 (schema "2") manifest MUST carry the
        # positive invariant pdf == "carousel.pdf". The preserved NEGATIVE
        # invariant — a schema "1" manifest carries NO pdf key — is re-proven
        # against a v1 asset so the freeze guarantee is not lost, only relocated
        # to its correct post-Sprint-004 value. No assertion is weakened.
        for name in _BATCH_A:
            _, manifest = _render_fixture(name)
            self.assertEqual(manifest["schema_version"], "2", name)
            self.assertEqual(manifest["pdf"], "carousel.pdf", name)
        _, v1 = render.render_asset(
            str(_REPO / "content" / "2026-07-03-hyd-premium-vs-budget"))
        self.assertEqual(v1["schema_version"], "1")
        self.assertNotIn("pdf", v1)

    def test_ids_are_format_nn_in_order(self):
        _, manifest = _render_fixture("fmt-receipts")
        self.assertEqual(manifest["surfaces"][0]["id"], "format-01")


# --- V13 dominant ratio + V14 floors via frozen measure fns (rows 4-6) ---------


class TestDominantAndFloors(unittest.TestCase):
    def test_every_content_slide_has_exactly_one_dominant_over_3x(self):
        for name in _BATCH_A:
            _, manifest = _render_fixture(name)
            for s in manifest["surfaces"]:
                els = s["elements"]
                r = measure.dominant_ratio_ok(els)
                self.assertTrue(r["passes"], (name, r))
                self.assertEqual(r["dominant_count"], 1, name)
                self.assertGreaterEqual(r["ratio"], 3.0, (name, r))
                self.assertEqual(r["dominant_font_px"], 132, name)

    def test_dominant_ratio_values(self):
        # BIG-NUMBER carries no body element -> body_reference falls back to 26
        # (ratio 132/26 = 5.08). RECEIPTS/CHECKLIST have body=30 (ratio 4.4).
        _, big = _render_fixture("fmt-big-number")
        self.assertAlmostEqual(
            measure.dominant_ratio_ok(big["surfaces"][0]["elements"])["ratio"],
            132 / 26, places=6)
        for name in ("fmt-receipts", "fmt-checklist"):
            _, m = _render_fixture(name)
            self.assertAlmostEqual(
                measure.dominant_ratio_ok(m["surfaces"][0]["elements"])["ratio"],
                132 / 30, places=6, msg=name)

    def test_raised_floors_met_for_every_non_wordmark_element(self):
        for name in _BATCH_A:
            _, manifest = _render_fixture(name)
            for s in manifest["surfaces"]:
                for e in s["elements"]:
                    if e["role"] == "wordmark":
                        continue
                    v = measure.format_slide_type_min(e["role"], e["font_px"])
                    self.assertTrue(v["passes"], (name, e["role"], e["font_px"]))

    def test_exactly_one_wordmark_per_slide(self):
        for name in _BATCH_A:
            _, manifest = _render_fixture(name)
            for s in manifest["surfaces"]:
                n = sum(1 for e in s["elements"] if e["role"] == "wordmark")
                self.assertEqual(n, 1, name)

    def test_wordmark_is_accent_deep_bottom_right(self):
        _, manifest = _render_fixture("fmt-big-number")
        wm = [e for e in manifest["surfaces"][0]["elements"]
              if e["role"] == "wordmark"][0]
        self.assertEqual(wm["text"], "TERREM")
        self.assertEqual(wm["color"], measure.TOKENS["accent-deep"])
        self.assertEqual(wm["font_px"], 26)


# --- Per-format grammar specifics (rows 2-3) -----------------------------------


class TestFormatGrammar(unittest.TestCase):
    def test_receipts_has_2_to_4_body_chips_on_surface_bg(self):
        _, manifest = _render_fixture("fmt-receipts")
        els = manifest["surfaces"][0]["elements"]
        chips = [e for e in els if e["role"] == "body"]
        self.assertTrue(2 <= len(chips) <= 4)
        # Chip text sits on the --surface token (white chip fill), weight 700.
        for c in chips:
            self.assertEqual(c["bg"], measure.TOKENS["surface"])
            self.assertEqual(c["weight"], 700)
            self.assertEqual(c["font_px"], 30)

    def test_dominant_is_the_single_accent_use(self):
        for name in _BATCH_A:
            _, manifest = _render_fixture(name)
            for s in manifest["surfaces"]:
                accents = [e for e in s["elements"]
                           if e["color"] == measure.TOKENS["accent"]]
                self.assertEqual(len(accents), 1, name)
                self.assertEqual(accents[0]["role"], "dominant", name)

    def test_checklist_has_at_least_two_step_body_elements(self):
        _, manifest = _render_fixture("fmt-checklist")
        els = manifest["surfaces"][0]["elements"]
        steps = [e for e in els if e["role"] == "body"]
        self.assertGreaterEqual(len(steps), 2)
        dom = [e for e in els if e["role"] == "dominant"]
        self.assertEqual(len(dom), 1)
        self.assertEqual(dom[0]["text"], "3")


# --- Schema structural acceptance (row 7) --------------------------------------


class TestSchemaAcceptance(unittest.TestCase):
    def test_emitted_v2_manifest_passes_validator_schema(self):
        import validate
        for name in _BATCH_A:
            _, manifest = _render_fixture(name)
            # Must not raise (structurally valid v2 manifest).
            validate._validate_manifest_schema(manifest, "<memory>")

    def test_every_color_and_bg_is_a_brand_token(self):
        for name in _BATCH_A:
            _, manifest = _render_fixture(name)
            for s in manifest["surfaces"]:
                for e in s["elements"]:
                    self.assertTrue(measure.is_brand_token(e["color"]),
                                    (name, e["color"]))
                    self.assertTrue(measure.is_brand_token(e["bg"]),
                                    (name, e["bg"]))
                    self.assertIn(e["color"], measure.TOKEN_HEXES, name)
                    self.assertIn(e["bg"], measure.TOKEN_HEXES, name)


# --- Determinism (row 8) -------------------------------------------------------


class TestDeterminism(unittest.TestCase):
    def test_rerender_pixel_and_manifest_identical(self):
        for name in _BATCH_A:
            imgs_a, man_a = _render_fixture(name)
            imgs_b, man_b = _render_fixture(name)
            for k in imgs_a:
                self.assertEqual(_rgba_sha(imgs_a[k]), _rgba_sha(imgs_b[k]),
                                 (name, k))
            self.assertEqual(
                json.dumps(man_a, sort_keys=True),
                json.dumps(man_b, sort_keys=True), name)

    def test_written_outputs_byte_identical_across_runs(self):
        for name in _BATCH_A:
            with tempfile.TemporaryDirectory() as ta, \
                 tempfile.TemporaryDirectory() as tb:
                da = Path(ta) / name
                db = Path(tb) / name
                shutil.copytree(_INPUTS / name, da)
                shutil.copytree(_INPUTS / name, db)
                ia, ma = render.render_asset(str(da))
                render.write_outputs(str(da), ia, ma)
                ib, mb = render.render_asset(str(db))
                render.write_outputs(str(db), ib, mb)
                pa = da / "render" / "format-01.png"
                pb = db / "render" / "format-01.png"
                self.assertEqual(_rgba_sha(Image.open(pa)),
                                 _rgba_sha(Image.open(pb)), name)
                self.assertEqual(
                    (da / "render" / "manifest.json").read_bytes(),
                    (db / "render" / "manifest.json").read_bytes(), name)


# --- Fail-loud invalid states + atomic no-partial-write (rows 9-16) ------------


class TestFailLoud(unittest.TestCase):
    def _assert_no_render_dir(self, folder):
        self.assertFalse((folder / "render").exists(),
                         "partial write left a render/ dir")

    def test_eleven_slides_fail_loud_no_write(self):
        blocks = "\n".join(
            "**F{} BIG-NUMBER**\nContext: c\nDominant: {}\nWordmark\n".format(i, i)
            for i in range(1, 12))
        with tempfile.TemporaryDirectory() as tmp:
            folder = _write_asset(tmp, blocks)
            with self.assertRaises(ValueError) as cm:
                render.render_asset(str(folder))
            self.assertIn("11", str(cm.exception))
            self.assertIn("10", str(cm.exception))
            self._assert_no_render_dir(folder)

    def test_no_dominant_fail_loud(self):
        text = "**F1 BIG-NUMBER**\nContext: only context\nWordmark\n"
        with tempfile.TemporaryDirectory() as tmp:
            folder = _write_asset(tmp, text)
            with self.assertRaises(ValueError) as cm:
                render.render_asset(str(folder))
            self.assertIn("dominant", str(cm.exception).lower())
            self._assert_no_render_dir(folder)

    def test_two_dominants_fail_loud(self):
        text = ("**F1 BIG-NUMBER**\nContext: c\nDominant: A\nDominant: B\n"
                "Wordmark\n")
        with tempfile.TemporaryDirectory() as tmp:
            folder = _write_asset(tmp, text)
            with self.assertRaises(ValueError) as cm:
                render.render_asset(str(folder))
            self.assertIn("dominant", str(cm.exception).lower())
            self._assert_no_render_dir(folder)

    def test_missing_wordmark_fail_loud(self):
        text = "**F1 BIG-NUMBER**\nContext: c\nDominant: A\n"
        with tempfile.TemporaryDirectory() as tmp:
            folder = _write_asset(tmp, text)
            with self.assertRaises(ValueError) as cm:
                render.render_asset(str(folder))
            self.assertIn("wordmark", str(cm.exception).lower())
            self._assert_no_render_dir(folder)

    def test_receipts_one_chip_fail_loud(self):
        text = ("**F1 RECEIPTS**\nDominant: A\nChip: only one\nWordmark\n")
        with tempfile.TemporaryDirectory() as tmp:
            folder = _write_asset(tmp, text)
            with self.assertRaises(ValueError) as cm:
                render.render_asset(str(folder))
            self.assertIn("2-4", str(cm.exception))
            self._assert_no_render_dir(folder)

    def test_receipts_five_chips_fail_loud(self):
        chips = "\n".join("Chip: item {}".format(i) for i in range(5))
        text = "**F1 RECEIPTS**\nDominant: A\n{}\nWordmark\n".format(chips)
        with tempfile.TemporaryDirectory() as tmp:
            folder = _write_asset(tmp, text)
            with self.assertRaises(ValueError) as cm:
                render.render_asset(str(folder))
            self.assertIn("2-4", str(cm.exception))
            self._assert_no_render_dir(folder)

    def test_checklist_one_step_fail_loud(self):
        text = ("**F1 CHECKLIST**\nDominant: 1\nStep: 1 only step\nWordmark\n")
        with tempfile.TemporaryDirectory() as tmp:
            folder = _write_asset(tmp, text)
            with self.assertRaises(ValueError) as cm:
                render.render_asset(str(folder))
            self.assertIn("Step", str(cm.exception))
            self._assert_no_render_dir(folder)

    def test_unknown_format_tag_fail_loud(self):
        # Sprint 003 conscious re-point (contract s0/row 19): TIMELINE now RENDERS,
        # so the "unknown tag fails loud" guarantee is re-proven against a
        # genuinely bogus tag (PIE-CHART). The behavior is preserved; only the
        # example tag moved. No assertion weakened.
        text = "**F1 PIE-CHART**\nDominant: A\nWordmark\n"
        with tempfile.TemporaryDirectory() as tmp:
            folder = _write_asset(tmp, text)
            with self.assertRaises(ValueError) as cm:
                render.render_asset(str(folder))
            msg = str(cm.exception)
            self.assertIn("PIE-CHART", msg)
            self.assertIn("F1", msg)
            self._assert_no_render_dir(folder)

    def test_batch_b_tags_now_render(self):
        # The positive half of the conscious flip (row 20): each batch-B tag that
        # Sprint 002 rejected now renders a 1080x1350 format-slide.
        for name in _BATCH_B:
            _, manifest = _render_fixture(name)
            self.assertEqual(manifest["schema_version"], "2", name)
            self.assertEqual(manifest["surfaces"][0]["format"],
                             _FORMAT_BY_FIXTURE[name], name)

    def test_unparseable_line_fail_loud(self):
        text = "**F1 BIG-NUMBER**\nContext: c\nDominant: A\nGarbledLine\nWordmark\n"
        with tempfile.TemporaryDirectory() as tmp:
            folder = _write_asset(tmp, text)
            with self.assertRaises(ValueError) as cm:
                render.render_asset(str(folder))
            msg = str(cm.exception)
            self.assertIn("F1", msg)
            self.assertIn("GarbledLine", msg)
            self._assert_no_render_dir(folder)

    def test_no_headers_fail_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = _write_asset(tmp, "just prose, no headers\n")
            with self.assertRaises(ValueError):
                render.render_asset(str(folder))
            self._assert_no_render_dir(folder)

    def test_missing_folder_fail_loud(self):
        with self.assertRaises(FileNotFoundError):
            render.render_asset("/tmp/does-not-exist-terrem-xyz")

    def test_empty_folder_no_renderable_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "empty"
            folder.mkdir()
            with self.assertRaises(FileNotFoundError):
                render.render_asset(str(folder))

    def test_exactly_ten_slides_ok(self):
        blocks = "\n".join(
            "**F{} BIG-NUMBER**\nContext: c\nDominant: {}\nWordmark\n".format(i, i)
            for i in range(1, 11))
        with tempfile.TemporaryDirectory() as tmp:
            folder = _write_asset(tmp, blocks)
            images, manifest = render.render_asset(str(folder))
            self.assertEqual(len(manifest["surfaces"]), 10)
            self.assertEqual(manifest["surfaces"][-1]["id"], "format-10")


# --- Anti-tofu guard (row 21) --------------------------------------------------


class TestAntiTofu(unittest.TestCase):
    def test_real_glyphs_render_no_false_tofu(self):
        # rupee + arrow + interpunct all present in vendored Inter -> no raise.
        _, manifest = _render_fixture("fmt-big-number")
        self.assertTrue(any("₹" in e["text"] for e in
                            manifest["surfaces"][0]["elements"]))

    def test_missing_glyph_raises(self):
        # A codepoint Inter lacks (CJK) must trip the tofu guard fail-loud.
        text = "**F1 BIG-NUMBER**\nContext: c\nDominant: 中文\nWordmark\n"
        with tempfile.TemporaryDirectory() as tmp:
            folder = _write_asset(tmp, text)
            with self.assertRaises(RuntimeError):
                render.render_asset(str(folder))
            self.assertFalse((folder / "render").exists())


# --- v1 byte-freeze (rows 18-19) -----------------------------------------------


class TestV1Freeze(unittest.TestCase):
    def _reference_manifest(self, slug):
        return json.loads(
            (_REPO / "content" / slug / "render" / "manifest.json")
            .read_text(encoding="utf-8"))

    def test_hyd_stays_schema_1_and_manifest_identical(self):
        slug = "2026-07-03-hyd-premium-vs-budget"
        committed = self._reference_manifest(slug)
        _, fresh = render.render_asset(str(_REPO / "content" / slug))
        self.assertEqual(fresh["schema_version"], "1")
        self.assertEqual(
            json.dumps(fresh, ensure_ascii=False, indent=2, sort_keys=True),
            json.dumps(committed, ensure_ascii=False, indent=2, sort_keys=True))

    def test_hyd_pngs_decoded_rgba_identical(self):
        slug = "2026-07-03-hyd-premium-vs-budget"
        rdir = _REPO / "content" / slug / "render"
        images, manifest = render.render_asset(str(_REPO / "content" / slug))
        for s in manifest["surfaces"]:
            committed = Image.open(rdir / s["png"])
            self.assertEqual(_rgba_sha(committed), _rgba_sha(images[s["png"]]),
                             s["png"])

    def test_tgrera_stays_schema_1(self):
        # Relocated to the retained v1 chart-card snapshot (Risk 2/C); the live
        # TGRERA folder is now a schema-v2 carousel by design.
        _, fresh = render.render_asset(str(_TGRERA_V1))
        self.assertEqual(fresh["schema_version"], "1")
        self.assertTrue(any(s["role"] == "chart-card" for s in fresh["surfaces"]))


# =============================================================================
# Sprint 003 — batch-B format library (TIMELINE, VS-CONTRAST, LEADERBOARD, CHART)
# =============================================================================


class TestBatchBCanvasSchema(unittest.TestCase):
    def test_each_batch_b_fixture_renders_1080x1350_format_slide(self):
        for name in _BATCH_B:
            images, manifest = _render_fixture(name)
            self.assertEqual(manifest["schema_version"], "2", name)
            self.assertEqual(len(manifest["surfaces"]), 1, name)
            s = manifest["surfaces"][0]
            self.assertEqual(s["role"], "format-slide", name)
            self.assertEqual(s["format"], _FORMAT_BY_FIXTURE[name], name)
            self.assertEqual(s["canvas"], {"w": 1080, "h": 1350}, name)
            self.assertIs(s["has_axis"], False, name)
            self.assertEqual(images[s["png"]].size, (1080, 1350), name)

    def test_no_pdf_key_this_sprint(self):
        # Sprint-004 conscious re-point (contract s0 / adversarial row 17), batch
        # B twin. Positive: v2 manifest carries pdf == "carousel.pdf". Preserved
        # negative: a schema "1" asset (tgrera chart-card) carries no pdf key.
        for name in _BATCH_B:
            _, manifest = _render_fixture(name)
            self.assertEqual(manifest["schema_version"], "2", name)
            self.assertEqual(manifest["pdf"], "carousel.pdf", name)
        _, v1 = render.render_asset(str(_TGRERA_V1))
        self.assertEqual(v1["schema_version"], "1")
        self.assertNotIn("pdf", v1)


class TestBatchBDominantAndFloors(unittest.TestCase):
    def test_exactly_one_dominant_over_3x_via_measure(self):
        for name in _BATCH_B:
            _, manifest = _render_fixture(name)
            for s in manifest["surfaces"]:
                r = measure.dominant_ratio_ok(s["elements"])
                self.assertTrue(r["passes"], (name, r))
                self.assertEqual(r["dominant_count"], 1, name)
                self.assertGreaterEqual(r["ratio"], 3.0, (name, r))
                self.assertEqual(r["dominant_font_px"], 132, name)

    def test_ratio_values_per_format(self):
        # TIMELINE/VS-CONTRAST/LEADERBOARD carry body=30 -> 132/30 = 4.40.
        # CHART is body-free (labels are chart-label) -> fallback 26 -> 132/26.
        for name in ("fmt-timeline", "fmt-vs-contrast", "fmt-leaderboard"):
            _, m = _render_fixture(name)
            self.assertAlmostEqual(
                measure.dominant_ratio_ok(m["surfaces"][0]["elements"])["ratio"],
                132 / 30, places=6, msg=name)
        _, chart = _render_fixture("fmt-chart")
        r = measure.dominant_ratio_ok(chart["surfaces"][0]["elements"])
        self.assertEqual(r["body_reference"], 26)
        self.assertAlmostEqual(r["ratio"], 132 / 26, places=6)

    def test_raised_floors_met_for_every_non_wordmark_element(self):
        for name in _BATCH_B:
            _, manifest = _render_fixture(name)
            for s in manifest["surfaces"]:
                for e in s["elements"]:
                    if e["role"] == "wordmark":
                        continue
                    v = measure.format_slide_type_min(e["role"], e["font_px"])
                    self.assertTrue(v["passes"], (name, e["role"], e["font_px"]))

    def test_exactly_one_wordmark_and_one_dominant(self):
        for name in _BATCH_B:
            _, manifest = _render_fixture(name)
            for s in manifest["surfaces"]:
                els = s["elements"]
                self.assertEqual(sum(1 for e in els if e["role"] == "wordmark"),
                                 1, name)
                self.assertEqual(sum(1 for e in els if e["role"] == "dominant"),
                                 1, name)

    def test_dominant_is_the_single_accent(self):
        for name in _BATCH_B:
            _, manifest = _render_fixture(name)
            for s in manifest["surfaces"]:
                accents = [e for e in s["elements"]
                           if e["color"] == measure.TOKENS["accent"]]
                self.assertEqual(len(accents), 1, name)
                self.assertEqual(accents[0]["role"], "dominant", name)


class TestBatchBGrammar(unittest.TestCase):
    def test_timeline_has_ge2_event_body_chips(self):
        _, m = _render_fixture("fmt-timeline")
        els = m["surfaces"][0]["elements"]
        chips = [e for e in els if e["role"] == "body"]
        self.assertGreaterEqual(len(chips), 2)
        for c in chips:  # event chips reuse the RECEIPTS chip primitive
            self.assertEqual(c["bg"], measure.TOKENS["surface"])
            self.assertEqual(c["weight"], 700)
            self.assertEqual(c["font_px"], 30)

    def test_vs_contrast_asymmetry(self):
        _, m = _render_fixture("fmt-vs-contrast")
        els = m["surfaces"][0]["elements"]
        dom = [e for e in els if e["role"] == "dominant"]
        head = [e for e in els if e["role"] == "headline"]
        labels = [e for e in els if e["role"] == "body"]
        self.assertEqual(len(dom), 1)
        self.assertEqual(dom[0]["font_px"], 132)
        self.assertEqual(len(head), 1)          # exactly one opposing number
        self.assertEqual(head[0]["font_px"], 52)
        self.assertGreaterEqual(len(labels), 2)  # two side labels

    def test_leaderboard_rows_are_body_non_chip_single_accent(self):
        _, m = _render_fixture("fmt-leaderboard")
        els = m["surfaces"][0]["elements"]
        rows = [e for e in els if e["role"] == "body"]
        self.assertGreaterEqual(len(rows), 2)
        for r in rows:  # rows are plain body (not chips), ink-muted, no accent
            self.assertFalse(r.get("is_chip"))
            self.assertEqual(r["color"], measure.TOKENS["ink-muted"])
            self.assertEqual(r["font_px"], 30)

    def test_chart_manifest_has_no_phantom_bar_elements(self):
        # Bars are DECORATIVE primitives, not manifest elements (row 5).
        _, m = _render_fixture("fmt-chart")
        s = m["surfaces"][0]
        roles = sorted(e["role"] for e in s["elements"])
        self.assertIn("chart-label", roles)
        self.assertEqual(roles.count("dominant"), 1)
        self.assertGreaterEqual(
            sum(1 for e in s["elements"] if e["role"] == "chart-label"), 2)
        self.assertTrue(all(r in {"headline", "dominant", "chart-label",
                                  "source-stamp", "wordmark"} for r in roles), roles)
        # chart-labels are drawn on --bg (never on the colored bar).
        for e in s["elements"]:
            if e["role"] == "chart-label":
                self.assertEqual(e["bg"], measure.TOKENS["bg"])
                self.assertEqual(e["color"], measure.TOKENS["ink"])

    def test_chart_draws_chart_up_bar_pixels(self):
        images, m = _render_fixture("fmt-chart")
        img = images[m["surfaces"][0]["png"]].convert("RGB")
        chart_up = tuple(int(measure.TOKENS["chart-up"][i:i + 2], 16)
                         for i in (1, 3, 5))
        colors = {c for _, c in img.getcolors(maxcolors=100000)}
        self.assertIn(chart_up, colors)  # real --chart-up bar ink present

    def test_vs_contrast_draws_border_divider_pixels(self):
        images, m = _render_fixture("fmt-vs-contrast")
        img = images[m["surfaces"][0]["png"]].convert("RGB")
        border = tuple(int(measure.TOKENS["border"][i:i + 2], 16)
                       for i in (1, 3, 5))
        colors = {c for _, c in img.getcolors(maxcolors=100000)}
        self.assertIn(border, colors)  # decorative --border divider present


class TestBatchBSchemaAndTokens(unittest.TestCase):
    def test_emitted_manifest_passes_validator_schema(self):
        import validate
        for name in _BATCH_B:
            _, manifest = _render_fixture(name)
            validate._validate_manifest_schema(manifest, "<memory>")

    def test_every_color_and_bg_is_a_brand_token(self):
        for name in _BATCH_B:
            _, manifest = _render_fixture(name)
            for s in manifest["surfaces"]:
                for e in s["elements"]:
                    self.assertIn(e["color"], measure.TOKEN_HEXES, name)
                    self.assertIn(e["bg"], measure.TOKEN_HEXES, name)


class TestBatchBDeterminism(unittest.TestCase):
    def test_rerender_pixel_and_manifest_identical(self):
        for name in _BATCH_B:
            imgs_a, man_a = _render_fixture(name)
            imgs_b, man_b = _render_fixture(name)
            for k in imgs_a:
                self.assertEqual(_rgba_sha(imgs_a[k]), _rgba_sha(imgs_b[k]),
                                 (name, k))
            self.assertEqual(json.dumps(man_a, sort_keys=True),
                             json.dumps(man_b, sort_keys=True), name)

    def test_written_outputs_byte_identical_across_runs(self):
        for name in _BATCH_B:
            with tempfile.TemporaryDirectory() as ta, \
                 tempfile.TemporaryDirectory() as tb:
                da = Path(ta) / name
                db = Path(tb) / name
                shutil.copytree(_INPUTS / name, da)
                shutil.copytree(_INPUTS / name, db)
                ia, ma = render.render_asset(str(da))
                render.write_outputs(str(da), ia, ma)
                ib, mb = render.render_asset(str(db))
                render.write_outputs(str(db), ib, mb)
                pa = da / "render" / "format-01.png"
                pb = db / "render" / "format-01.png"
                self.assertEqual(_rgba_sha(Image.open(pa)),
                                 _rgba_sha(Image.open(pb)), name)
                self.assertEqual(
                    (da / "render" / "manifest.json").read_bytes(),
                    (db / "render" / "manifest.json").read_bytes(), name)


class TestBatchBFailLoud(unittest.TestCase):
    def _assert_no_render_dir(self, folder):
        self.assertFalse((folder / "render").exists(),
                         "partial write left a render/ dir")

    def _expect_value_error(self, text, *needles):
        with tempfile.TemporaryDirectory() as tmp:
            folder = _write_asset(tmp, text)
            with self.assertRaises(ValueError) as cm:
                render.render_asset(str(folder))
            msg = str(cm.exception)
            for n in needles:
                self.assertIn(n, msg)
            self._assert_no_render_dir(folder)

    def test_chart_bar_without_numeric_fail_loud(self):
        self._expect_value_error(
            "**F1 CHART**\nDominant: X\nBar: no number here\n"
            "Bar: Kokapet · 5\nSource: s\nWordmark\n", "F1", "numeric")

    def test_chart_one_bar_fail_loud(self):
        self._expect_value_error(
            "**F1 CHART**\nDominant: X\nBar: only · 5\nSource: s\nWordmark\n",
            "F1", "2 Bar")

    def test_chart_missing_source_fail_loud(self):
        self._expect_value_error(
            "**F1 CHART**\nDominant: X\nBar: a · 5\nBar: b · 3\nWordmark\n",
            "F1", "Source")

    def test_timeline_one_event_fail_loud(self):
        self._expect_value_error(
            "**F1 TIMELINE**\nDominant: 9 days\nEvent: only one\nWordmark\n",
            "F1", "2 Event")

    def test_leaderboard_one_row_fail_loud(self):
        self._expect_value_error(
            "**F1 LEADERBOARD**\nDominant: Top\nRow: 2 · only\nWordmark\n",
            "F1", "2 Row")

    def test_vs_contrast_zero_headline_fail_loud(self):
        self._expect_value_error(
            "**F1 VS-CONTRAST**\nBody: A\nBody: B\nDominant: 9\nWordmark\n",
            "F1", "headline")

    def test_vs_contrast_two_headlines_fail_loud(self):
        self._expect_value_error(
            "**F1 VS-CONTRAST**\nBody: A\nBody: B\nDominant: 9\n"
            "Headline: 4\nHeadline: 5\nWordmark\n", "F1", "headline")

    def test_vs_contrast_one_body_label_fail_loud(self):
        self._expect_value_error(
            "**F1 VS-CONTRAST**\nBody: A\nDominant: 9\nHeadline: 4\nWordmark\n",
            "F1", "Body")

    def test_batch_b_zero_dominant_fail_loud(self):
        self._expect_value_error(
            "**F1 TIMELINE**\nEvent: a · 1\nEvent: b · 2\nWordmark\n",
            "F1", "dominant")

    def test_batch_b_two_dominants_fail_loud(self):
        self._expect_value_error(
            "**F1 LEADERBOARD**\nDominant: A\nDominant: B\nRow: 2 · x\n"
            "Row: 3 · y\nWordmark\n", "F1", "dominant")

    def test_batch_b_missing_wordmark_fail_loud(self):
        self._expect_value_error(
            "**F1 CHART**\nDominant: X\nBar: a · 5\nBar: b · 3\nSource: s\n",
            "F1", "wordmark")

    def test_bogus_tag_pie_chart_fail_loud(self):
        self._expect_value_error(
            "**F1 PIE-CHART**\nDominant: A\nWordmark\n", "F1", "PIE-CHART")

    def test_mixed_ab_eleven_slides_fail_loud(self):
        # R14 inherited: 11 mixed batch-A/B slides fail loud, no partial write.
        fmts = ["BIG-NUMBER", "TIMELINE", "LEADERBOARD"]
        blocks = []
        for i in range(1, 12):
            f = fmts[i % len(fmts)]
            if f == "BIG-NUMBER":
                blocks.append(
                    "**F{} BIG-NUMBER**\nContext: c\nDominant: {}\nWordmark".format(i, i))
            elif f == "TIMELINE":
                blocks.append(
                    "**F{} TIMELINE**\nDominant: {}\nEvent: a · 1\nEvent: b · 2\n"
                    "Wordmark".format(i, i))
            else:
                blocks.append(
                    "**F{} LEADERBOARD**\nDominant: {}\nRow: 2 · x\nRow: 3 · y\n"
                    "Wordmark".format(i, i))
        self._expect_value_error("\n".join(blocks) + "\n", "11", "10")


class TestBatchBValidateGuardAndFreeze(unittest.TestCase):
    def test_validate_flows_batch_b_through_v13_v19(self):
        # CONSCIOUS RE-POINT (Sprint 005, Risk C): the Sprint-002 exit-2 guard is
        # REMOVED — a batch-B v2 asset no longer raises PreconditionError; it now
        # flows through the QA Gate V2 checks and reaches a real verdict. This
        # test's intent (v2 assets are HANDLED by validate) is preserved, only its
        # assertion moves from "cited exit 2" to "real verdict with V13-V19 wired".
        import json as _json
        import validate
        for name in _BATCH_B:
            with tempfile.TemporaryDirectory() as tmp:
                da = Path(tmp) / name
                shutil.copytree(_INPUTS / name, da)
                imgs, man = render.render_asset(str(da))
                render.write_outputs(str(da), imgs, man)
                code = validate.run(str(da), "2026-07-06", "test")  # no raise
                self.assertIn(code, (0, 1))
                doc = _json.loads((da / "render" / "qa-verdict.json").read_text())
                ids = {c["id"] for c in doc["checks"]}
                self.assertIn("V13-dominant-ratio", ids)
                self.assertIn("V14-wordmark", ids)

    def test_v1_freeze_still_holds(self):
        # The batch-B additions must not perturb the v1 assets. hyd stays live;
        # tgrera's chart-card freeze is re-proven against the retained v1
        # snapshot (Risk 2/C) — the live TGRERA folder is now schema-v2.
        for da in (_REPO / "content" / "2026-07-03-hyd-premium-vs-budget",
                   _TGRERA_V1):
            _, fresh = render.render_asset(str(da))
            self.assertEqual(fresh["schema_version"], "1", str(da))


# ============================================================================
# Sprint 004 — deterministic multi-page carousel.pdf (R15/R16/R18/R19).
# ============================================================================
# NOTE: Pillow 11.3.0 can SAVE but NOT OPEN PDFs ('PDF' in Image.OPEN is False).
# The contract s7(c)/(d) verification snippets use Image.open(...pdf)/n_frames,
# which raise UnidentifiedImageError on this (and every) Pillow. These tests
# therefore verify page count/order via stdlib byte-parsing of the PDF, never
# Image.open. The emitted PDF is nonetheless a valid PDF 1.4 (pdfinfo reads it:
# "Pages: 3", "Page size: 1080 x 1350 pts"). See generator_trace.log for the
# drop-in byte-parse replacement for the contract's Image.open commands.

_PDF_MULTI = "fmt-multi"   # the new 3-slide fixture (page-count > 1 proof)


def _byte_page_count(pdf_bytes):
    """Return the PDF page count triangulated from three independent byte signals
    that MUST agree: the /Pages tree /Count, the number of /Type /Page (not
    /Pages) objects, and the number of /MediaBox entries. Returns an int; raises
    AssertionError-friendly disagreement is surfaced by the caller."""
    count_m = re.search(rb"/Count\s+(\d+)", pdf_bytes)
    count = int(count_m.group(1)) if count_m else -1
    page_objs = len(re.findall(rb"/Type\s*/Page(?![s])", pdf_bytes))
    mediaboxes = len(re.findall(rb"/MediaBox\s*\[", pdf_bytes))
    return count, page_objs, mediaboxes


def _render_to_tmp(tmp, fixture):
    """Render an inputs/ fixture into a fresh temp asset dir; return the render
    dir Path (holding format-NN.png, manifest.json, carousel.pdf)."""
    da = Path(tmp) / fixture
    shutil.copytree(_INPUTS / fixture, da)
    imgs, man = render.render_asset(str(da))
    render.write_outputs(str(da), imgs, man)
    return da / "render", man


class TestCarouselPdfEmission(unittest.TestCase):
    """Matrix rows 1-3, 10: PDF exists, starts %PDF, page count == slide count,
    manifest pdf key present on v2."""

    def test_pdf_emitted_and_is_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            render_dir, man = _render_to_tmp(tmp, _PDF_MULTI)
            pdf = render_dir / "carousel.pdf"
            self.assertTrue(pdf.exists(), "carousel.pdf not emitted")
            self.assertTrue(pdf.read_bytes()[:8].startswith(b"%PDF"))
            self.assertEqual(man.get("pdf"), "carousel.pdf")

    def test_page_count_equals_slide_count_all_v2_fixtures(self):
        for fixture in _ALL_FIXTURES + (_PDF_MULTI,):
            with tempfile.TemporaryDirectory() as tmp:
                render_dir, man = _render_to_tmp(tmp, fixture)
                n_slides = sum(1 for s in man["surfaces"]
                               if s["role"] == "format-slide")
                pdf_bytes = (render_dir / "carousel.pdf").read_bytes()
                count, page_objs, mediaboxes = _byte_page_count(pdf_bytes)
                # All three independent signals agree and equal the slide count.
                self.assertEqual(count, n_slides, (fixture, "/Count"))
                self.assertEqual(page_objs, n_slides, (fixture, "/Type/Page"))
                self.assertEqual(mediaboxes, n_slides, (fixture, "/MediaBox"))

    def test_fmt_multi_has_three_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            render_dir, _ = _render_to_tmp(tmp, _PDF_MULTI)
            count, page_objs, mediaboxes = _byte_page_count(
                (render_dir / "carousel.pdf").read_bytes())
            self.assertEqual((count, page_objs, mediaboxes), (3, 3, 3))

    def test_every_page_is_1080x1350(self):
        # MediaBox is 0 0 1080 1350 for every page (72 dpi default -> pt == px).
        with tempfile.TemporaryDirectory() as tmp:
            render_dir, _ = _render_to_tmp(tmp, _PDF_MULTI)
            boxes = re.findall(
                rb"/MediaBox\s*\[\s*0\s+0\s+1080(?:\.0)?\s+1350(?:\.0)?\s*\]",
                (render_dir / "carousel.pdf").read_bytes())
            self.assertEqual(len(boxes), 3)


class TestPdfPageOrderAndMixed(unittest.TestCase):
    """Matrix rows 4, 16: page order == manifest surface order; a mixed asset's
    PDF pages are the format-slide surfaces ONLY (order proven at the seam)."""

    def test_page_source_order_at_the_seam(self):
        with tempfile.TemporaryDirectory() as tmp:
            da = Path(tmp) / _PDF_MULTI
            shutil.copytree(_INPUTS / _PDF_MULTI, da)
            imgs, man = render.render_asset(str(da))
            pages = render._format_slide_pdf_pages(imgs, man)
            fmt_surfaces = [s for s in man["surfaces"]
                            if s["role"] == "format-slide"]
            self.assertEqual(len(pages), len(fmt_surfaces))
            # Page i is the exact in-memory raster of format-0(i+1).png, in order.
            for i, s in enumerate(fmt_surfaces):
                self.assertIs(pages[i], imgs[s["png"]])
                self.assertEqual(s["png"], "format-{:02d}.png".format(i + 1))

    def test_mixed_asset_pdf_pages_are_format_slides_only(self):
        # A folder with BOTH carousel.md (carousel-slide) and formats.md
        # (format-slide) -> schema "2", PDF pages = format-slide surfaces only;
        # no carousel-slide raster ever enters the PDF (contract s1.5 mixed rule).
        with tempfile.TemporaryDirectory() as tmp:
            da = Path(tmp) / "mixed"
            da.mkdir()
            (da / "carousel.md").write_text(
                "**S1 cover**\n> Reactive single line hook\nWordmark\n",
                encoding="utf-8")
            shutil.copy(_INPUTS / _PDF_MULTI / "formats.md", da / "formats.md")
            imgs, man = render.render_asset(str(da))
            self.assertEqual(man["schema_version"], "2")
            self.assertEqual(man.get("pdf"), "carousel.pdf")
            pages = render._format_slide_pdf_pages(imgs, man)
            fmt = [s for s in man["surfaces"] if s["role"] == "format-slide"]
            carousel = [s for s in man["surfaces"]
                        if s["role"] == "carousel-slide"]
            self.assertTrue(len(carousel) >= 1)         # carousel-slide present
            self.assertEqual(len(pages), len(fmt))       # but not in the PDF
            for p, s in zip(pages, fmt):
                self.assertIs(p, imgs[s["png"]])


class TestPdfDeterminismAndMetadata(unittest.TestCase):
    """Matrix rows 5-9: cross-process byte-determinism (R16), same-process
    determinism (subset), no per-run CreationDate/ModDate/ID, fixed producer."""

    def test_cross_process_byte_identical(self):
        # R16: two INDEPENDENT render.py process invocations of the same input
        # into two different parent dirs with identical basename -> byte-identical
        # carousel.pdf. A same-process BytesIO round-trip would NOT prove this
        # (contract s1.3); the real save path (Title else filename-derived) is
        # exercised only cross-process.
        render_py = str(_TOOL_DIR / "render.py")
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a" / _PDF_MULTI
            b = Path(tmp) / "b" / _PDF_MULTI
            for d in (a, b):
                d.mkdir(parents=True)
                shutil.copy(_INPUTS / _PDF_MULTI / "formats.md", d / "formats.md")
                r = subprocess.run(
                    [sys.executable, render_py, str(d)],
                    capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
            pa = (a / "render" / "carousel.pdf").read_bytes()
            pb = (b / "render" / "carousel.pdf").read_bytes()
            self.assertEqual(pa, pb, "cross-process PDF bytes differ (R16)")

    def test_same_process_re_render_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            r1, _ = _render_to_tmp(tmp, _PDF_MULTI)
            b1 = (r1 / "carousel.pdf").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            r2, _ = _render_to_tmp(tmp, _PDF_MULTI)
            b2 = (r2 / "carousel.pdf").read_bytes()
        self.assertEqual(b1, b2)

    def test_no_per_run_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            render_dir, _ = _render_to_tmp(tmp, _PDF_MULTI)
            b = (render_dir / "carousel.pdf").read_bytes()
            self.assertNotIn(b"CreationDate", b, "CreationDate leaked")
            self.assertNotIn(b"ModDate", b, "ModDate leaked")
            self.assertNotIn(b"/ID", b, "run-varying document /ID present")
            self.assertIn(b"created by Pillow", b)   # fixed producer comment
            self.assertIn(b"/Producer", b)
            self.assertIn(b"/Title", b)


class TestPdfFreezeAndAtomicity(unittest.TestCase):
    """Matrix rows 11-13, 15: v1 emits no PDF/no pdf key; freeze holds; an
    11-slide formats.md fails loud leaving no render/ dir (no partial PDF)."""

    def test_v1_assets_emit_no_pdf(self):
        # hyd stays live; tgrera relocated to the retained v1 snapshot (Risk 2/C).
        for src in (_REPO / "content" / "2026-07-03-hyd-premium-vs-budget",
                    _TGRERA_V1):
            slug = src.name
            with tempfile.TemporaryDirectory() as tmp:
                da = Path(tmp) / slug
                shutil.copytree(src, da)
                imgs, man = render.render_asset(str(da))
                self.assertEqual(man["schema_version"], "1", slug)
                self.assertNotIn("pdf", man, slug)
                render.write_outputs(str(da), imgs, man)
                self.assertFalse((da / "render" / "carousel.pdf").exists(), slug)

    def test_11_slides_fail_loud_no_partial_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            da = Path(tmp) / "over"
            da.mkdir()
            blocks = []
            for i in range(1, 12):
                blocks.append(
                    "**F{} BIG-NUMBER**\nContext: c\nDominant: {}\n"
                    "Wordmark".format(i, i))
            (da / "formats.md").write_text("\n\n".join(blocks) + "\n",
                                           encoding="utf-8")
            with self.assertRaises(ValueError):
                render.render_asset(str(da))
            # render_asset raised before any write_outputs -> no render/ dir.
            self.assertFalse((da / "render").exists(), "partial render/ dir left")


if __name__ == "__main__":
    unittest.main()
