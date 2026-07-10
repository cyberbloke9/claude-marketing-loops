#!/usr/bin/env python3
"""Direct-publishing CLI for the TERREM marketing-loop system — dry-run-first.

Sprint 002 (spec s11 Sprint 002; contract sprint_002/contract.md). This delivers
the SKELETON of ``publish_api.py``: the injectable HTTP transport (a single
``urllib.request.urlopen`` call site), the full CLI argument surface, the ``.env``
loader, the ``--live`` precondition gate, queue row selection + scope filtering,
the deterministic plan model + ``publish-plan.json`` writer, and the reusable
placeholder / redaction / image_url helpers.

NO channel adapters are built this sprint (Instagram=003, LinkedIn=004,
Facebook=005, live posting / queue transition / day-cap=006). The adapter
registry ships EMPTY, so every selected row renders in the plan with an empty
``steps`` list and an honest ``note`` naming the sprint that fills it.

Determinism: this module NEVER reads the wall clock. The only dates it handles
come from ``--week`` / ``--date`` args, which are parsed (``datetime.strptime``
on the supplied value only) but never compared against "now". Same inputs =>
byte-identical ``publish-plan.json``.

Security: secrets come ONLY from an untracked ``.env``; they are loaded into
memory and NEVER printed to stdout/stderr nor written to any tracked file. Every
place a secret would appear in the plan shows ``<REDACTED>`` (contract s7.4).

No-network proof: every network call routes through the single ``Transport``
class (the ONLY ``urlopen`` call site — AST-provable). Dry-run invokes the
transport ZERO times; tests inject a ``RecordingTransport`` / ``RaisingTransport``
so no test and no dry-run ever opens a real socket.

Sprint 006 wires the frozen adapter ``execute`` flows + ``mark_posted.transition``
into the real ``--live`` path: in-scope ``queued`` rows post via the injected
transport and transition ``queued -> posted`` (``posted_date`` <- --date, the
platform-returned ``permalink`` recorded), with the per-day cap (B16), no-regress
guard (B15), and incremental persistence (prior posts survive a later refusal).
Live writes the QUEUE ONLY, never ``publish-plan.json``.

Exit codes (mirror the toolchain convention):
    0  success  — dry-run plan emitted; or every in-scope live row posted +
                  recorded (queue transitioned deterministically).
    1  domain refusal — a targeted already-posted row (no double-post); an adapter
                  refusal (IG container ERROR/EXPIRED, rate-limit, unexpected
                  shape); a per-day-cap breach. Cited on stderr; prior posts stand.
    2  usage / precondition — malformed --week/--date; unknown --channel; invalid
                  --max-per-day / --linkedin-post-type; both --dry-run and --live;
                  invalid/unreadable queue; missing/invalid package; --live failing
                  gate (a)/(b)/(c) or missing --date; >10 IG children; missing local
                  upload bytes. Cited on stderr, no write.

Stdlib only.
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import queue  # noqa: E402
import mark_posted  # noqa: E402  (reuse the frozen queued->posted transition)

_DEFAULT_QUEUE = "content/publish-queue.json"
_PLAN_FILENAME = "publish-plan.json"
_DEFAULT_ENV = ".env"

_WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_PLAN_SCHEMA_VERSION = "1"

# Redaction token shown wherever a secret would otherwise appear (contract s7.4).
_REDACTED = "<REDACTED>"

# The public-asset base-URL placeholder used when no concrete base is supplied
# (contract s7.5 / B11).
_BASE_URL_PLACEHOLDER = "<PUBLIC_ASSET_BASE_URL>"

# Channel -> sprint marker: the SINGLE source for the machine-plan `note` and the
# stdout `note` line so they never drift (contract s5.2). youtube shares the
# generic 003+ marker (no queued asset, but a valid channel).
_CHANNEL_SPRINT = {
    "instagram": "003+",
    "linkedin": "004+",
    "facebook": "005+",
    "youtube": "003+",
}

# Tokens required per channel when going live (contract s4a / B12a).
_CHANNEL_TOKENS = {
    "instagram": ("IG_USER_ID", "IG_ACCESS_TOKEN"),
    "linkedin": ("LI_PERSON_URN", "LI_ACCESS_TOKEN"),
    "facebook": ("FB_PAGE_ID", "FB_PAGE_TOKEN"),
}

# --------------------------------------------------------------------------- #
# Instagram adapter constants (verified — R4-B1/B2/B3, R5-1/R5-3).
# Instagram Login flavor: host graph.instagram.com, NO Facebook Page.
# --------------------------------------------------------------------------- #
_IG_HOST = "https://graph.instagram.com"
_IG_MAX_CHILDREN = 10  # carousel children cap (R4-B2)

# Container polling is COUNT-bounded, never time-bounded (contract s9). No
# wall-clock read anywhere; MAX_POLL_ATTEMPTS caps the loop. Any inter-poll delay
# routes through the injectable ``sleep`` seam (default below); tests pass a no-op.
MAX_POLL_ATTEMPTS = 30
POLL_DELAY_SECONDS = 2


def _default_sleep(seconds):
    """Default inter-poll delay seam (contract s4.3). Tests inject a no-op so no
    test ever blocks; the canonical execution never reaches it (FINISHED first)."""
    time.sleep(seconds)


# --------------------------------------------------------------------------- #
# LinkedIn adapter constants (verified — R4-B4, R5-6). Member-profile posting
# only (person URN, w_member_social). Organic carousels are IMPOSSIBLE via the
# API (R4-B4); the two supported organic paths are MultiImage and multi-page PDF
# Documents. Company-page posting needs the vetted Community Management API
# (R5-5) — a NON-GOAL this sprint.
# --------------------------------------------------------------------------- #
_LI_HOST = "https://api.linkedin.com"
_LI_MAX_IMAGES = 20  # LinkedIn multiImage upper bound (no minimum-of-2 gate)
_LI_PERSON_URN_PLACEHOLDER = "<LI_PERSON_URN>"
_LI_PERMALINK_PREFIX = "https://www.linkedin.com/feed/update/"

# The LinkedIn versioned-API monthly header (B28, R5 risk 6). A FIXED module
# constant, NEVER derived from the wall clock; overridable via --linkedin-version
# (validated ^\d{6}$). Determinism: same inputs => byte-identical plan.
LINKEDIN_VERSION_DEFAULT = "202506"
_LI_VERSION_RE = re.compile(r"^\d{6}$")


# --------------------------------------------------------------------------- #
# Facebook Page adapter constants — ROUND-5-GAP (R4-B5, UNVERIFIED).
# WHO may post is VERIFIED (R5-4: Standard Access suffices for the founder's own
# Page; pages_manage_posts + pages_read_engagement + pages_show_list with a Page
# token). But the publishing FLOW itself — endpoints, params, response shapes,
# permalink construction — DID NOT survive verification (R4-B5) and is a
# best-documented-guess pending live verification. The whole flow is therefore
# labeled ``round-5-gap`` in code + output and gated behind --enable-facebook
# (default OFF). Do NOT treat this adapter's fidelity as authoritative.
# --------------------------------------------------------------------------- #
_FB_HOST = "https://graph.facebook.com"  # bare host, NO version prefix (mirrors _IG_HOST)
_FB_PAGE_ID_PLACEHOLDER = "<FB_PAGE_ID>"
# round-5-gap GUESS: the real Facebook permalink shape is unverified. A FIXED
# module constant (never wall-clock-derived); permalink = prefix + post_id.
_FB_PERMALINK_PREFIX = "https://www.facebook.com/"
# Exact disabled-row note (contract s7.1); single source so JSON + stdout agree.
_FB_DISABLED_NOTE = ("facebook adapter disabled (round-5-gap, unverified); pass "
                     "--enable-facebook to render this row")


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested directly).
# --------------------------------------------------------------------------- #
def placeholder(name, index=None):
    """Render a named deterministic placeholder (contract s7.3 / B10).

    ``placeholder("ig-parent-creation-id") == "<ig-parent-creation-id>"``;
    ``placeholder("ig-child-container-id", 2) == "<ig-child-container-id-2>"``
    (1-indexed). Adapters (003/004) pass their own specific names; this module
    ships only the reusable formatter, no dead adapter-specific constants.
    """
    if index is None:
        return "<{}>".format(name)
    return "<{}-{}>".format(name, index)


def redacted():
    """Return the redaction token ``<REDACTED>`` (contract s7.4 / B17)."""
    return _REDACTED


def redact_bearer(value):
    """Redact the credential in a ``Bearer <token>`` header value.

    ``redact_bearer("Bearer sk-real") == "Bearer <REDACTED>"``. A value that is
    not a Bearer header is returned wholly redacted (defensive).
    """
    if value is not None and value.startswith("Bearer "):
        return "Bearer " + _REDACTED
    return _REDACTED


def redact_token_param(value):
    """Redact the value of a ``key=secret`` query/param string.

    ``redact_token_param("access_token=sk-real") == "access_token=<REDACTED>"``.
    A string without ``=`` is returned wholly redacted (defensive).
    """
    if value is not None and "=" in value:
        key = value.split("=", 1)[0]
        return "{}={}".format(key, _REDACTED)
    return _REDACTED


def image_url(base, slug, filename):
    """Join a public-asset URL as ``<base>/<slug>/<filename>`` (contract s7.5).

    The FIXED join rule (spec B11): a single trailing slash on ``base`` is
    collapsed. When ``base`` is ``None``/absent the literal placeholder
    ``<PUBLIC_ASSET_BASE_URL>`` is used in its place (dry-run does not require a
    concrete base). ``slug`` / ``filename`` are joined verbatim.
    """
    root = base if base else _BASE_URL_PLACEHOLDER
    root = root.rstrip("/")
    return "{}/{}/{}".format(root, slug, filename)


def parse_env(text):
    """Parse ``.env`` text into a dict per the frozen algorithm (contract s4).

    ``KEY=VALUE`` lines; ``#`` starts a comment (inline or full-line); surrounding
    whitespace trimmed; a single matching surrounding quote pair stripped; last
    assignment wins. Returns ``(env_dict, error)`` where ``error`` is ``None`` on
    success or a cited message string (naming the offending LINE NUMBER, never the
    value) when a non-comment line lacks ``=``.
    """
    env = {}
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0]
        line = line.strip()
        if not line:
            continue
        if "=" not in line:
            return None, ".env line {} is not KEY=VALUE".format(lineno)
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        env[key] = value
    return env, None


# --------------------------------------------------------------------------- #
# Transport seam (B38/B39). The ONLY urllib.request.urlopen call site lives in
# Transport.request; adapters (003+) call the injected transport, never urlopen.
# --------------------------------------------------------------------------- #
class Response(object):
    """A small, frozen response shape returned by ``Transport.request`` (s8.2).

    Attributes: ``status`` (int), ``headers`` (dict[str, str], lower-cased keys),
    ``body`` (bytes). ``json()`` parses the body (raising ``ValueError`` on
    non-JSON). Adapters (003+) call ``resp.json()["id"]`` etc.
    """

    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.body = body

    def json(self):
        return json.loads(self.body)


class Transport(object):
    """The single live HTTP seam — the ONLY ``urlopen`` call site in the module.

    ``request(method, url, headers=None, body=None) -> Response``. No adapter
    calls it this sprint (empty registry), but the interface is frozen so 003+
    conform without reshaping.
    """

    def request(self, method, url, headers=None, body=None):
        req = urllib.request.Request(
            url, data=body, headers=headers or {}, method=method)
        with urllib.request.urlopen(req) as resp:  # noqa: S310 (the ONE seam)
            return Response(
                status=getattr(resp, "status", resp.getcode()),
                headers={k.lower(): v for k, v in dict(resp.headers).items()},
                body=resp.read(),
            )


class RecordingTransport(object):
    """A fake transport for tests: records calls, returns canned JSON, no socket.

    Construct with ``RecordingTransport(responses=[{...}, {...}])``; each
    ``request`` pops the next payload and returns a 200 ``Response`` with that
    payload as the JSON body. With no responses configured it returns ``{}``.
    Every ``(method, url, headers, body)`` is appended to ``.calls``.
    """

    def __init__(self, responses=None):
        self._responses = list(responses) if responses else []
        self.calls = []

    def request(self, method, url, headers=None, body=None):
        self.calls.append((method, url, headers, body))
        if self._responses:
            payload = self._responses.pop(0)
            body_bytes = json.dumps(payload).encode("utf-8")
        else:
            body_bytes = b"{}"
        return Response(status=200, headers={}, body=body_bytes)


class RaisingTransport(object):
    """A transport whose every ``request`` raises — proves dry-run never posts."""

    def request(self, method, url, headers=None, body=None):
        raise AssertionError("no network in dry-run/tests")


# --------------------------------------------------------------------------- #
# Adapter contract: typed refusals + a single shared flow definition (contract
# s1.1 / s5). ONE flow generator describes the ordered calls; the dry-run PLAN
# and live EXECUTE both WALK it, so the plan is never a hand-written parallel
# fiction (the parity test proves this). The generator yields ``_Step`` objects
# and receives the (parsed JSON) response for each — real responses in execute,
# deterministic ``plan_response`` stubs in dry-run.
# --------------------------------------------------------------------------- #
class AdapterRefusal(Exception):
    """Domain refusal (exit 1): container ERROR/EXPIRED, poll-exhausted, rate
    limit, or an unexpected response shape. Mapped to exit 1 by run()/Sprint 006."""


class AdapterUsageError(Exception):
    """Usage / precondition error (exit 2): 0 or >10 carousel children (s3.1).
    Enforced at plan-BUILD time (dry-run) AND at execute time — identical in both."""


class _Step(object):
    """One HTTP call in an adapter flow. ``url`` is the BARE url (no query); IG
    carries its fields as query ``params`` (faithful to Meta's documented curl
    form). ``plan_response`` is the deterministic stub the dry-run driver feeds
    back so dependent-value placeholders thread through later steps."""

    def __init__(self, channel, label, method, url, params,
                 headers=None, payload=None, plan_response=None,
                 upload_path=None):
        self.channel = channel
        self.label = label
        self.method = method
        self.url = url
        self.params = params
        self.headers = headers or {}
        self.payload = payload
        self.plan_response = plan_response if plan_response is not None else {}
        # execute-only: the local file whose bytes are the request body for a
        # binary upload (LinkedIn PUT). NEVER serialized into the plan (the plan
        # shows the ``payload`` binary placeholder string instead).
        self.upload_path = upload_path

    def execute_body(self):
        """The request body an EXECUTE call sends (contract s5.3). Binary-upload
        steps (``upload_path`` set) send the file bytes; JSON steps (dict/list
        ``payload``) send compact JSON bytes; everything else sends ``None`` (the
        Instagram default — every IG step has no upload_path and a null payload)."""
        if self.upload_path is not None:
            return Path(self.upload_path).read_bytes()
        if isinstance(self.payload, (dict, list)):
            return json.dumps(self.payload).encode("utf-8")
        return None

    def plan_dict(self):
        """The machine-plan step object — EXACTLY the 7 frozen keys (contract
        s7.3). ``params`` values already carry placeholders/<REDACTED> because the
        plan driver builds the flow with placeholder ids + a <REDACTED> token."""
        return {
            "channel": self.channel,
            "label": self.label,
            "method": self.method,
            "url": self.url,
            "params": dict(self.params),
            "headers": dict(self.headers),
            "payload": self.payload,
        }

    def request_url(self):
        """The concrete url an EXECUTE call hits: bare url + urlencoded params.
        (Dry-run never calls this — it renders ``url`` + ``params`` separately.)"""
        if self.params:
            return self.url + "?" + urllib.parse.urlencode(self.params)
        return self.url


class _IgResult(object):
    """Success result of an Instagram execute: the recorded ``permalink`` (written
    to the queue in Sprint 006) + the published ``media_id``."""

    def __init__(self, permalink, media_id):
        self.permalink = permalink
        self.media_id = media_id


class _LiResult(object):
    """Success result of a LinkedIn execute: the constructed ``permalink``
    (https://www.linkedin.com/feed/update/<urn>, written to the queue in Sprint
    006) + the created ``post_urn``."""

    def __init__(self, permalink, post_urn):
        self.permalink = permalink
        self.post_urn = post_urn


class _FbResult(object):
    """Success result of a Facebook execute (ROUND-5-GAP): the CONSTRUCTED
    ``permalink`` (``_FB_PERMALINK_PREFIX + post_id`` — a guess, R4-B5; written to
    the queue in Sprint 006) + the created feed ``post_id``."""

    def __init__(self, permalink, post_id):
        self.permalink = permalink
        self.post_id = post_id


class _RespView(dict):
    """A parsed-JSON response body (dict) that ALSO carries the response headers
    (lower-cased) so a live LinkedIn post URN can be read from the ``x-restli-id``
    response header first (contract s5.2). It subclasses ``dict``, so every
    Instagram reader (``resp["data"]`` / ``resp["id"]`` / ...) indexes it exactly
    like the plain dict it received before — IG behavior is byte-identical."""

    def __init__(self, *args, **kwargs):
        super(_RespView, self).__init__(*args, **kwargs)
        self.headers = {}


# --- response readers (shared by execute; live-pending shapes, contract s6) --- #
# Isolated so a founder's live response nesting change touches ONE place (R4-B3).
def _read_quota(resp):
    """content_publishing_limit → (quota_usage, quota_total). ASSUMPTION: flattened
    ``{"data":[{"quota_usage":int,"quota_total":int}]}`` (Meta returns limit data
    under data[0]); live-pending (contract s6)."""
    try:
        row0 = resp["data"][0]
        return int(row0["quota_usage"]), int(row0["quota_total"])
    except (KeyError, IndexError, TypeError, ValueError):
        raise AdapterRefusal(
            "unexpected Instagram response for content_publishing_limit")


def _read_id(resp, step_label):
    """POST /media or /media_publish → the returned object ``id``."""
    try:
        return resp["id"]
    except (KeyError, TypeError):
        raise AdapterRefusal(
            "unexpected Instagram response for {}".format(step_label))


def _read_status(resp):
    """GET /<container-id>?fields=status_code → the ``status_code`` string."""
    try:
        return resp["status_code"]
    except (KeyError, TypeError):
        raise AdapterRefusal(
            "unexpected Instagram response for poll container status")


def _read_permalink(resp):
    """GET /<media-id>?fields=permalink → the ``permalink`` url."""
    try:
        return resp["permalink"]
    except (KeyError, TypeError):
        raise AdapterRefusal("unexpected Instagram response for fetch permalink")


def _ig_flow(image_urls, caption, account_id, token, sleep):
    """The SINGLE Instagram container-flow definition (B19–B24). A generator that
    yields ``_Step`` and receives each step's parsed response back via ``.send``.

    Rendered with ``account_id`` / ``token`` / ``image_urls`` supplied by the
    caller: the PLAN driver passes ``<IG_USER_ID>`` / ``<REDACTED>`` / placeholder
    urls (deterministic, secret-free); EXECUTE passes the real env values. Every
    dependent value (child ids, parent creation id, media id) is read from the
    prior response — a placeholder string in the plan, a real id in execute — and
    threaded verbatim into later steps. Returns an ``_IgResult`` on success;
    raises ``AdapterRefusal`` on rate-limit / container-error / poll-exhausted."""
    n = len(image_urls)

    # 1 — rate-limit pre-check (R4-B3; 50-vs-100 is a discrepancy, NOT a gate).
    limit_resp = yield _Step(
        "instagram", "IG · check content_publishing_limit", "GET",
        "{}/{}/content_publishing_limit".format(_IG_HOST, account_id),
        {"access_token": token, "fields": "quota_usage,quota_total"},
        plan_response={"data": [{"quota_usage": 0, "quota_total": 1}]})
    usage, total = _read_quota(limit_resp)
    if usage >= total:
        raise AdapterRefusal(
            "Instagram rate limit exceeded (quota_usage {} >= quota_total {}); "
            "row refused (R4-B3)".format(usage, total))

    if n == 1:
        # Single-image degrade (B21/s4.2): one container, no carousel framing.
        cont_resp = yield _Step(
            "instagram", "IG · create media container", "POST",
            "{}/{}/media".format(_IG_HOST, account_id),
            {"access_token": token, "image_url": image_urls[0]},
            plan_response={"id": placeholder("ig-parent-creation-id")})
        creation_id = _read_id(cont_resp, "create media container")
    else:
        # Carousel: N child containers (B20) + one parent (B21).
        child_ids = []
        for i, url in enumerate(image_urls, start=1):
            child_resp = yield _Step(
                "instagram",
                "IG · create child container {}/{}".format(i, n), "POST",
                "{}/{}/media".format(_IG_HOST, account_id),
                {"access_token": token, "image_url": url,
                 "is_carousel_item": "true"},
                plan_response={"id": placeholder("ig-child-container-id", i)})
            child_ids.append(
                _read_id(child_resp, "create child container {}".format(i)))
        parent_resp = yield _Step(
            "instagram", "IG · create parent carousel container", "POST",
            "{}/{}/media".format(_IG_HOST, account_id),
            {"access_token": token, "caption": caption,
             "children": ",".join(child_ids), "media_type": "CAROUSEL"},
            plan_response={"id": placeholder("ig-parent-creation-id")})
        creation_id = _read_id(parent_resp, "create parent carousel container")

    # poll — count-bounded, never time-bounded (B22/s4.3). Dry-run renders ONE
    # poll step (its plan_response is FINISHED, so the loop breaks immediately).
    attempt = 0
    while True:
        attempt += 1
        status_resp = yield _Step(
            "instagram", "IG · poll container status", "GET",
            "{}/{}".format(_IG_HOST, creation_id),
            {"access_token": token, "fields": "status_code"},
            plan_response={"status_code": "FINISHED"})
        status = _read_status(status_resp)
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise AdapterRefusal(
                "Instagram container status {} for creation_id {}; row refused"
                .format(status, creation_id))
        if attempt >= MAX_POLL_ATTEMPTS:
            raise AdapterRefusal(
                "Instagram container did not finish after {} polls; row refused"
                .format(MAX_POLL_ATTEMPTS))
        sleep(POLL_DELAY_SECONDS)

    # publish (B23).
    pub_resp = yield _Step(
        "instagram", "IG · publish media", "POST",
        "{}/{}/media_publish".format(_IG_HOST, account_id),
        {"access_token": token, "creation_id": creation_id},
        plan_response={"id": placeholder("ig-media-id")})
    media_id = _read_id(pub_resp, "publish media")

    # permalink (B24).
    perma_resp = yield _Step(
        "instagram", "IG · fetch permalink", "GET",
        "{}/{}".format(_IG_HOST, media_id),
        {"access_token": token, "fields": "permalink"},
        plan_response={"permalink": placeholder("ig-permalink")})
    permalink = _read_permalink(perma_resp)
    return _IgResult(permalink=permalink, media_id=media_id)


def _drive_plan(gen):
    """Walk a flow generator WITHOUT a transport (dry-run): collect each yielded
    step's ``plan_dict`` and feed back its deterministic ``plan_response`` stub."""
    steps = []
    to_send = None
    while True:
        try:
            step = gen.send(to_send)
        except StopIteration:
            break
        steps.append(step.plan_dict())
        to_send = step.plan_response
    return steps


def _drive_execute(gen, transport):
    """Walk the SAME flow generator against an injected transport (execute): send
    each real request (bare url + urlencoded params + the step's request body),
    feed the parsed JSON response back. Returns the generator's return value (an
    ``_IgResult`` / ``_LiResult``).

    Generalized in Sprint 004 (contract s5.3), backward-compatible with IG:
    - **Request body** is ``step.execute_body()`` — file bytes for a binary upload
      (LinkedIn PUT), compact JSON for a dict/list payload (LinkedIn init/posts),
      and ``None`` for every Instagram step (no upload_path, null payload).
    - **Empty-response tolerance:** an empty/whitespace body (LinkedIn's empty
      ``PUT`` 201) feeds ``{}`` to the generator instead of raising; a non-empty
      NON-JSON body still raises ``AdapterRefusal``. IG bodies are always non-empty
      JSON, so IG never takes the empty branch.
    - The fed value is a ``_RespView`` (a dict carrying the response headers) so a
      LinkedIn post URN can be read from ``x-restli-id`` first; IG indexes it as a
      plain dict (unchanged)."""
    to_send = None
    while True:
        try:
            step = gen.send(to_send)
        except StopIteration as stop:
            return stop.value
        resp = transport.request(
            step.method, step.request_url(), headers=step.headers,
            body=step.execute_body())
        body = getattr(resp, "body", None)
        if body is None or not body.strip():
            parsed = {}
        else:
            try:
                parsed = resp.json()
            except ValueError:
                raise AdapterRefusal(
                    "non-JSON {} response for {}".format(
                        step.channel, step.label))
        if isinstance(parsed, dict):
            view = _RespView(parsed)
            view.headers = getattr(resp, "headers", {}) or {}
            to_send = view
        else:
            to_send = parsed


class InstagramAdapter(object):
    """Instagram Login adapter (graph.instagram.com). ``plan_steps`` and
    ``execute`` both derive from ``_ig_flow`` — the anti-stub guarantee (s1.1)."""

    channel = "instagram"

    def _slug(self, package, row):
        return package.get("slug") or row.get("slug")

    def _validate(self, package, row):
        """Attachment-count guard (B20/B2), run in BOTH modes (s3.1)."""
        attachments = package.get("attachments", [])
        n = len(attachments)
        slug = self._slug(package, row)
        if n == 0:
            raise AdapterUsageError(
                "instagram row ({}): no attachments to publish".format(slug))
        if n > _IG_MAX_CHILDREN:
            raise AdapterUsageError(
                "instagram carousel exceeds 10 children (got {}): Instagram "
                "allows at most 10 (R4-B2)".format(n))

    def _image_urls(self, package, row, base):
        slug = self._slug(package, row)
        return [image_url(base, slug, Path(a).name)
                for a in package.get("attachments", [])]

    def note(self, n_steps):
        return ("instagram adapter (Instagram Login, graph.instagram.com); {} "
                "HTTP calls; verified R4-B2/R4-B3/R5-3".format(n_steps))

    def plan_steps(self, row, package, base):
        """Dry-run: build the full ordered step list (no transport, no secret)."""
        self._validate(package, row)
        image_urls = self._image_urls(package, row, base)
        gen = _ig_flow(image_urls, package.get("caption", ""),
                       "<IG_USER_ID>", _REDACTED, lambda _s: None)
        return _drive_plan(gen)

    def execute(self, row, package, ctx, transport):
        """Live/test: walk the same flow against ``transport``. ``ctx`` supplies
        ``ig_user_id`` / ``ig_access_token`` / ``public_asset_base_url`` and an
        optional no-op ``sleep``. CLI-unreachable this sprint (Sprint 006 wires
        it into the live path); covered by the unit + parity tests (s1.2)."""
        self._validate(package, row)
        base = ctx.get("public_asset_base_url")
        account_id = ctx["ig_user_id"]
        token = ctx["ig_access_token"]
        sleep = ctx.get("sleep") or _default_sleep
        image_urls = self._image_urls(package, row, base)
        gen = _ig_flow(image_urls, package.get("caption", ""),
                       account_id, token, sleep)
        return _drive_execute(gen, transport)


# --------------------------------------------------------------------------- #
# LinkedIn adapter (verified — R4-B4, R5-6). Member-profile posting; BOTH organic
# flows implemented, EXACTLY ONE executed per row. Shares the plan-driver /
# execute-driver split with Instagram (the anti-stub guarantee, contract s1.1).
# --------------------------------------------------------------------------- #
def _li_headers(token, version):
    """Versioned headers on a JSON ``/rest/*`` call (B28). The plan passes
    ``token=<REDACTED>`` so ``Authorization`` renders ``Bearer <REDACTED>``;
    execute passes the real token (sent only over the wire, never emitted)."""
    return {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "LinkedIn-Version": version,
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _li_put_headers(token):
    """The binary-upload PUT carries ONLY Authorization (B28 / s4 common rules)."""
    return {"Authorization": "Bearer " + token}


def _read_li_init_image(resp):
    """images initializeUpload → (value.uploadUrl, value.image). Missing → refusal."""
    try:
        return resp["value"]["uploadUrl"], resp["value"]["image"]
    except (KeyError, TypeError):
        raise AdapterRefusal(
            "unexpected LinkedIn response for initialize image upload")


def _read_li_init_document(resp):
    """documents initializeUpload → (value.uploadUrl, value.document)."""
    try:
        return resp["value"]["uploadUrl"], resp["value"]["document"]
    except (KeyError, TypeError):
        raise AdapterRefusal(
            "unexpected LinkedIn response for initialize document upload")


def _read_li_post_urn(resp):
    """/rest/posts → the created post URN. LinkedIn returns it in the
    ``x-restli-id`` response HEADER (live-faithful, R5); the body ``id`` is the
    fallback that the mock (headers={}) exercises. Isolated in ONE helper so a
    founder correction touches a single place. Missing both → refusal."""
    headers = getattr(resp, "headers", None) or {}
    urn = headers.get("x-restli-id")
    if not urn and hasattr(resp, "get"):
        urn = resp.get("id")
    if not urn:
        raise AdapterRefusal(
            "unexpected LinkedIn response for create post "
            "(no x-restli-id header or body id)")
    return urn


# --- /rest/posts bodies (B26/B27 mandated fields + isolated live-pending extras).
# The `distribution` block, `content.media.title`, and the Content-Type header are
# faithful to the Posts API cited in R4-B4 but NOT independently verified; they are
# frozen for determinism and isolated here so a founder correction touches ONE
# builder. Tests assert the MANDATED fields, not the exact live-pending structure.
def _li_document_post_body(owner, caption, document_urn, title):
    return {
        "author": owner,
        "commentary": caption,
        "content": {"media": {"id": document_urn, "title": title}},
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "visibility": "PUBLIC",
    }


def _li_multiimage_post_body(owner, caption, image_urns):
    return {
        "author": owner,
        "commentary": caption,
        "content": {"multiImage": {"images": [{"id": u} for u in image_urns]}},
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "visibility": "PUBLIC",
    }


def _li_document_flow(pdf_filename, pdf_path, caption, owner, token, version,
                      title):
    """The SINGLE LinkedIn DOCUMENT-flow definition (B27, DEFAULT). 3 calls:
    initialize document upload → PUT the PDF bytes → create the document post.
    The plan driver passes ``<LI_PERSON_URN>`` / ``<REDACTED>`` + placeholder ids;
    execute passes the real owner/token + threads the real uploadUrl/document URN.
    Permalink (B29) is CONSTRUCTED from the returned post URN — NO 4th call."""
    init_resp = yield _Step(
        "linkedin", "LI · initialize document upload", "POST",
        _LI_HOST + "/rest/documents", {"action": "initializeUpload"},
        headers=_li_headers(token, version),
        payload={"initializeUploadRequest": {"owner": owner}},
        plan_response={"value": {
            "uploadUrl": placeholder("li-upload-url", 1),
            "document": placeholder("li-document-urn")}})
    upload_url, document_urn = _read_li_init_document(init_resp)

    yield _Step(
        "linkedin", "LI · upload document bytes", "PUT",
        upload_url, {},
        headers=_li_put_headers(token),
        payload="<binary PDF: {}>".format(pdf_filename),
        upload_path=pdf_path)

    post_resp = yield _Step(
        "linkedin", "LI · create document post", "POST",
        _LI_HOST + "/rest/posts", {},
        headers=_li_headers(token, version),
        payload=_li_document_post_body(owner, caption, document_urn, title),
        plan_response={"id": placeholder("li-post-urn")})
    post_urn = _read_li_post_urn(post_resp)
    return _LiResult(
        permalink=_LI_PERMALINK_PREFIX + post_urn, post_urn=post_urn)


def _li_multiimage_flow(attachments, caption, owner, token, version):
    """The SINGLE LinkedIn MULTIIMAGE-flow definition (B26). For N images:
    interleaved (initialize image upload i → PUT image bytes i) ×N, then one
    create multi-image post. Total 2N+1 calls (7 for N=3)."""
    n = len(attachments)
    image_urns = []
    for i, attachment in enumerate(attachments, start=1):
        init_resp = yield _Step(
            "linkedin",
            "LI · initialize image upload {}/{}".format(i, n), "POST",
            _LI_HOST + "/rest/images", {"action": "initializeUpload"},
            headers=_li_headers(token, version),
            payload={"initializeUploadRequest": {"owner": owner}},
            plan_response={"value": {
                "uploadUrl": placeholder("li-upload-url", i),
                "image": placeholder("li-image-urn", i)}})
        upload_url, image_urn = _read_li_init_image(init_resp)

        yield _Step(
            "linkedin",
            "LI · upload image bytes {}/{}".format(i, n), "PUT",
            upload_url, {},
            headers=_li_put_headers(token),
            payload="<binary PNG: {}>".format(Path(attachment).name),
            upload_path=attachment)
        image_urns.append(image_urn)

    post_resp = yield _Step(
        "linkedin", "LI · create multi-image post", "POST",
        _LI_HOST + "/rest/posts", {},
        headers=_li_headers(token, version),
        payload=_li_multiimage_post_body(owner, caption, image_urns),
        plan_response={"id": placeholder("li-post-urn")})
    post_urn = _read_li_post_urn(post_resp)
    return _LiResult(
        permalink=_LI_PERMALINK_PREFIX + post_urn, post_urn=post_urn)


class LinkedInAdapter(object):
    """LinkedIn member-profile adapter (api.linkedin.com/rest/*). ``plan_steps``
    and ``execute`` both derive from ``_li_document_flow`` / ``_li_multiimage_flow``
    — the anti-stub guarantee (s1.1). EXACTLY ONE flow per row (R4-B4)."""

    channel = "linkedin"

    def _slug(self, package, row):
        return package.get("slug") or row.get("slug")

    def _manifest_pdf(self, row, package):
        """Resolve the render manifest's ``pdf`` (filename, absolute-ish path) for
        the document flow (contract s3). Raises ``AdapterUsageError`` (exit 2) when
        the manifest is missing/unreadable or carries no non-empty ``pdf``."""
        slug = self._slug(package, row)
        manifest_path = (
            Path(row["package_path"]).parent.parent / "render" / "manifest.json")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise AdapterUsageError(
                "linkedin row ({}): render manifest not found at {} (needed for "
                "the document flow)".format(slug, manifest_path))
        pdf = manifest.get("pdf")
        if not pdf:
            raise AdapterUsageError(
                "linkedin row ({}): manifest has no 'pdf' (needed for the "
                "document flow)".format(slug))
        return pdf, str(manifest_path.parent / pdf)

    def _validate(self, row, package, post_type):
        """Precondition guards (s3.1), run in BOTH dry-run and execute."""
        slug = self._slug(package, row)
        if post_type == "document":
            self._manifest_pdf(row, package)  # raises on missing manifest/pdf
        else:
            n = len(package.get("attachments", []))
            if n == 0:
                raise AdapterUsageError(
                    "linkedin row ({}): no attachments to publish "
                    "(multi-image)".format(slug))
            if n > _LI_MAX_IMAGES:
                raise AdapterUsageError(
                    "linkedin multi-image exceeds 20 images (got {})".format(n))

    def _flow(self, row, package, owner, token, version, post_type):
        caption = package.get("caption", "")
        if post_type == "document":
            slug = self._slug(package, row)
            pdf_filename, pdf_path = self._manifest_pdf(row, package)
            return _li_document_flow(
                pdf_filename, pdf_path, caption, owner, token, version, slug)
        return _li_multiimage_flow(
            package.get("attachments", []), caption, owner, token, version)

    def note(self, n_steps, post_type):
        flow = "document" if post_type == "document" else "multi-image"
        return ("linkedin adapter (member profile, api.linkedin.com; {} flow); "
                "{} HTTP calls; verified R4-B4/R5-6".format(flow, n_steps))

    def plan_steps(self, row, package, base, post_type, version):
        """Dry-run: build the full ordered step list (no transport, no secret,
        no byte read). ``base`` is unused (LinkedIn uploads bytes, not URLs)."""
        self._validate(row, package, post_type)
        gen = self._flow(
            row, package, _LI_PERSON_URN_PLACEHOLDER, _REDACTED, version,
            post_type)
        return _drive_plan(gen)

    def execute(self, row, package, ctx, transport):
        """Live/test: walk the same flow against ``transport``. ``ctx`` supplies
        ``li_person_urn`` / ``li_access_token`` / ``linkedin_post_type`` /
        ``linkedin_version``. CLI-unreachable this sprint (Sprint 006 wires it into
        the live path); covered by the unit + parity tests (s1.2)."""
        post_type = ctx.get("linkedin_post_type", "document")
        version = ctx.get("linkedin_version", LINKEDIN_VERSION_DEFAULT)
        self._validate(row, package, post_type)
        gen = self._flow(
            row, package, ctx["li_person_urn"], ctx["li_access_token"],
            version, post_type)
        return _drive_execute(gen, transport)


# --------------------------------------------------------------------------- #
# Facebook Page adapter — ROUND-5-GAP (R4-B5, UNVERIFIED best-documented-guess).
# The photos+feed flow (B32) is a documented GUESS, gated behind --enable-facebook
# (default OFF). Like Instagram/LinkedIn, ``plan_steps`` and ``execute`` both
# derive from the SINGLE ``_fb_flow`` generator (the anti-stub guarantee, s1.2);
# it reuses the frozen ``_drive_plan`` / ``_drive_execute`` drivers + ``_Step``
# model unchanged. Reuses the SAME Instagram PNG assets (R4-A3) — zero FB-specific
# creative. WHO may post is verified (R5-4); the HOW below is NOT (R4-B5).
# --------------------------------------------------------------------------- #
def _read_fb_id(resp, step_label):
    """POST /photos or /feed → the returned object ``id`` (an unpublished photo id
    or the feed post id). Missing/malformed → ``AdapterRefusal`` (exit 1 in a
    future live path; surfaced via unit tests this sprint). ROUND-5-GAP: the
    response shape is an unverified guess (R4-B5). Reused for photo id + post id."""
    try:
        return resp["id"]
    except (KeyError, TypeError):
        raise AdapterRefusal(
            "unexpected Facebook response for {}".format(step_label))


def _fb_flow(image_urls, caption, page_id, token):
    """The SINGLE Facebook photos+feed flow definition (B32) — ROUND-5-GAP,
    best-documented-guess pending live verification (R4-B5). For N images the flow
    is N+1 calls: N unpublished photo uploads, then ONE feed post that stitches the
    photo ids via ``attached_media``. The permalink is CONSTRUCTED from the post id
    (no extra call) using the guessed ``_FB_PERMALINK_PREFIX``.

    A generator yielding ``_Step`` and receiving each step's parsed response via
    ``.send`` — same protocol as ``_ig_flow``. The PLAN driver passes
    ``<FB_PAGE_ID>`` / ``<REDACTED>`` / placeholder image urls (deterministic,
    secret-free); EXECUTE passes the real page id / token / concrete urls. Each
    photo id (a placeholder in the plan, a real id in execute) is read from its
    response and threaded verbatim into the feed step's ``attached_media`` —
    proving dependent-value flow (B10). Returns an ``_FbResult`` on success;
    raises ``AdapterRefusal`` on an unexpected response."""
    n = len(image_urls)
    photo_ids = []
    for i, url in enumerate(image_urls, start=1):
        photo_resp = yield _Step(
            "facebook",
            "FB · upload unpublished photo {}/{}".format(i, n), "POST",
            "{}/{}/photos".format(_FB_HOST, page_id),
            {"access_token": token, "published": "false", "url": url},
            plan_response={"id": placeholder("fb-photo-id", i)})
        photo_ids.append(_read_fb_id(photo_resp, "upload photo {}".format(i)))

    # attached_media: compact deterministic JSON of the ordered photo ids (B10).
    attached_media = json.dumps(
        [{"media_fbid": pid} for pid in photo_ids],
        sort_keys=True, separators=(",", ":"))

    feed_resp = yield _Step(
        "facebook", "FB · create feed post", "POST",
        "{}/{}/feed".format(_FB_HOST, page_id),
        {"access_token": token, "attached_media": attached_media,
         "message": caption},
        plan_response={"id": placeholder("fb-post-id")})
    post_id = _read_fb_id(feed_resp, "create feed post")
    return _FbResult(
        permalink=_FB_PERMALINK_PREFIX + post_id, post_id=post_id)


class FacebookAdapter(object):
    """Facebook Page adapter (graph.facebook.com; photos+feed) — ROUND-5-GAP,
    best-documented-guess pending live verification (R4-B5). ``plan_steps`` and
    ``execute`` both derive from ``_fb_flow`` (the anti-stub guarantee, s1.2).
    Gated behind --enable-facebook (default OFF); when OFF the row is skipped with
    a cited notice (§7.1) BEFORE this adapter is ever entered — so this class runs
    only when the operator has explicitly opted into the unverified guess."""

    channel = "facebook"

    def _slug(self, package, row):
        return package.get("slug") or row.get("slug")

    def _validate(self, package, row):
        """G1: at least one attachment. NO upper-bound cap — the FB feed
        attachment limit is part of the unverified R4-B5 gap; inventing a hard
        gate here would dress a guess up as fact (contract s3 G1)."""
        n = len(package.get("attachments", []))
        if n == 0:
            slug = self._slug(package, row)
            raise AdapterUsageError(
                "facebook row ({}): no attachments to publish".format(slug))

    def _image_urls(self, package, row, base):
        slug = self._slug(package, row)
        return [image_url(base, slug, Path(a).name)
                for a in package.get("attachments", [])]

    def note(self, n_steps):
        """Enabled-row note (contract s4.4). ``n_steps`` == N+1 (N photo uploads +
        1 feed post). Always carries ``round-5-gap`` + ``best-documented-guess``."""
        return ("facebook adapter (Page feed, graph.facebook.com; photos+feed "
                "flow); {} HTTP calls; round-5-gap: best-documented-guess pending "
                "live verification (R4-B5)".format(n_steps))

    def plan_steps(self, row, package, base):
        """Dry-run: build the full ordered step list (no transport, no secret).
        Signature mirrors ``InstagramAdapter.plan_steps``."""
        self._validate(package, row)
        image_urls = self._image_urls(package, row, base)
        gen = _fb_flow(image_urls, package.get("caption", ""),
                       _FB_PAGE_ID_PLACEHOLDER, _REDACTED)
        return _drive_plan(gen)

    def execute(self, row, package, ctx, transport):
        """Live/test: walk the same flow against ``transport``. ``ctx`` supplies
        ``fb_page_id`` / ``fb_page_token`` / ``public_asset_base_url``.
        CLI-unreachable this sprint (Sprint 006 wires it into the live path);
        covered by the unit + parity tests (s1.3)."""
        self._validate(package, row)
        base = ctx.get("public_asset_base_url")
        page_id = ctx["fb_page_id"]
        token = ctx["fb_page_token"]
        image_urls = self._image_urls(package, row, base)
        gen = _fb_flow(image_urls, package.get("caption", ""), page_id, token)
        return _drive_execute(gen, transport)


def _fb_skip_notice(slug):
    """The EXACT skip NOTICE line (contract s7.1), single source shared by the
    dry-run and live-off paths so they never drift."""
    return ("NOTICE: facebook row ({}) skipped: facebook adapter disabled; pass "
            "--enable-facebook (round-5-gap, unverified)".format(slug))


# Adapter registry. instagram + linkedin + facebook (round-5-gap, gated).
_ADAPTERS = {"instagram": InstagramAdapter(), "linkedin": LinkedInAdapter(),
             "facebook": FacebookAdapter()}


def _load_package(package_path):
    """Load + parse a row's package JSON (existence/parseability already checked
    in run() before dispatch)."""
    return json.loads(Path(package_path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Plan model + deterministic writer.
# --------------------------------------------------------------------------- #
def _note_for(channel):
    """The row `note` string (single source, shared by JSON + stdout)."""
    sprint = _CHANNEL_SPRINT.get(channel, "003+")
    return "no adapter registered for channel '{}' (lands in Sprint {})".format(
        channel, sprint)


def _build_plan(week, mode, rows, base=None,
                linkedin_post_type="document",
                linkedin_version=LINKEDIN_VERSION_DEFAULT,
                enable_facebook=False):
    """Build the plan envelope (contract s7.1). ``rows`` in (slug, channel) order.

    Each entry copies ``package_path`` verbatim. A row whose channel has a
    registered adapter (instagram + linkedin + facebook) gets the adapter's full
    ordered ``steps`` + adapter ``note``. Facebook is SPECIAL (round-5-gap, B30):
    when ``enable_facebook`` is False (the default) a facebook row is listed with
    ``steps=[]`` + the disabled note and the adapter is NEVER entered (no guard
    runs); only with ``enable_facebook`` True does it render the guessed flow.
    Branch order (contract s8): facebook-disabled → facebook-enabled → linkedin →
    other-adapter (instagram) → youtube.

    May raise ``AdapterUsageError`` (IG 0/>10 attachments; LI missing manifest/pdf
    or 0/>20 attachments; enabled FB 0 attachments) — the caller maps it to exit 2
    BEFORE any plan is written.
    """
    plan_rows = []
    for r in rows:
        channel = r["channel"]
        adapter = _ADAPTERS.get(channel)
        if channel == "facebook" and not enable_facebook:
            # ROUND-5-GAP gate OFF (the default): skip-with-notice. The adapter
            # code (and its guards) is never entered; the row is listed for
            # legibility + deterministic diffing with an empty step list.
            steps = []
            note = _FB_DISABLED_NOTE
        elif channel == "facebook":
            package = _load_package(r["package_path"])
            steps = adapter.plan_steps(r, package, base)
            note = adapter.note(len(steps))
        elif channel == "linkedin":
            package = _load_package(r["package_path"])
            steps = adapter.plan_steps(
                r, package, base, linkedin_post_type, linkedin_version)
            note = adapter.note(len(steps), linkedin_post_type)
        elif adapter is not None:
            package = _load_package(r["package_path"])
            steps = adapter.plan_steps(r, package, base)
            note = adapter.note(len(steps))
        else:
            steps = []
            note = _note_for(channel)
        plan_rows.append({
            "slug": r["slug"],
            "channel": channel,
            "package_path": r.get("package_path"),
            "note": note,
            "steps": steps,
        })
    return {
        "schema_version": _PLAN_SCHEMA_VERSION,
        "week": week,
        "mode": mode,
        "rows": plan_rows,
    }


def plan_dumps(plan):
    """Serialize a plan deterministically (contract s7.2): sort_keys, indent 2,
    single trailing newline — mirroring ``queue.dumps`` style."""
    return json.dumps(plan, sort_keys=True, indent=2) + "\n"


def _escape_stdout(value):
    """Escape newlines in a param VALUE to the literal two-char sequence ``\\n`` so
    the line-oriented stdout template stays intact + byte-assertable (contract
    s7.2). The machine JSON keeps the value VERBATIM (real newlines, B5)."""
    return str(value).replace("\r\n", "\\n").replace("\n", "\\n").replace(
        "\r", "\\n")


def _render_step_params(params):
    """Render a step's params as ``k1=v1, k2=v2`` (keys SORTED), or ``(none)``."""
    if not params:
        return "(none)"
    return ", ".join(
        "{}={}".format(k, _escape_stdout(params[k])) for k in sorted(params))


def _render_step_headers(headers):
    """Render a step's headers as ``k1: v1, k2: v2`` (keys SORTED). Secret-bearing
    values already carry ``<REDACTED>`` (contract s6). Only called when non-empty."""
    return ", ".join(
        "{}: {}".format(k, headers[k]) for k in sorted(headers))


def _render_step_payload(payload):
    """Render a step's payload (contract s6). A dict/list renders as compact
    deterministic JSON (``sort_keys``, default ``ensure_ascii`` — real newlines
    become the two-char ``\\n``, non-ASCII becomes ``\\uXXXX``, matching the
    machine plan's ``plan_dumps``). A string (the binary placeholder) is verbatim."""
    if isinstance(payload, (dict, list)):
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return str(payload)


def _render_plan_stdout(plan, plan_path):
    """Render the human-readable stdout plan (contract s7.2, exact template)."""
    lines = []
    week = plan["week"]
    mode = plan["mode"]
    rows = plan["rows"]
    lines.append("Publishing plan for week {} (mode: {})".format(week, mode))
    n = len(rows)
    for i, r in enumerate(rows, start=1):
        lines.append("")
        lines.append("Row {}/{}: {} ({})".format(i, n, r["slug"], r["channel"]))
        lines.append("  package: {}".format(r["package_path"]))
        lines.append("  steps: {}".format(len(r["steps"])))
        for j, s in enumerate(r["steps"], start=1):
            lines.append("    {}. {}".format(j, s["label"]))
            lines.append("       {} {}".format(s["method"], s["url"]))
            lines.append("       params: {}".format(
                _render_step_params(s["params"])))
            # Conditional (contract s6): render a headers line ONLY when non-empty
            # and a payload line ONLY when non-null, so IG steps (headers {},
            # payload null) stay byte-identical to the Sprint-003 template.
            headers = s.get("headers") or {}
            if headers:
                lines.append("       headers: {}".format(
                    _render_step_headers(headers)))
            if s.get("payload") is not None:
                lines.append("       payload: {}".format(
                    _render_step_payload(s["payload"])))
        lines.append("  note: {}".format(r["note"]))
    lines.append("")
    lines.append("Plan written to {}".format(plan_path))
    return lines


# --------------------------------------------------------------------------- #
# Live-mode precondition gate (B12/B13).
# --------------------------------------------------------------------------- #
def _live_gate(in_scope_channels, enable_facebook, env_path,
               public_asset_base_url, i_have_verified_dry_run, date):
    """Check ALL live preconditions independently (B12/B13, contract s4.5).

    Returns ``(failures, env, base)``: ``failures`` is a list of cited failure
    messages (empty => gate passes); ``env`` is the parsed ``.env`` dict (so the
    live driver builds ``ctx`` WITHOUT re-parsing); ``base`` is the resolved
    public-asset base URL. FAILURE MESSAGES + GATE BEHAVIOR are byte-identical to
    Sprint 002/005 — this refactor only additionally RETURNS env + base. Never
    echoes any secret value."""
    failures = []

    # (c-adjacent) --date is a live precondition of its own (contract s3.3).
    if not date:
        failures.append(
            "ERROR: --live requires --date YYYY-MM-DD (the posted-date; never "
            "the wall clock)")

    # (a) .env tokens for the in-scope channels.
    env = {}
    ep = Path(env_path)
    if not ep.exists():
        failures.append(
            "ERROR: --live requires an env file at {} (holding the platform "
            "tokens); not found".format(env_path))
    else:
        env, err = parse_env(ep.read_text(encoding="utf-8"))
        if err is not None:
            failures.append("ERROR: {}".format(err))
            env = {}
        else:
            required = []
            for ch in sorted(in_scope_channels):
                if ch == "facebook" and not enable_facebook:
                    continue
                required.extend(_CHANNEL_TOKENS.get(ch, ()))
            missing = [k for k in required if not env.get(k)]
            if missing:
                failures.append(
                    "ERROR: --live is missing required token(s) in {}: {} "
                    "(values never echoed)".format(
                        env_path, ", ".join(sorted(set(missing)))))

    # (b) PUBLIC_ASSET_BASE_URL: --public-asset-base-url flag OR .env value.
    base = public_asset_base_url or env.get("PUBLIC_ASSET_BASE_URL")
    if not base:
        failures.append(
            "ERROR: --live requires PUBLIC_ASSET_BASE_URL (via "
            "--public-asset-base-url or a PUBLIC_ASSET_BASE_URL line in the "
            "env file)")

    # (c) explicit acknowledgment flag.
    if not i_have_verified_dry_run:
        failures.append(
            "ERROR: --live requires --i-have-verified-dry-run; run a --dry-run "
            "first and inspect the plan")

    return failures, env, base


# --------------------------------------------------------------------------- #
# Live driver (Sprint 006): the real queued->posted path. Reuses the frozen
# adapter execute() flows + mark_posted.transition — nothing here re-derives an
# API fact or re-implements the transition.
# --------------------------------------------------------------------------- #
def _build_ctx(env, base, linkedin_post_type, linkedin_version):
    """Map the parsed ``.env`` + resolved flags onto the per-adapter ctx keys the
    frozen ``execute`` methods already consume (contract s2 ctx builder). Tokens
    are carried in memory ONLY — into ``execute`` -> the transport (over the wire);
    never echoed. ``sleep`` is intentionally omitted so IG polling uses the real
    ``_default_sleep`` under a live run (tests inject their own no-op via ctx)."""
    return {
        "ig_user_id": env.get("IG_USER_ID"),
        "ig_access_token": env.get("IG_ACCESS_TOKEN"),
        "li_person_urn": env.get("LI_PERSON_URN"),
        "li_access_token": env.get("LI_ACCESS_TOKEN"),
        "linkedin_post_type": linkedin_post_type,
        "linkedin_version": linkedin_version,
        "fb_page_id": env.get("FB_PAGE_ID"),
        "fb_page_token": env.get("FB_PAGE_TOKEN"),
        "public_asset_base_url": base,
    }


def _required_upload_paths(row, package, ctx):
    """The local files whose BYTES an adapter's ``execute`` reads mid-flow
    (contract s4.4). Dry-run does "no byte read", so these are the paths the live
    pre-validation must confirm exist on disk BEFORE any post. Instagram/Facebook
    upload by URL (no local bytes) => []. LinkedIn document => the manifest PDF;
    LinkedIn multi-image => the package attachments."""
    if row["channel"] != "linkedin":
        return []
    post_type = ctx.get("linkedin_post_type", "document")
    if post_type == "document":
        # Reuse the frozen adapter's manifest resolution (single source of truth).
        _fn, pdf_path = _ADAPTERS["linkedin"]._manifest_pdf(row, package)
        return [pdf_path]
    return list(package.get("attachments", []))


def _run_live(selected, q, queue_path, date, max_per_day, ctx, transport,
              enable_facebook):
    """The live driver (contract s5/s6). For each in-scope ``queued`` row in
    ``(slug, channel)`` order: enforce the per-day cap, ``execute`` against the
    injected ``transport``, transition ``queued -> posted`` via
    ``mark_posted.transition``, and write the queue INCREMENTALLY (after each
    success) so a later refusal leaves earlier posts persisted. Returns
    ``(exit_code, stdout, stderr)``. NEVER writes ``publish-plan.json`` (contract
    s7). Facebook posts only when ``enable_facebook`` (round-5-gap); when OFF a
    facebook row is skipped with the NOTICE and does NOT consume cap budget."""
    stdout, stderr = [], []

    # Per-day cap baseline (B16, contract s5): count ONCE, across the WHOLE loaded
    # queue, rows already ``posted`` on ``--date``. A single baseline + a run
    # counter avoids double-counting after each incremental write.
    baseline = sum(
        1 for r in q["rows"]
        if r.get("state") == queue.STATE_POSTED and r.get("posted_date") == date)
    made = 0
    current_q = q

    for r in selected:
        slug, channel = r["slug"], r["channel"]

        # Facebook (round-5-gap) with the flag OFF: skip with the exact NOTICE;
        # no transition, no cap consumption, run continues (contract s8).
        if channel == "facebook" and not enable_facebook:
            stderr.append(_fb_skip_notice(slug))
            continue

        # Per-day cap breach (B16): refuse this row, stop; prior posts stand.
        if baseline + made >= max_per_day:
            stderr.append(
                "REFUSED ({}, {}): would exceed the per-day cap of {} post(s) "
                "for {} (day-cap)".format(slug, channel, max_per_day, date))
            return 1, stdout, stderr

        adapter = _ADAPTERS[channel]
        package = _load_package(r["package_path"])
        try:
            result = adapter.execute(r, package, ctx, transport)
        except AdapterRefusal as exc:
            # Domain refusal surfaced from the adapter (container ERROR, rate
            # limit, unexpected shape) -> exit 1; prior posts persisted (s4.2).
            stderr.append("REFUSED ({}, {}): {}".format(slug, channel, exc))
            return 1, stdout, stderr
        except (AdapterUsageError, OSError) as exc:
            # Missing/unreadable local upload bytes surfaced mid-flow -> exit 2;
            # prior siblings persisted (contract s4.4). The up-front precondition
            # makes this rare, but a race is still exit 2, not a traceback.
            stderr.append("ERROR: {}".format(exc))
            return 2, stdout, stderr

        # Transition reuses the FROZEN mark_posted semantics (B14/B15) — same
        # field-setting + no-regress guard + deterministic write.
        new_q, status = mark_posted.transition(
            current_q, slug, channel, date, result.permalink)
        if status != "posted":
            # Defense-in-depth (contract s3): selection is queued-only, so this is
            # unreachable in practice; surfaced as the no-double-post refusal.
            stderr.append(
                "REFUSED ({}, {}): row is already posted; refusing to re-post "
                "(no double-post)".format(slug, channel))
            return 1, stdout, stderr

        queue.write_queue(queue_path, new_q)  # incremental persistence (s6)
        current_q = new_q
        made += 1
        stdout.append("posted {} {} {}".format(slug, channel, date))
        stdout.append("  permalink: {}".format(result.permalink))

    return 0, stdout, stderr


# --------------------------------------------------------------------------- #
# Core entry points (frozen signatures — contract s1.1).
# --------------------------------------------------------------------------- #
def run(
    week,
    slug=None,
    channel=None,
    mode="dry-run",
    queue_path=_DEFAULT_QUEUE,
    date=None,
    max_per_day=3,
    enable_facebook=False,
    linkedin_post_type="document",
    linkedin_version=LINKEDIN_VERSION_DEFAULT,
    public_asset_base_url=None,
    env_path=_DEFAULT_ENV,
    i_have_verified_dry_run=False,
    transport=None,
):
    """Run the publish pipeline. Returns ``(exit_code, stdout_lines, stderr_lines)``.

    Buffers all output as line lists (no direct print), exactly like
    ``mark_posted.run``. When ``transport is None`` the default ``Transport()`` is
    constructed; tests pass ``RecordingTransport()`` / ``RaisingTransport()``.
    This sprint the adapter registry is empty, so ``transport`` is held but
    invoked zero times.
    """
    stdout, stderr = [], []
    if transport is None:
        transport = Transport()

    # --- basic argument validation (exit 2, no write, no network) --------- #
    if not week or not _WEEK_RE.match(week):
        stderr.append(
            "ERROR: --week must be 'YYYY-Www' (e.g. 2026-W28); got {!r}".format(week))
        return 2, stdout, stderr

    if mode not in ("dry-run", "live"):
        stderr.append("ERROR: mode must be 'dry-run' or 'live'; got {!r}".format(mode))
        return 2, stdout, stderr

    if linkedin_post_type not in ("document", "multi-image"):
        stderr.append(
            "ERROR: --linkedin-post-type must be 'document' or 'multi-image'; "
            "got {!r}".format(linkedin_post_type))
        return 2, stdout, stderr

    if not _LI_VERSION_RE.match(linkedin_version or ""):
        stderr.append(
            "ERROR: --linkedin-version must be a 'YYYYMM' string (6 digits, e.g. "
            "202506); got {!r}".format(linkedin_version))
        return 2, stdout, stderr

    if not isinstance(max_per_day, int) or isinstance(max_per_day, bool) \
            or max_per_day < 1:
        stderr.append("ERROR: --max-per-day must be an integer >= 1; got {!r}".format(
            max_per_day))
        return 2, stdout, stderr

    if date is not None:
        if not _DATE_RE.match(date):
            stderr.append(
                "ERROR: --date must be 'YYYY-MM-DD'; got {!r}".format(date))
            return 2, stdout, stderr
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            stderr.append(
                "ERROR: --date {!r} is not a real calendar date".format(date))
            return 2, stdout, stderr

    if channel is not None and channel not in queue.VALID_CHANNELS:
        stderr.append(
            "ERROR: unknown --channel {!r} (expected one of {})".format(
                channel, sorted(queue.VALID_CHANNELS)))
        return 2, stdout, stderr

    # --- load + select queue rows ----------------------------------------- #
    try:
        q = queue.load_queue(queue_path)
    except ValueError as exc:
        stderr.append("ERROR: {}".format(exc))
        return 2, stdout, stderr

    selected = [
        r for r in q["rows"]
        if r.get("state") == queue.STATE_QUEUED
        and r.get("week") == week
        and (slug is None or r.get("slug") == slug)
        and (channel is None or r.get("channel") == channel)
    ]
    selected.sort(key=lambda r: (r["slug"], r["channel"]))

    # --- empty state (fires BEFORE the live gate; no plan/queue write) ----- #
    if not selected:
        # Targeted already-posted refusal (B15, contract s4.1): in --live ONLY,
        # when BOTH --slug and --channel pin exactly one (slug, channel) row that
        # is already ``posted`` (no queued row in scope), REFUSE with exit 1 in the
        # mark_posted idiom (the no-double-post guard made observable). Any broader
        # empty scope falls through to the exit-0 "nothing queued" message — so an
        # already-posted week re-run is exit 0, never exit 1 (Gate 3 vs Gate 4).
        if mode == "live" and slug is not None and channel is not None:
            already = [
                r for r in q["rows"]
                if r.get("state") == queue.STATE_POSTED
                and r.get("week") == week
                and r.get("slug") == slug
                and r.get("channel") == channel
            ]
            if already:
                stderr.append(
                    "REFUSED ({}, {}): row is already posted; refusing to "
                    "re-post (no double-post)".format(slug, channel))
                return 1, stdout, stderr
        filters = []
        if slug is not None:
            filters.append("slug={}".format(slug))
        if channel is not None:
            filters.append("channel={}".format(channel))
        suffix = " ({})".format(", ".join(filters)) if filters else ""
        stderr.append("nothing queued for {}{}".format(week, suffix))
        return 0, stdout, stderr

    in_scope_channels = {r["channel"] for r in selected}

    # --- live gate (post-empty, pre-package, pre-dispatch) ----------------- #
    live_env, live_base = {}, None
    if mode == "live":
        failures, live_env, live_base = _live_gate(
            in_scope_channels, enable_facebook, env_path,
            public_asset_base_url, i_have_verified_dry_run, date)
        if failures:
            stderr.extend(failures)
            return 2, stdout, stderr

    # --- package existence + JSON-parseability validation (B4, s5.1a) ------ #
    # Runs in (slug, channel) order; the FIRST failing package aborts with exit
    # 2 (no partial plan). Existence/parseability only — no field consumed.
    for r in selected:
        pkg_path = r.get("package_path")
        if not pkg_path:
            stderr.append(
                "ERROR: package_path missing for ({}, {})".format(
                    r["slug"], r["channel"]))
            return 2, stdout, stderr
        pp = Path(pkg_path)
        if not pp.exists():
            stderr.append(
                "ERROR: package not found for ({}, {}): {}".format(
                    r["slug"], r["channel"], pkg_path))
            return 2, stdout, stderr
        try:
            json.loads(pp.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            stderr.append(
                "ERROR: package {} is not valid JSON: {}".format(pkg_path, exc))
            return 2, stdout, stderr

    # --- dispatch ---------------------------------------------------------- #
    if mode == "live":
        # §4.3 usage pre-validation: build the plan IN MEMORY (the SAME adapter
        # validation dry-run uses — 0/>10 IG children, LI missing manifest, etc.)
        # with the live flags. Any AdapterUsageError -> exit 2 BEFORE any post,
        # NO network, NO queue write. The in-memory plan is DISCARDED (live must
        # NOT write publish-plan.json, contract s7).
        ctx = _build_ctx(live_env, live_base, linkedin_post_type, linkedin_version)
        try:
            _build_plan(
                week, "live", selected, live_base,
                linkedin_post_type, linkedin_version,
                enable_facebook=enable_facebook)
        except AdapterUsageError as exc:
            stderr.append("ERROR: {}".format(exc))
            return 2, stdout, stderr

        # §4.4 upload-byte precondition: dry-run does "no byte read", so confirm
        # every required local upload file exists on disk UP FRONT (so nothing
        # posts when a later row's bytes are missing). Facebook-disabled rows are
        # skipped (never posted). Missing/unreadable -> exit 2, cited, no post.
        for r in selected:
            if r["channel"] == "facebook" and not enable_facebook:
                continue
            package = _load_package(r["package_path"])
            for upath in _required_upload_paths(r, package, ctx):
                p = Path(upath)
                if not p.exists() or not p.is_file():
                    stderr.append(
                        "ERROR: local upload file missing for ({}, {}): {} "
                        "(required by the live upload flow)".format(
                            r["slug"], r["channel"], upath))
                    return 2, stdout, stderr

        return _run_live(
            selected, q, queue_path, date, max_per_day, ctx, transport,
            enable_facebook)

    # dry-run (the default): build + write the plan, echo to stdout, exit 0.
    # A >10 / 0-attachment package is an AdapterUsageError -> exit 2, NO write.
    try:
        plan = _build_plan(
            week, mode, selected, public_asset_base_url,
            linkedin_post_type, linkedin_version,
            enable_facebook=enable_facebook)
    except AdapterUsageError as exc:
        stderr.append("ERROR: {}".format(exc))
        return 2, stdout, stderr
    plan_path = Path(queue_path).parent / _PLAN_FILENAME
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(plan_dumps(plan), encoding="utf-8")
    stdout.extend(_render_plan_stdout(plan, str(plan_path)))
    # ROUND-5-GAP skip NOTICE (§7.1): one line per in-scope disabled facebook row,
    # in (slug, channel) order (``selected`` is already sorted). Emitted to stderr
    # AFTER the plan write; the row itself is listed with steps:[] in the plan.
    if not enable_facebook:
        for r in selected:
            if r["channel"] == "facebook":
                stderr.append(_fb_skip_notice(r["slug"]))
    return 0, stdout, stderr


def main(argv=None):
    """CLI entry point. Builds the argparse surface, maps args 1:1 to run(...),
    prints buffered output, returns the exit code. NEVER injects a transport."""
    parser = argparse.ArgumentParser(
        prog="publish_api.py",
        description=(
            "Direct-publishing CLI for the TERREM marketing-loop system. "
            "DRY-RUN IS THE DEFAULT (no credentials needed): it emits, per "
            "queued row, the ordered HTTP request plan each channel adapter "
            "would make, to stdout and content/publish-plan.json, with zero "
            "network and zero queue change. --live actually posts and is gated "
            "on THREE preconditions: (a) an env file with the platform tokens "
            "for the channels in scope, (b) PUBLIC_ASSET_BASE_URL, and (c) the "
            "explicit --i-have-verified-dry-run acknowledgment (plus --date). "
            "Exit codes: 0 success, 1 domain refusal, 2 usage/precondition."),
    )
    parser.add_argument(
        "--week", required=True,
        help="run scope: ISO week 'YYYY-Www' (e.g. 2026-W28). REQUIRED. [F]")
    parser.add_argument(
        "--slug", default=None, help="narrow scope to one content slug. [F]")
    parser.add_argument(
        "--channel", default=None,
        help="narrow scope to one channel (must be a valid queue channel). [F]")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="preview mode (DEFAULT when neither --dry-run nor --live is "
             "passed): emit the request plan, no network, no queue change. [F]")
    parser.add_argument(
        "--live", action="store_true",
        help="actually post — gated on (a) env tokens, (b) "
             "PUBLIC_ASSET_BASE_URL, (c) --i-have-verified-dry-run, plus "
             "--date. Posts each queued row and transitions it queued->posted "
             "with the returned permalink (per-day cap enforced). [F]")
    parser.add_argument(
        "--queue", default=_DEFAULT_QUEUE,
        help="publish-queue JSON path (default: {}). [F]".format(_DEFAULT_QUEUE))
    parser.add_argument(
        "--date", default=None,
        help="posted-date 'YYYY-MM-DD' (a real calendar date; never the wall "
             "clock). Required in --live; validated when given. Written verbatim "
             "as the row's posted_date and keys the per-day cap. [P]")
    parser.add_argument(
        "--max-per-day", type=int, default=3,
        help="per-day post cap across channels (default 3; must be an integer "
             ">= 1). The breaching row is refused (exit 1). [P]")
    parser.add_argument(
        "--enable-facebook", action="store_true",
        help="opt into the (round-5-gap, unverified) Facebook adapter in live: "
             "post facebook rows via the guessed flow. OFF by default (skip). [P]")
    parser.add_argument(
        "--linkedin-post-type", choices=("document", "multi-image"),
        default="document",
        help="LinkedIn flow selector (default: document): 'document' posts the "
             "render/manifest.json PDF; 'multi-image' posts the package "
             "attachments. Exactly one flow per row (R4-B4). [F]")
    parser.add_argument(
        "--linkedin-version", default=LINKEDIN_VERSION_DEFAULT,
        help="LinkedIn versioned-API monthly header 'YYYYMM' (default: {}); a "
             "FIXED constant, never wall-clock-derived. [F]".format(
                 LINKEDIN_VERSION_DEFAULT))
    parser.add_argument(
        "--public-asset-base-url", default=None,
        help="public base URL serving the PNGs; used by the image_url helper "
             "and satisfies live gate (b). Optional in dry-run. [F]")
    parser.add_argument(
        "--env", default=_DEFAULT_ENV,
        help="env file holding platform tokens (default: {}); consumed by the "
             "loader + live gate. [F]".format(_DEFAULT_ENV))
    parser.add_argument(
        "--i-have-verified-dry-run", action="store_true",
        help="explicit acknowledgment required by --live (gate (c)). [F]")

    args = parser.parse_args(argv)

    # Both --dry-run and --live is a usage error (contract s3.1).
    if args.dry_run and args.live:
        sys.stderr.write(
            "ERROR: --dry-run and --live are mutually exclusive; pass at most "
            "one (dry-run is the default)\n")
        return 2
    mode = "live" if args.live else "dry-run"

    code, stdout_lines, stderr_lines = run(
        week=args.week,
        slug=args.slug,
        channel=args.channel,
        mode=mode,
        queue_path=args.queue,
        date=args.date,
        max_per_day=args.max_per_day,
        enable_facebook=args.enable_facebook,
        linkedin_post_type=args.linkedin_post_type,
        linkedin_version=args.linkedin_version,
        public_asset_base_url=args.public_asset_base_url,
        env_path=args.env,
        i_have_verified_dry_run=args.i_have_verified_dry_run,
    )
    for line in stdout_lines:
        sys.stdout.write(line + "\n")
    for line in stderr_lines:
        sys.stderr.write(line + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
