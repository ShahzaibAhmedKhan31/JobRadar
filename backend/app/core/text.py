"""Text normalization helpers used for search and dedupe."""

from __future__ import annotations

import html
import re
from collections.abc import Iterable

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_BULLET_RE = re.compile(r"<li[^>]*>", re.IGNORECASE)
_BREAK_RE = re.compile(r"<br\s*/?>|</p>|</div>|</h[1-6]>", re.IGNORECASE)
_LIST_SPLIT_RE = re.compile(r"[,\n;|]+")


def strip_html(value: str) -> str:
    """Turn a (possibly) HTML description into readable plain text."""
    text = _BULLET_RE.sub("\n- ", value)
    text = _BREAK_RE.sub("\n", text)
    text = _HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    lines = [_WHITESPACE_RE.sub(" ", line).strip(" \t-") for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned.strip()


def clean_text(value: str | None, *, max_length: int | None = None) -> str | None:
    """Normalize whitespace and truncate to ``max_length`` characters."""
    if value is None:
        return None
    text = strip_html(value)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if not text:
        return None
    if max_length is not None and len(text) > max_length:
        text = text[: max_length - 1].rstrip() + "…"
    return text


def snippet(value: str | None, limit: int = 240) -> str | None:
    """Return a user-facing preview capped at ``limit`` characters."""
    text = clean_text(value)
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def normalize_key(value: str | None) -> str:
    """Lowercase, punctuation-free form used in fingerprints."""
    if not value:
        return ""
    text = value.casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def split_terms(values: Iterable[str] | None, *, max_terms: int = 10) -> list[str]:
    """Split user input like ``"backend, data  engineer"`` into clean terms."""
    if not values:
        return []
    seen: set[str] = set()
    terms: list[str] = []
    for raw in values:
        if not raw:
            continue
        for part in _LIST_SPLIT_RE.split(str(raw)):
            term = _WHITESPACE_RE.sub(" ", part).strip()[:100]
            if len(term) < 1:
                continue
            key = term.casefold()
            if key in seen:
                continue
            seen.add(key)
            terms.append(term)
            if len(terms) >= max_terms:
                return terms
    return terms
