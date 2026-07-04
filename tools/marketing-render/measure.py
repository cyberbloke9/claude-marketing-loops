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
