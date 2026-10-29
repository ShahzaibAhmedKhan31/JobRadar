"""Job URL validation and canonicalization."""

from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.core.text import normalize_key

MAX_URL_LENGTH = 2000
DEFAULT_PORTS = {"http": 80, "https": 443}

#: Query parameters that only track the click, never identify the listing.
TRACKING_PARAM_PREFIXES = ("utm_", "trk", "tracking", "ref_", "refid", "src_", "src")
TRACKING_PARAMS = {
    "ref",
    "referrer",
    "source",
    "campaign",
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "originalsubdomain",
}


class InvalidJobUrlError(ValueError):
    """Raised when a URL is not a usable http(s) job link."""


def validate_job_url(raw: str | None) -> str:
    """Validate and normalize a job URL, returning a canonical string.

    Only absolute ``http``/``https`` URLs are accepted. Fragments, default
    ports, trailing slashes and click-tracking parameters are removed so the
    same listing does not produce multiple rows.

    Raises:
        InvalidJobUrlError: if the URL is empty, malformed or unsupported.
    """
    if raw is None:
        raise InvalidJobUrlError("Job URL is required")
    candidate = raw.strip()
    if not candidate:
        raise InvalidJobUrlError("Job URL is required")
    if len(candidate) > MAX_URL_LENGTH:
        raise InvalidJobUrlError("Job URL is too long")
    if any(char.isspace() for char in candidate):
        raise InvalidJobUrlError("Job URL must not contain whitespace")

    parts = urlsplit(candidate)
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        raise InvalidJobUrlError("Job URL must use http or https")
    if not parts.hostname:
        raise InvalidJobUrlError("Job URL must include a host")

    try:
        port = parts.port
    except ValueError as exc:  # invalid port like ":abc"
        raise InvalidJobUrlError("Job URL has an invalid port") from exc
    if parts.username or parts.password:
        raise InvalidJobUrlError("Job URL must not contain credentials")

    host = parts.hostname.lower()
    if host != "localhost" and "." not in host:
        raise InvalidJobUrlError("Job URL host looks invalid")
    netloc = host if port in (None, DEFAULT_PORTS[scheme]) else f"{host}:{port}"

    path = parts.path.rstrip("/") or "/"

    query_pairs = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in TRACKING_PARAMS:
            continue
        if lowered.startswith(TRACKING_PARAM_PREFIXES):
            continue
        query_pairs.append((key, value))
    query = urlencode(sorted(query_pairs), doseq=True)

    normalized = urlunsplit((scheme, netloc, path, query, ""))
    if len(normalized) > MAX_URL_LENGTH:
        raise InvalidJobUrlError("Job URL is too long")
    return normalized


def is_valid_job_url(raw: str | None) -> bool:
    try:
        validate_job_url(raw)
    except InvalidJobUrlError:
        return False
    return True


def job_fingerprint(*, job_url: str, title: str, company_name: str) -> str:
    """Fallback dedupe key for providers without a stable listing id.

    Combines the canonical URL with normalized title/company so two different
    roles with similar titles are not merged. Truncated SHA-256 keeps the index
    small while remaining collision-safe for personal-scale data.
    """
    material = "|".join(
        (
            job_url.strip().lower(),
            normalize_key(title),
            normalize_key(company_name),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:40]
