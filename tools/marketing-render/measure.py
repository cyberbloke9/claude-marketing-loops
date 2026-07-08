"""Measurement core for the TERREM marketing-loop Asset Renderer + QA Gate.

Pure, deterministic measurement library (Sprint 001). Renders nothing, opens no
PNG, reads no manifest. The only I/O is reading ``brand/brand-kit.md`` to parse
the blacklist (V9, single-source rule). Every function is a pure computation over
numbers, hex strings, and bounding boxes, raises ``ValueError`` naming the
offending value on malformed input, and never touches the network.

Spec refs: §5.2 (V4, V5, V6, V9), §5.3 (token rule), §9 (locked tokens).
"""

import re

# --- §3 Locked constants (source of truth: brand-kit.md §3 / spec §9) ----------

# Token name -> canonical lowercase hex. Exactly these nine, no others.
TOKENS = {
    "bg": "#faf8f3",
    "surface": "#ffffff",
    "ink": "#1c1917",
    "ink-muted": "#57534e",
    "accent": "#0f766e",
    "accent-deep": "#0d3d38",
    "chart-up": "#0d9488",
    "chart-down": "#dc2626",
    "border": "#e0dbd3",
}

# The set of the nine token hexes (lowercase).
TOKEN_HEXES = frozenset(TOKENS.values())

# Glyph-size cross-check tolerance (Risk 4): ±25%.
SIZE_TOLERANCE = 0.25

# --- §4.1 Color / contrast (V4) ------------------------------------------------

_HEX6_RE = re.compile(r"^[0-9a-f]{6}$")


def normalize_hex(value):
    """Accept ``#RRGGBB`` or ``RRGGBB`` (any case) -> canonical lowercase ``#rrggbb``.

    Raises ``ValueError`` for anything else. 3-digit shorthand is rejected;
    full 6-digit only (all brand tokens are 6-digit).
    """
    if not isinstance(value, str):
        raise ValueError("invalid hex color: {!r}".format(value))
    body = value[1:] if value.startswith("#") else value
    body = body.lower()
    if not _HEX6_RE.match(body):
        raise ValueError("invalid hex color: {}".format(value))
    return "#" + body


def _channels(hex_color):
    """Return (r, g, b) integers 0..255 from a validated hex color."""
    h = normalize_hex(hex_color)[1:]
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lin(c):
    """Linearize an 8-bit channel value per WCAG 2.x."""
    cs = c / 255.0
    if cs <= 0.03928:
        return cs / 12.92
    return ((cs + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color):
    """WCAG 2.x relative luminance in [0, 1]."""
    r, g, b = _channels(hex_color)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(hex_a, hex_b):
    """WCAG contrast ratio ``(Llighter + 0.05) / (Ldarker + 0.05)``.

    Symmetric; result in [1.0, 21.0].
    """
    la = relative_luminance(hex_a)
    lb = relative_luminance(hex_b)
    lighter, darker = (la, lb) if la >= lb else (lb, la)
    return (lighter + 0.05) / (darker + 0.05)


def is_large_text(font_px, weight):
    """True if ``font_px >= 24`` OR (``font_px >= 18.5`` AND ``weight >= 700``)."""
    return font_px >= 24 or (font_px >= 18.5 and weight >= 700)


def contrast_check(fg_hex, bg_hex, font_px, weight):
    """Return contrast verdict dict.

    ``{"ratio": float, "threshold": 4.5 | 3.0, "large": bool, "passes": bool}``.
    ``passes`` is computed on the raw full-precision ratio (``raw >= threshold``),
    so ``4.497`` cannot round up and falsely pass. ``ratio`` is rounded to 2
    decimals for display only.
    """
    raw_ratio = contrast_ratio(fg_hex, bg_hex)
    large = is_large_text(font_px, weight)
    threshold = 3.0 if large else 4.5
    return {
        "ratio": round(raw_ratio, 2),
        "threshold": threshold,
        "large": large,
        "passes": raw_ratio >= threshold,
    }


# --- §4.2 Token validation (§5.3 token rule) -----------------------------------


def is_brand_token(hex_color):
    """True iff ``normalize_hex(hex_color)`` is one of the nine brand tokens."""
    return normalize_hex(hex_color) in TOKEN_HEXES


def token_name(hex_color):
    """Return the token name for a token hex, else ``None``."""
    target = normalize_hex(hex_color)
    for name, hex_val in TOKENS.items():
        if hex_val == target:
            return name
    return None


# --- §4.3 Type-size minimums (V5, first half) ----------------------------------

_SURFACE_ROLES = frozenset({"carousel-slide", "chart-card"})
_ELEMENT_ROLES = frozenset(
    {"headline", "hook", "body", "source-stamp", "wordmark", "chart-label"}
)

# element_role -> {surface_role -> minimum px or None (exempt)}
_TYPE_MINIMUMS = {
    "headline": {"carousel-slide": 48, "chart-card": 36},
    "hook": {"carousel-slide": 48, "chart-card": 36},
    "body": {"carousel-slide": 24, "chart-card": 24},
    "source-stamp": {"carousel-slide": None, "chart-card": None},
    "wordmark": {"carousel-slide": None, "chart-card": None},
    "chart-label": {"carousel-slide": None, "chart-card": None},
}


def type_min_ok(surface_role, element_role, font_px):
    """Return ``{"minimum": <int or None>, "passes": <bool>}`` for V5 size floor.

    Exempt roles (minimum ``None``) always pass. Unknown roles -> ``ValueError``.
    """
    if surface_role not in _SURFACE_ROLES:
        raise ValueError("unknown surface_role: {}".format(surface_role))
    if element_role not in _ELEMENT_ROLES:
        raise ValueError("unknown element_role: {}".format(element_role))
    minimum = _TYPE_MINIMUMS[element_role][surface_role]
    if minimum is None:
        return {"minimum": None, "passes": True}
    return {"minimum": minimum, "passes": font_px >= minimum}


# --- §4.4 Glyph-size consistency cross-check (V5, second half; Risk 4) ----------


def size_consistent(declared_font_px, measured_px, tol=SIZE_TOLERANCE):
    """True iff ``declared*(1-tol) <= measured <= declared*(1+tol)``.

    Generic band primitive. Defines only the tolerance band math (±25% per Risk 4),
    not what ``measured_px`` means (deferred to Sprint 004).
    """
    lo = declared_font_px * (1 - tol)
    hi = declared_font_px * (1 + tol)
    return lo <= measured_px <= hi


# --- §4.5 Safe-zone containment (V6) -------------------------------------------

SAFE_ZONES = {
    (1080, 1350): {"x_min": 40, "y_min": 40, "x_max": 1040, "y_max": 1310},
    (1080, 1920): {"x_min": 0, "y_min": 250, "x_max": 1080, "y_max": 1480},
}


def safe_zone_ok(canvas_w, canvas_h, bbox):
    """Geometry check for V6.

    ``bbox = [x, y, w, h]``; element occupies ``x..x+w`` by ``y..y+h``.
    Returns ``{"passes": bool, "reason": str}``. Unknown canvas -> ``ValueError``.
    Non-4-length or negative w/h -> ``ValueError``.
    """
    zone = SAFE_ZONES.get((canvas_w, canvas_h))
    if zone is None:
        raise ValueError("no safe zone for canvas {}x{}".format(canvas_w, canvas_h))
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise ValueError("bbox must be length-4 [x, y, w, h]: {!r}".format(bbox))
    x, y, w, h = bbox
    if w < 0 or h < 0:
        raise ValueError("bbox has negative width/height: {!r}".format(bbox))
    right = x + w
    bottom = y + h
    if x < zone["x_min"]:
        return {"passes": False, "reason": "left edge {} < x_min {}".format(x, zone["x_min"])}
    if y < zone["y_min"]:
        return {"passes": False, "reason": "top edge {} < y_min {}".format(y, zone["y_min"])}
    if right > zone["x_max"]:
        return {"passes": False, "reason": "right edge {} > x_max {}".format(right, zone["x_max"])}
    if bottom > zone["y_max"]:
        return {"passes": False, "reason": "bottom edge {} > y_max {}".format(bottom, zone["y_max"])}
    return {"passes": True, "reason": "within safe zone"}


# --- §4.6 Blacklist parser + scan (V9, single-source) --------------------------

_QUOTED_RE = re.compile(r'"([^"]+)"')


def parse_blacklist(brand_kit_path):
    """Parse double-quoted phrases from the ``## 8. Blacklist`` section.

    Returns phrases verbatim (original casing, en-dashes, etc.). Raises
    ``ValueError`` if the ``## 8`` section is not found. Does not hardcode phrases.
    """
    with open(brand_kit_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s+8\b", line):
            start = i
            break
    if start is None:
        raise ValueError(
            "blacklist section '## 8' not found in {}".format(brand_kit_path)
        )
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^##\s+\d", lines[j]):
            end = j
            break
    section = "\n".join(lines[start:end])
    return _QUOTED_RE.findall(section)


def normalize_for_scan(text):
    """Lowercase, replace unicode dashes with '-', collapse whitespace runs."""
    text = text.lower()
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text


def scan_blacklist(text, phrases):
    """Return the sublist of ``phrases`` whose normalized form is a substring of
    the normalized ``text``. Case/dash/whitespace-insensitive. Empty list = clean.
    """
    haystack = normalize_for_scan(text)
    return [p for p in phrases if normalize_for_scan(p) in haystack]


# =============================================================================
# Renderer V2 — Format Library measurement core (Sprint 001, run 003)
# =============================================================================
# All symbols below are ADDITIVE. Nothing above this line is mutated. These are
# pure computations over element dicts (``{"role": str, "font_px": int, ...}``)
# and strings, consumed by the Sprint-005 validator. Spec refs: §5.2 (V13/V14/
# V15/V17/V19), §5.3, §5.4; contract §1.1; Risks 3/4/5/6.

# The V13-exempt utility roles: a slide whose elements are a subset of these
# carries no content and needs no dominant element (spec §5.2 V13, Risk 6).
_UTILITY_ROLES = frozenset({"so-what", "source-stamp", "wordmark"})
# Content roles: any element with one of these makes a slide a content slide
# (NOT a utility slide) and forces the exactly-one-dominant rule.
_CONTENT_ROLES = frozenset(
    {"headline", "hook", "body", "chart-label", "dominant"}
)

# Fallback body_reference when a surface declares no body element (Risk 3): the
# raised v2 body floor. Kept in sync with _V2_TYPE_MINIMUMS["body"].
_BODY_REFERENCE_FALLBACK = 26
# V13 dominant-ratio threshold: dominant.font_px must be >= 3x body_reference.
_DOMINANT_RATIO = 3.0


# --- §5.2 V13 core: dominant-element ratio -------------------------------------


def body_reference(elements):
    """Return the V13 ``body_reference`` for a surface's element list.

    ``= max(font_px)`` over elements whose ``role == "body"``; falls back to the
    raised body floor **26** when the surface has no body element (spec §5.2 V13,
    Risk 3). Purely reads ``role``/``font_px``; mutates nothing.
    """
    body_sizes = [
        el["font_px"] for el in elements if el.get("role") == "body"
    ]
    if not body_sizes:
        return _BODY_REFERENCE_FALLBACK
    return max(body_sizes)


def count_dominant(elements):
    """Number of elements whose ``role == "dominant"``."""
    return sum(1 for el in elements if el.get("role") == "dominant")


def is_utility_slide(elements):
    """True iff every element's role is a utility role AND the list is non-empty.

    Utility roles are ``{so-what, source-stamp, wordmark}``. Any content role
    (``headline``/``hook``/``body``/``chart-label``/``dominant``) makes the slide
    a content slide (returns False). An empty element list returns False (an
    empty slide is not a utility slide). Spec §5.2 V13, Risk 6.
    """
    if not elements:
        return False
    return all(el.get("role") in _UTILITY_ROLES for el in elements)


def dominant_ratio_ok(elements):
    """V13 verdict for one surface's element list.

    Returns a dict::

        {"exempt": bool, "dominant_count": int, "body_reference": int,
         "dominant_font_px": int|None, "ratio": float|None,
         "passes": bool, "reason": str}

    Utility slides are exempt (pass). A content slide must declare exactly one
    ``dominant`` element with ``dominant.font_px / body_reference >= 3.0`` on the
    raw float (no rounding-up). Spec §5.2 V13, Risk 3/6.
    """
    ref = body_reference(elements)
    if is_utility_slide(elements):
        return {
            "exempt": True,
            "dominant_count": 0,
            "body_reference": ref,
            "dominant_font_px": None,
            "ratio": None,
            "passes": True,
            "reason": "utility slide (subset of {so-what, source-stamp, "
                      "wordmark}); V13 exempt",
        }
    doms = [el for el in elements if el.get("role") == "dominant"]
    n = len(doms)
    if n == 0:
        return {
            "exempt": False,
            "dominant_count": 0,
            "body_reference": ref,
            "dominant_font_px": None,
            "ratio": None,
            "passes": False,
            "reason": "no dominant element on content slide",
        }
    if n >= 2:
        return {
            "exempt": False,
            "dominant_count": n,
            "body_reference": ref,
            "dominant_font_px": None,
            "ratio": None,
            "passes": False,
            "reason": "{} dominant elements; exactly one required".format(n),
        }
    dfp = doms[0]["font_px"]
    ratio = dfp / ref
    passes = ratio >= _DOMINANT_RATIO
    if passes:
        reason = "dominant {}px / body_reference {}px = {:.3f} >= 3".format(
            dfp, ref, ratio)
    else:
        reason = ("dominant {}px / body_reference {}px = {:.3f} < 3x rule "
                  "(spec §5.2 V13)").format(dfp, ref, ratio)
    return {
        "exempt": False,
        "dominant_count": 1,
        "body_reference": ref,
        "dominant_font_px": dfp,
        "ratio": ratio,
        "passes": passes,
        "reason": reason,
    }


# --- §5.2 V14 core: raised type floors for format-slide surfaces ---------------
#
# NEW table, keyed on element role only (surface role is always "format-slide"
# by construction; surface-role routing happens in the Sprint-005 validator).
# _TYPE_MINIMUMS (above) is left byte-for-byte unchanged. Contract decisions:
#   * so-what -> 26  (a body-class utility line; V14 prose is silent on it)
#   * dominant -> 48 (a headline-class figure; deliberately redundant because
#                     V13 already forces dominant >= 3*26 = 78, so this floor can
#                     never be the binding constraint — it exists for table
#                     completeness and a graceful floor if V13 is bypassed).
_V2_TYPE_MINIMUMS = {
    "headline": 48,
    "hook": 48,
    "dominant": 48,
    "body": 26,
    "chart-label": 26,
    "so-what": 26,
    "source-stamp": 24,
    "wordmark": None,  # exempt
}


def format_slide_type_min(element_role, font_px):
    """V14 size-floor verdict for one element on a format-slide surface.

    Returns ``{"minimum": int|None, "passes": bool}``. An exempt role
    (``wordmark``, minimum ``None``) always passes. Unknown role -> ``ValueError``
    naming the role. Keyed on element role only. Spec §5.2 V14.
    """
    if element_role not in _V2_TYPE_MINIMUMS:
        raise ValueError("unknown format-slide element_role: {}".format(element_role))
    minimum = _V2_TYPE_MINIMUMS[element_role]
    if minimum is None:
        return {"minimum": None, "passes": True}
    return {"minimum": minimum, "passes": font_px >= minimum}


# --- §5.2 V15 core: thumbnail effective-px comparator (measured-px route) -------
#
# Per Risk 4, V15 is a MEASURED-pixel check: Sprint 005 downscales the real PNG
# to 360px and measures rendered ink-band height. This sprint ships ONLY the
# comparator + scale factor + pinned thresholds — no font_px->pass predictor
# (that Risk-4-forbidden arithmetic route is an explicit non-goal).
#
# Threshold provenance (comment only — measure.py takes no dependency on
# validate.py's K_INTER): ink-band ~= 0.83 * font_px at 1080; at 360px that is
# 0.83 * font_px / 3. Headline floor 48 -> 0.83*48/3 ~= 13.3 -> 13. Dominant
# floor 78 (=3*26) -> 0.83*78/3 ~= 21.6 -> 21. PROVISIONAL pending Sprint-006
# real-render revalidation (contract §1.1.C); binding invariant: the v2 positive
# control clears 13/21 at 360px AND the illegible fixture fails them.
THUMB_W = 360
CANVAS_W = 1080
THUMB_HEADLINE_MIN_PX = 13
THUMB_DOMINANT_MIN_PX = 21

_THUMB_MIN_BY_ROLE = {
    "headline": THUMB_HEADLINE_MIN_PX,
    "hook": THUMB_HEADLINE_MIN_PX,
    "dominant": THUMB_DOMINANT_MIN_PX,
}


def thumbnail_scale_band(full_band_px, canvas_w=CANVAS_W, thumb_w=THUMB_W):
    """Downscale a full-canvas ink-band height to its 360px-preview effective px.

    ``= full_band_px * thumb_w / canvas_w`` (= ``full_band_px / 3`` at the pinned
    360/1080). Pure arithmetic; the *source* of ``full_band_px`` is a real-PNG
    ink measurement wired in Sprint 005, never here. Spec §5.2 V15, Risk 4.
    """
    return full_band_px * thumb_w / canvas_w


def thumbnail_ink_ok(role, effective_px):
    """V15 comparator: does a measured 360px effective ink height clear its floor?

    Returns ``{"role": role, "minimum": int, "effective_px": float,
    "passes": bool}``. ``headline``/``hook`` -> 13; ``dominant`` -> 21. Any other
    role -> ``ValueError`` (V15 gates only headline/hook + dominant). ``passes``
    is computed on the raw float. Spec §5.2 V15, Risk 4.
    """
    if role not in _THUMB_MIN_BY_ROLE:
        raise ValueError(
            "thumbnail_ink_ok gates only headline/hook/dominant; got: {}".format(role)
        )
    minimum = _THUMB_MIN_BY_ROLE[role]
    return {
        "role": role,
        "minimum": minimum,
        "effective_px": effective_px,
        "passes": effective_px >= minimum,
    }


# --- §5.4 V17 + V19 core: meta.md cover-pattern / one-dataset block parser ------
#
# Modeled on validate.py's _parse_provenance_block + the provenance grammar.

_COVER_START = "<!-- cover-pattern:start -->"
_COVER_END = "<!-- cover-pattern:end -->"

# V17 valid cover patterns.
VALID_COVER_PATTERNS = frozenset({"BIG-NUMBER", "CHART-FIRST"})


def parse_cover_pattern_block(meta_text):
    """Parse the ``<!-- cover-pattern:start -->`` … ``end`` block from meta text.

    Returns a dict of lowercased key -> verbatim value (trailing ``# …`` inline
    comment stripped, matching §5.4's example), or ``None`` when the block is
    absent. Reads a string; opens no file. Spec §5.4, contract §1.1.D.
    """
    if _COVER_START not in meta_text or _COVER_END not in meta_text:
        return None
    inner = meta_text.split(_COVER_START, 1)[1].split(_COVER_END, 1)[0]
    kv = {}
    for line in inner.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.split("#", 1)[0].strip()
            kv[key.strip().lower()] = val
    return kv


def cover_pattern_valid(parsed):
    """V17 predicate: parsed block present with a valid ``pattern`` value.

    True iff ``parsed`` is not ``None`` and ``parsed["pattern"]`` is a non-empty
    string in ``VALID_COVER_PATTERNS``. Spec §5.2 V17.
    """
    if not parsed:
        return False
    pattern = parsed.get("pattern")
    return bool(pattern) and pattern in VALID_COVER_PATTERNS


def one_dataset_present(parsed):
    """V19 presence predicate: a non-empty ``one_dataset`` attestation exists.

    True iff ``parsed`` is not ``None`` and ``parsed["one_dataset"]`` is a
    non-empty string. Presence only — never semantic (Risk 5). Spec §5.2 V19.
    """
    if not parsed:
        return False
    value = parsed.get("one_dataset")
    return bool(value) and isinstance(value, str)
