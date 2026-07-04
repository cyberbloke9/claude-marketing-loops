#!/usr/bin/env python3
"""Validator CLI for the TERREM marketing-loop Asset Renderer + QA Gate.

Sprint 004. Consumes the renderer->validator seam
(``content/<slug>/render/manifest.json`` + the real PNG bytes + the asset's
``*.md`` specs) and runs checks **V2-V12** (spec s5.2). Emits two consumer seams:
a machine-readable ``render/qa-verdict.json`` (spec s5.4) and a human-readable
verdict block appended idempotently into the asset's ``meta.md`` (contract s5.3).

Headless CLI. No browser, no network, no third-party dependency beyond Pillow.
Imports only stdlib + ``PIL`` + the local ``measure`` module (used verbatim).
The Inter precedence rule (Risk 1) is enforced by NOT implementing any
font-family check (font family is not recoverable from raster pixels); the stale
``qa-checklist.md`` line is corrected as a source edit, not a runtime assertion.

Exit codes:
    0  overall verdict PASS
    1  overall verdict FAIL (>=1 applicable check FAILed) -- a valid verdict was
       still written
    2  usage / precondition error (missing folder, missing manifest/PNG,
       malformed manifest, color outside token set) -- nothing was written

Usage:
    python3 tools/marketing-render/validate.py <asset-folder> \
        [--checked-on YYYY-MM-DD] [--checked-by NAME]

Spec refs: s5.2 (V2-V12), s5.3 (manifest schema consumed), s5.4 (qa-verdict.json
produced), s6 (states), s7 (tone), s9 (tokens/no-network); contract s3-s6.
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

from PIL import Image

# Local measurement module (Sprint 001) lives beside this file.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import measure  # noqa: E402

# Repo root (validate.py at tools/marketing-render/validate.py -> parents[2]).
_REPO_ROOT = _HERE.parent.parent
_BRAND_KIT = _REPO_ROOT / "brand" / "brand-kit.md"
_QA_CHECKLIST = _REPO_ROOT / "brand" / "qa-checklist.md"


# --- Calibrated pixel-measurement constants (contract s4.3/s4.5, R-A/R-B) -------
# Calibrated on the real TGRERA render (see generator_trace.log): every real
# element clears INK_MIN_PX with wide margin (smallest real = wordmark 804px),
# a blank crop yields 0 ink -> FAIL. K_INTER centres the ink-band/font_px ratio
# between all-caps (~0.72, wordmark) and mixed-case descender lines (~0.955,
# headline) so all real elements land inside the +/-25% band, while a 2x lie
# falls outside it.
INK_TOL = 60          # max Euclidean RGB distance from declared color to count "ink"
INK_MIN_PX = 50       # min matching pixels inside a bbox for V3 ink-present
K_INTER = 0.83        # median ink-band height / declared font_px (Inter)
BAND_GAP = 3          # >= this many blank rows separates two text-line ink bands

# Required format per surface role (V2).
_FORMAT_BY_ROLE = {
    "carousel-slide": (1080, 1350),
    "chart-card": (1080, 1920),
}

# V6 applies only to these element roles; the rest are exempt (skipped).
_SAFEZONE_ROLES = frozenset({"headline", "body", "hook"})

# Roles the manifest may declare (schema s5.3).
_ELEMENT_ROLES = frozenset(
    {"headline", "hook", "body", "source-stamp", "wordmark", "chart-label"}
)
_SURFACE_ROLES = frozenset({"carousel-slide", "chart-card"})

# V8 date-token detectors (presence-based, Risk C).
_ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_MONTH_DAY_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}\b",
    re.IGNORECASE,
)

# Verdict-block markers in meta.md (idempotent replace, contract s5.3).
_VERDICT_START = "<!-- qa-verdict:start -->"
_VERDICT_END = "<!-- qa-verdict:end -->"

# Provenance-block markers in meta.md (V11, contract s4.11).
_PROV_START = "<!-- provenance:start -->"
_PROV_END = "<!-- provenance:end -->"
_PROV_REQUIRED_KEYS = ("sources", "terrem_db_numbers", "as_of")


class PreconditionError(Exception):
    """Raised for exit-2 states (contract s6): missing/malformed inputs."""


# --- Small pure helpers --------------------------------------------------------


def _hex_rgb(hexstr):
    h = measure.normalize_hex(hexstr)[1:]
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _crop_rows_ink(png, bbox, color_rgb):
    """Return ``(ink_count, [row_has_ink...])`` for a bbox crop of ``png``.

    A pixel is "ink" if its Euclidean RGB distance from ``color_rgb`` is
    ``<= INK_TOL``. ``row_has_ink[i]`` is True iff crop row ``i`` holds any ink.
    """
    x, y, w, h = bbox
    x = max(0, x)
    y = max(0, y)
    crop = png.crop((x, y, x + w, y + h))
    cw, ch = crop.size
    px = list(crop.getdata())
    cr, cg, cb = color_rgb
    tol2 = INK_TOL * INK_TOL
    ink_count = 0
    row_has_ink = [False] * ch
    for ry in range(ch):
        base = ry * cw
        row_ink = False
        for rx in range(cw):
            r, g, b = px[base + rx][:3]
            if (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2 <= tol2:
                ink_count += 1
                row_ink = True
        row_has_ink[ry] = row_ink
    return ink_count, row_has_ink


def _median_band_height(row_has_ink):
    """Median ink-band height (one text line's vertical extent) or ``None``.

    Contiguous inked rows form a band; ``>= BAND_GAP`` blank rows separate bands
    (multi-line elements yield one band per line). Returns median band height
    across all bands, or ``None`` when no ink band exists.
    """
    bands = []
    start = None
    blank = 0
    for i, val in enumerate(row_has_ink):
        if val:
            if start is None:
                start = i
            blank = 0
        else:
            if start is not None:
                blank += 1
                if blank >= BAND_GAP:
                    bands.append(i - blank + 1 - start)
                    start = None
                    blank = 0
    if start is not None:
        bands.append(len(row_has_ink) - blank - start)
    if not bands:
        return None
    bands.sort()
    return bands[len(bands) // 2]


def _has_source_and_date(text):
    """V8 presence rule: text carries a source cue AND a date token."""
    has_source = ("source" in text.lower()) or ("·" in text)
    has_date = bool(_ISO_DATE_RE.search(text)) or bool(_MONTH_DAY_RE.search(text))
    return has_source and has_date


# --- Loading + schema validation (exit-2 states, contract s6) -------------------


def _read_text(path):
    return path.read_text(encoding="utf-8")


def load_asset(asset_folder):
    """Load manifest + PNGs + specs. Raise ``PreconditionError`` for exit-2 states.

    Returns a dict with keys: ``folder, slug, manifest, images (png-name->PIL),
    meta_text, copy_text``.
    """
    folder = Path(asset_folder)
    if not folder.is_dir():
        raise PreconditionError("asset folder not found: {}".format(asset_folder))

    render_dir = folder / "render"
    manifest_path = render_dir / "manifest.json"
    if not manifest_path.is_file():
        raise PreconditionError(
            "manifest/PNG not found; run render first: {}".format(manifest_path)
        )

    try:
        manifest = json.loads(_read_text(manifest_path))
    except (ValueError, UnicodeDecodeError) as exc:
        raise PreconditionError(
            "malformed manifest (unparseable JSON) {}: {}".format(manifest_path, exc)
        )

    _validate_manifest_schema(manifest, manifest_path)

    # Load every referenced PNG (must exist).
    images = {}
    for surf in manifest["surfaces"]:
        png_name = surf["png"]
        png_path = render_dir / png_name
        if not png_path.is_file():
            raise PreconditionError(
                "manifest/PNG not found; run render first: {}".format(png_path)
            )
        try:
            img = Image.open(png_path)
            img.load()
            images[png_name] = img.convert("RGB")
        except Exception as exc:  # noqa: BLE001 - any decode failure is a precondition error
            raise PreconditionError(
                "malformed PNG {}: {}".format(png_path, exc)
            )

    meta_path = folder / "meta.md"
    meta_text = _read_text(meta_path) if meta_path.is_file() else ""

    # V9 corpus: carousel.md, script.md, chart-spec.md (those that exist).
    # Deliberately NOT meta.md (it receives the appended verdict block -> circular).
    copy_parts = []
    for name in ("carousel.md", "script.md", "chart-spec.md"):
        p = folder / name
        if p.is_file():
            copy_parts.append(_read_text(p))

    return {
        "folder": folder,
        "slug": manifest["slug"],
        "manifest": manifest,
        "images": images,
        "meta_text": meta_text,
        "copy_text": "\n".join(copy_parts),
    }


def _validate_manifest_schema(manifest, path):
    """Structural + token validation. Raise ``PreconditionError`` naming the field.

    Tolerates unknown extra fields (e.g. ``chart_ref``): only required fields are
    enforced; extras are ignored.
    """
    if not isinstance(manifest, dict):
        raise PreconditionError("malformed manifest: top level is not an object")
    for key in ("schema_version", "slug", "surfaces"):
        if key not in manifest:
            raise PreconditionError(
                "malformed manifest: missing top-level field '{}' in {}".format(key, path)
            )
    if not isinstance(manifest["surfaces"], list) or not manifest["surfaces"]:
        raise PreconditionError("malformed manifest: 'surfaces' must be a non-empty list")

    for si, surf in enumerate(manifest["surfaces"]):
        where = "surfaces[{}]".format(si)
        if not isinstance(surf, dict):
            raise PreconditionError("malformed manifest: {} is not an object".format(where))
        for key in ("id", "role", "png", "canvas", "elements"):
            if key not in surf:
                raise PreconditionError(
                    "malformed manifest: {} missing field '{}'".format(where, key)
                )
        if surf["role"] not in _SURFACE_ROLES:
            raise PreconditionError(
                "malformed manifest: {} has unknown surface role '{}'".format(
                    where, surf["role"]
                )
            )
        canvas = surf["canvas"]
        if not isinstance(canvas, dict) or "w" not in canvas or "h" not in canvas:
            raise PreconditionError(
                "malformed manifest: {}.canvas must have w and h".format(where)
            )
        if not isinstance(surf["elements"], list):
            raise PreconditionError(
                "malformed manifest: {}.elements must be a list".format(where)
            )
        for ei, el in enumerate(surf["elements"]):
            ewhere = "{}.elements[{}]".format(where, ei)
            if not isinstance(el, dict):
                raise PreconditionError(
                    "malformed manifest: {} is not an object".format(ewhere)
                )
            for key in ("text", "role", "font_px", "weight", "color", "bg", "bbox"):
                if key not in el:
                    raise PreconditionError(
                        "malformed manifest: {} missing field '{}'".format(ewhere, key)
                    )
            if el["role"] not in _ELEMENT_ROLES:
                raise PreconditionError(
                    "malformed manifest: {}.role unknown value '{}'".format(
                        ewhere, el["role"]
                    )
                )
            if not isinstance(el["font_px"], (int, float)) or el["font_px"] <= 0:
                raise PreconditionError(
                    "malformed manifest: {}.font_px must be a positive number".format(ewhere)
                )
            bbox = el["bbox"]
            if not isinstance(bbox, list) or len(bbox) != 4:
                raise PreconditionError(
                    "malformed manifest: {}.bbox must be [x, y, w, h]".format(ewhere)
                )
            # Token rule (schema s5.3): color and bg must both be brand tokens.
            for field in ("color", "bg"):
                val = el[field]
                try:
                    is_tok = measure.is_brand_token(val)
                except ValueError:
                    is_tok = False
                if not is_tok:
                    raise PreconditionError(
                        "malformed manifest: {}.{} = {!r} is not a brand token".format(
                            ewhere, field, val
                        )
                    )


# --- Check-record plumbing -----------------------------------------------------


def _rec(checks, cid, surface, status, detail, rule, bbox=None):
    rec = {"id": cid, "surface": surface, "status": status, "detail": detail, "rule": rule}
    if bbox is not None:
        rec["element_bbox"] = list(bbox)
    checks.append(rec)
    return rec


# --- The checks (V2-V11); V12 is the verdict writer ----------------------------


def run_checks(asset):
    """Run V2-V11 over every surface + asset-wide. Return ``(checks, needs_review)``.

    Deterministic generation order: per surface (manifest order) V2 then per
    element V3/V4/V5-floor/V5-crosscheck/V6, then surface-level V8/V10; then
    asset-wide V7, V9, V11.
    """
    manifest = asset["manifest"]
    images = asset["images"]
    checks = []

    for surf in manifest["surfaces"]:
        sid = surf["id"]
        srole = surf["role"]
        png = images[surf["png"]]
        cw, ch = surf["canvas"]["w"], surf["canvas"]["h"]

        _check_v2_canvas(checks, surf, png, sid, srole, cw, ch)

        for el in surf["elements"]:
            _check_element(checks, surf, el, png, sid, srole)

        _check_v8_source(checks, surf, sid, srole)
        _check_v10_axis(checks, surf, sid, srole)

    _check_v7_hook(checks, manifest)
    _check_v9_blacklist(checks, asset)
    _check_v11_provenance(checks, asset)

    needs_review = _provenance_prompts()
    return checks, needs_review


def _check_v2_canvas(checks, surf, png, sid, srole, cw, ch):
    real_w, real_h = png.size
    required = _FORMAT_BY_ROLE.get(srole)
    rule = "qa-checklist.md §Layout"
    if (real_w, real_h) != (cw, ch):
        _rec(checks, "V2-canvas", sid, "FAIL",
             "PNG {}x{} != manifest canvas {}x{}".format(real_w, real_h, cw, ch), rule)
        return
    if required is not None and (cw, ch) != required:
        _rec(checks, "V2-canvas", sid, "FAIL",
             "canvas {}x{} != required {}x{} for role {}".format(
                 cw, ch, required[0], required[1], srole), rule)
        return
    _rec(checks, "V2-canvas", sid, "PASS",
         "{}x{} matches format".format(real_w, real_h), rule)


def _check_element(checks, surf, el, png, sid, srole):
    erole = el["role"]
    bbox = el["bbox"]
    font_px = el["font_px"]
    weight = el["weight"]
    color = el["color"]
    bg = el["bg"]
    color_rgb = _hex_rgb(color)

    # --- V3 ink-present ---
    ink_count, row_has_ink = _crop_rows_ink(png, bbox, color_rgb)
    if ink_count < INK_MIN_PX:
        _rec(checks, "V3-ink", sid, "FAIL",
             "{} ink px < {} (blank/near-blank PNG under declared text)".format(
                 ink_count, INK_MIN_PX),
             "spec §5.2 V3", bbox)
    else:
        _rec(checks, "V3-ink", sid, "PASS",
             "{} ink px >= {}".format(ink_count, INK_MIN_PX), "spec §5.2 V3", bbox)

    # --- V4 contrast (declared hex) ---
    cc = measure.contrast_check(color, bg, font_px, weight)
    kind = "large" if cc["large"] else "normal"
    if cc["passes"]:
        _rec(checks, "V4-contrast", sid, "PASS",
             "ratio {}:1 >= {}:1 ({})".format(cc["ratio"], cc["threshold"], kind),
             "brand-kit.md §3", bbox)
    else:
        _rec(checks, "V4-contrast", sid, "FAIL",
             "ratio {}:1 < {}:1 ({})".format(cc["ratio"], cc["threshold"], kind),
             "brand-kit.md §3", bbox)

    # --- V5 floor ---
    tm = measure.type_min_ok(srole, erole, font_px)
    if tm["minimum"] is None:
        _rec(checks, "V5-floor", sid, "skipped",
             "role '{}' exempt from size floor".format(erole),
             "qa-checklist.md §Typography", bbox)
    elif tm["passes"]:
        _rec(checks, "V5-floor", sid, "PASS",
             "font_px {} >= {}".format(font_px, tm["minimum"]),
             "qa-checklist.md §Typography", bbox)
    else:
        _rec(checks, "V5-floor", sid, "FAIL",
             "font_px {} < min {} for {}/{}".format(font_px, tm["minimum"], srole, erole),
             "qa-checklist.md §Typography", bbox)

    # --- V5 cross-check (measured from PNG pixels; anti-lie) ---
    band = _median_band_height(row_has_ink) if ink_count >= INK_MIN_PX else None
    if band is None:
        _rec(checks, "V5-crosscheck", sid, "skipped",
             "no measurable ink band", "spec §5.2 V5", bbox)
    else:
        effective_px = band / K_INTER
        if measure.size_consistent(font_px, effective_px, measure.SIZE_TOLERANCE):
            _rec(checks, "V5-crosscheck", sid, "PASS",
                 "declared {}px vs measured ~{:.1f}px (band {}px) within +/-25%".format(
                     font_px, effective_px, band),
                 "spec §5.2 V5", bbox)
        else:
            _rec(checks, "V5-crosscheck", sid, "FAIL",
                 "declared {}px vs measured ~{:.1f}px (band {}px) outside +/-25%".format(
                     font_px, effective_px, band),
                 "spec §5.2 V5", bbox)

    # --- V6 safe zone ---
    if erole not in _SAFEZONE_ROLES:
        _rec(checks, "V6-safezone", sid, "skipped",
             "role '{}' exempt from safe zone".format(erole),
             "qa-checklist.md §Layout", bbox)
    else:
        cw, ch = surf["canvas"]["w"], surf["canvas"]["h"]
        try:
            sz = measure.safe_zone_ok(cw, ch, bbox)
        except ValueError as exc:
            _rec(checks, "V6-safezone", sid, "FAIL", str(exc),
                 "qa-checklist.md §Layout", bbox)
            return
        if sz["passes"]:
            _rec(checks, "V6-safezone", sid, "PASS", sz["reason"],
                 "qa-checklist.md §Layout", bbox)
        else:
            _rec(checks, "V6-safezone", sid, "FAIL", sz["reason"],
                 "qa-checklist.md §Layout", bbox)


def _check_v7_hook(checks, manifest):
    rule = "qa-checklist.md §Carousel"
    hook_el = None
    hook_sid = None
    for surf in manifest["surfaces"]:
        for el in surf["elements"]:
            if el["role"] == "hook":
                hook_el = el
                hook_sid = surf["id"]
                break
        if hook_el is not None:
            break
    if hook_el is None:
        _rec(checks, "V7-hook-words", "asset", "skipped",
             "no hook element (no carousel slide-1) — N/A", rule)
        return
    words = len(hook_el["text"].split())
    if words > 10:
        _rec(checks, "V7-hook-words", hook_sid, "FAIL",
             "hook is {} words > 10".format(words), rule)
    else:
        _rec(checks, "V7-hook-words", hook_sid, "PASS",
             "hook is {} words <= 10".format(words), rule)


def _check_v8_source(checks, surf, sid, srole):
    rule = "qa-checklist.md §Chart integrity"
    stamps = [el for el in surf["elements"] if el["role"] == "source-stamp"]
    is_chart = srole == "chart-card"
    # A carousel "source slide" is one that carries a source-stamp.
    applies = is_chart or (srole == "carousel-slide" and bool(stamps))
    if not applies:
        _rec(checks, "V8-source-stamp", sid, "skipped",
             "not a chart-card or carousel source slide", rule)
        return
    if not stamps:
        _rec(checks, "V8-source-stamp", sid, "FAIL",
             "no source-stamp element on {}".format(srole), rule)
        return
    for st in stamps:
        if _has_source_and_date(st["text"]):
            _rec(checks, "V8-source-stamp", sid, "PASS",
                 "source-stamp carries source + date", rule, st["bbox"])
            return
    _rec(checks, "V8-source-stamp", sid, "FAIL",
         "source-stamp missing source attribution and/or as-of date", rule,
         stamps[0]["bbox"])


def _check_v10_axis(checks, surf, sid, srole):
    rule = "qa-checklist.md §Chart integrity"
    if srole != "chart-card" or not surf.get("has_axis", False):
        _rec(checks, "V10-chart-integrity", sid, "skipped",
             "no plotted axis (has_axis=false) — N/A", rule)
        return
    axis_min = surf.get("axis_min")
    break_disclosed = surf.get("break_disclosed", False)
    if axis_min != 0 and not break_disclosed:
        _rec(checks, "V10-chart-integrity", sid, "FAIL",
             "axis_min={} != 0 and break not disclosed".format(axis_min), rule)
    else:
        _rec(checks, "V10-chart-integrity", sid, "PASS",
             "axis_min={} (zero-based or break disclosed)".format(axis_min), rule)


def _check_v9_blacklist(checks, asset):
    rule = "brand-kit.md §8"
    phrases = measure.parse_blacklist(str(_BRAND_KIT))
    manifest_text = "\n".join(
        el["text"] for surf in asset["manifest"]["surfaces"] for el in surf["elements"]
    )
    corpus = asset["copy_text"] + "\n" + manifest_text
    hits = measure.scan_blacklist(corpus, phrases)
    if hits:
        _rec(checks, "V9-blacklist", "asset", "FAIL",
             "blacklisted stat present: {}".format("; ".join(repr(h) for h in hits)),
             rule)
    else:
        _rec(checks, "V9-blacklist", "asset", "PASS",
             "no blacklisted stats ({} phrases scanned)".format(len(phrases)), rule)


def _parse_provenance_block(meta_text):
    """Return dict of lowercase key -> value from the provenance block, or None."""
    if _PROV_START not in meta_text or _PROV_END not in meta_text:
        return None
    inner = meta_text.split(_PROV_START, 1)[1].split(_PROV_END, 1)[0]
    kv = {}
    for line in inner.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            kv[key.strip().lower()] = val.strip()
    return kv


def _check_v11_provenance(checks, asset):
    rule = "qa-checklist.md §Data provenance"
    kv = _parse_provenance_block(asset["meta_text"])
    if kv is None:
        _rec(checks, "V11-provenance", "asset", "FAIL",
             "no provenance attestation block in meta.md", rule)
        return
    for key in _PROV_REQUIRED_KEYS:
        if key not in kv or not kv[key]:
            _rec(checks, "V11-provenance", "asset", "FAIL",
                 "provenance block missing/empty required key '{}'".format(key), rule)
            return
    as_of = kv["as_of"]
    if not (_ISO_DATE_RE.search(as_of) or _MONTH_DAY_RE.search(as_of)):
        _rec(checks, "V11-provenance", "asset", "FAIL",
             "provenance 'as_of' has no date token: {!r}".format(as_of), rule)
        return
    _rec(checks, "V11-provenance", "asset", "PASS",
         "attestation block present with sources/terrem_db_numbers/as_of", rule)


def _provenance_prompts():
    """Emit the qa-checklist.md §Data provenance bullet prompts as needs_review."""
    if not _QA_CHECKLIST.is_file():
        return []
    text = _read_text(_QA_CHECKLIST)
    lines = text.splitlines()
    prompts = []
    in_section = False
    for line in lines:
        if re.match(r"^##\s+Data provenance", line):
            in_section = True
            continue
        if in_section and re.match(r"^##\s+", line):
            break
        if in_section:
            m = re.match(r"^\s*-\s*\[.\]\s*(.+)$", line)
            if m:
                prompts.append(m.group(1).strip())
    return [{"prompt": p, "rule": "qa-checklist.md §Data provenance"} for p in prompts]


# --- Verdict output (V12) ------------------------------------------------------


def build_verdict(asset, checks, needs_review, checked_on, checked_by):
    failed = [
        {"id": c["id"], "surface": c["surface"], "detail": c["detail"], "rule": c["rule"]}
        for c in checks
        if c["status"] == "FAIL"
    ]
    verdict = "FAIL" if failed else "PASS"
    # Ordered construction (contract s5.4 key order); do NOT sort_keys top level.
    doc = {
        "schema_version": "1",
        "slug": asset["slug"],
        "verdict": verdict,
        "checked_on": checked_on,
        "checked_by": checked_by,
        "checks": checks,
        "failed_checks": failed,
        "needs_review": needs_review,
    }
    return doc


def write_verdict_json(asset, doc):
    out = asset["folder"] / "render" / "qa-verdict.json"
    out.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out


def _verdict_block(doc, checked_by, checked_on):
    if doc["failed_checks"]:
        failed_line = ", ".join(
            "{} {}".format(f["id"], f["surface"]) for f in doc["failed_checks"]
        )
    else:
        failed_line = "none"
    return "\n".join([
        _VERDICT_START,
        "QA: {}".format(doc["verdict"]),
        "Failed checks: {}".format(failed_line),
        "Checked by: {} on {}".format(checked_by, checked_on),
        _VERDICT_END,
    ])


def write_meta_verdict(asset, doc, checked_by, checked_on):
    """Insert/replace the delimited verdict block in meta.md (idempotent)."""
    meta_path = asset["folder"] / "meta.md"
    block = _verdict_block(doc, checked_by, checked_on)
    if meta_path.is_file():
        text = _read_text(meta_path)
    else:
        text = ""
    if _VERDICT_START in text and _VERDICT_END in text:
        pattern = re.compile(
            re.escape(_VERDICT_START) + r".*?" + re.escape(_VERDICT_END), re.DOTALL
        )
        new_text = pattern.sub(lambda _m: block, text, count=1)
    else:
        sep = "" if text.endswith("\n\n") or text == "" else (
            "\n" if text.endswith("\n") else "\n\n")
        new_text = text + sep + block + "\n"
    meta_path.write_text(new_text, encoding="utf-8")
    return meta_path


# --- CLI orchestration ---------------------------------------------------------


def _print_verdict(doc):
    for f in doc["failed_checks"]:
        print("FAIL {} {} — {} ({})".format(f["id"], f["surface"], f["detail"], f["rule"]))
    n = len(doc["checks"])
    fcount = len(doc["failed_checks"])
    scount = sum(1 for c in doc["checks"] if c["status"] == "skipped")
    print("VERDICT: {} ({} checks, {} failed, {} skipped)".format(
        doc["verdict"], n, fcount, scount))


def run(asset_folder, checked_on, checked_by):
    """Full pipeline. Returns exit code. Raises PreconditionError for exit 2."""
    asset = load_asset(asset_folder)
    checks, needs_review = run_checks(asset)
    doc = build_verdict(asset, checks, needs_review, checked_on, checked_by)
    write_verdict_json(asset, doc)
    write_meta_verdict(asset, doc, checked_by, checked_on)
    _print_verdict(doc)
    return 0 if doc["verdict"] == "PASS" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate a rendered content asset against the brand QA gate "
                    "(checks V2-V12); emit qa-verdict.json + meta.md verdict block."
    )
    parser.add_argument("asset_folder", help="path to content/<slug>/")
    parser.add_argument("--checked-on", default=datetime.date.today().isoformat(),
                        help="verdict date YYYY-MM-DD (default: today)")
    parser.add_argument("--checked-by", default="validator-cli",
                        help="verdict author (default: validator-cli)")
    args = parser.parse_args(argv)
    try:
        return run(args.asset_folder, args.checked_on, args.checked_by)
    except PreconditionError as exc:
        sys.stderr.write("ERROR: {}\n".format(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
