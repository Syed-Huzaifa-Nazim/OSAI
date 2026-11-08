"""Generic parsing helpers used by the Daraz scraper.

Nothing in here knows about Daraz specifically - site knowledge lives in
selectors.py. These are the primitives that make extraction defensive: every
helper returns a sensible default instead of raising, because a product page
that is missing one field should still produce a usable record.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any, Iterable, List, Optional

_WHITESPACE_RE = re.compile(r"\s+")
_TAG_RE = re.compile(r"<[^>]+>")
_NUMBER_RE = re.compile(r"-?[\d,]*\.?\d+")


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------
def clean_text(value: Any) -> str:
    """Collapse whitespace, unescape entities, strip tags."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = html.unescape(value)
    value = _TAG_RE.sub(" ", value)
    value = html.unescape(value)
    value = value.replace("\xa0", " ").replace("​", "")
    return _WHITESPACE_RE.sub(" ", value).strip()


def strip_html(raw_html: Any) -> str:
    """Turn an HTML fragment into readable plain text with list breaks kept."""
    if not raw_html:
        return ""
    if not isinstance(raw_html, str):
        raw_html = str(raw_html)
    text = re.sub(r"<\s*(br|/p|/div|/li|/tr|/h[1-6])\s*/?>", "\n", raw_html, flags=re.I)
    text = re.sub(r"<\s*li[^>]*>", "\n- ", text, flags=re.I)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    lines = [_WHITESPACE_RE.sub(" ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def truncate(text: str, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    seen: set = set()
    out: List[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------
def to_float(value: Any) -> Optional[float]:
    """Best-effort float from anything ('Rs. 1,299.00' -> 1299.0)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = _NUMBER_RE.search(str(value).replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def to_int(value: Any) -> Optional[int]:
    result = to_float(value)
    return int(result) if result is not None else None


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    return text in {"true", "yes", "1", "y", "available", "on"}


def percent(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if not numerator or not denominator:
        return None
    try:
        return round((numerator / denominator) * 100, 2)
    except ZeroDivisionError:
        return None


# ---------------------------------------------------------------------------
# Nested structures
# ---------------------------------------------------------------------------
def deep_get(data: Any, path: str, default: Any = None) -> Any:
    """Walk a dotted path. Numeric segments index into lists."""
    current = data
    for part in path.split("."):
        if current is None:
            return default
        if isinstance(current, dict):
            if part in current:
                current = current[part]
                continue
            return default
        if isinstance(current, list):
            if part.isdigit() and int(part) < len(current):
                current = current[int(part)]
                continue
            return default
        return default
    return current if current is not None else default


def first_path(data: Any, paths: Iterable[str], default: Any = None) -> Any:
    """Return the first non-empty value among candidate dotted paths."""
    for path in paths:
        value = deep_get(data, path)
        if value not in (None, "", [], {}):
            return value
    return default


def find_key_anywhere(data: Any, key: str, max_depth: int = 8) -> Optional[Any]:
    """Breadth-first hunt for a key anywhere in a nested structure."""
    queue: List[tuple] = [(data, 0)]
    while queue:
        node, depth = queue.pop(0)
        if depth > max_depth:
            continue
        if isinstance(node, dict):
            if key in node and node[key] not in (None, "", [], {}):
                return node[key]
            for value in node.values():
                if isinstance(value, (dict, list)):
                    queue.append((value, depth + 1))
        elif isinstance(node, list):
            for value in node[:60]:
                if isinstance(value, (dict, list)):
                    queue.append((value, depth + 1))
    return None


def collect_strings(node: Any, limit: int = 200, max_depth: int = 6) -> List[str]:
    """Flatten every string inside a nested structure (used for promo/spec blobs)."""
    out: List[str] = []

    def walk(value: Any, depth: int) -> None:
        if len(out) >= limit or depth > max_depth:
            return
        if isinstance(value, str):
            cleaned = clean_text(value)
            if cleaned:
                out.append(cleaned)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                walk(item, depth + 1)

    walk(node, 0)
    return out


# ---------------------------------------------------------------------------
# JSON embedded in HTML
# ---------------------------------------------------------------------------
def extract_json_object(source: str, start_index: int) -> Optional[Any]:
    """Read one balanced JSON object beginning at `start_index` ('{').

    Regex alone cannot do this because the blob contains nested braces and
    braces inside strings, so we scan with a depth counter that is string- and
    escape-aware.
    """
    if start_index < 0 or start_index >= len(source) or source[start_index] != "{":
        return None

    depth = 0
    in_string = False
    escaped = False

    for i in range(start_index, len(source)):
        char = source[i]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = source[start_index : i + 1]
                try:
                    return json.loads(candidate)
                except (json.JSONDecodeError, ValueError):
                    return None
    return None


def safe_json_loads(value: Any) -> Optional[Any]:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Keyword matching
# ---------------------------------------------------------------------------
def contains_any(haystack: str, keywords: Iterable[str]) -> bool:
    lowered = (haystack or "").lower()
    return any(keyword in lowered for keyword in keywords)


def matched_keywords(haystack: str, keywords: Iterable[str]) -> List[str]:
    lowered = (haystack or "").lower()
    return [keyword for keyword in keywords if keyword in lowered]


def count_keyword_hits(haystack: str, keywords: Iterable[str]) -> int:
    lowered = (haystack or "").lower()
    return sum(lowered.count(keyword) for keyword in keywords)
