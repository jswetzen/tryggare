"""Deterministic personal-data patterns, shared by the assistant's spec checks and the
feature-request text checks. A backstop only: human review is the real control."""

import re
import unicodedata

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_PERSONNUMMER = re.compile(r"(?<!\d)(\d{6}|\d{8})[-+]?\d{4}(?!\d)")
_PHONE = re.compile(r"(?<![\w.])\+?\d[\d ()./-]{7,}\d(?![\w.])")
_URL = re.compile(r"\b[a-z][a-z0-9+.-]*://\S+", re.IGNORECASE)
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍‎‏⁠­﻿"), None)
_AT = re.compile(r"\s*@\s*")
_ISO = r"\d{4}-\d{2}-\d{2}([T ][\d:.]+(Z|[+-]\d{2}:\d{2})?)?"
_ISO_VALUE = re.compile(rf"{_ISO}(\s*[-/–]\s*{_ISO})?")
# Digits by design; a key is still checked for a personnummer below.
_FREE_KEYS = {"accent_color"}

# Only for free text (feature requests), where a date or an id is never a shape.
# Any year-first or year-last date with -, / or . separators, not only strict ISO.
_DATE_ANYWHERE = re.compile(
    r"(?<!\d)(\d{4}\s*([-/.])\s*\d{1,2}\s*\2\s*\d{1,2}|\d{1,2}\s*([-/.])\s*\d{1,2}\s*\3\s*\d{4})(?!\d)"
)
_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)
# Registration reference codes (registrations/tokens.py): 8 characters from this
# alphabet, looked up case-insensitively. Needs a digit too, so ordinary words do not match.
_REFERENCE_CODE = re.compile(r"\b(?=[A-Z2-9]*\d)[2-9A-HJ-NP-Z]{8}\b", re.IGNORECASE)


def _normalize_text(text: str, keep_urls: bool = False) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_ZERO_WIDTH)
    return _AT.sub("@", text if keep_urls else _URL.sub(" ", text))


def _pii_kind(text: str, is_key: bool = False, keep_urls: bool = False) -> str | None:
    text = _normalize_text(text, keep_urls)
    if is_key:
        text = text.replace("-", "")
        return "a personnummer-like number" if _PERSONNUMMER.search(text) else None
    if _ISO_VALUE.fullmatch(text.strip()):
        return None
    if _EMAIL.search(text):
        return "an email address"
    if _PERSONNUMMER.search(text):
        return "a personnummer-like number"
    for match in _PHONE.finditer(text):
        if sum(c.isdigit() for c in match.group()) >= 9:
            return "a phone number"
    return None


def free_text_kind(text: str) -> str | None:
    """What personal-data shape ``text`` contains, or None. Stricter than ``_pii_kind``:
    any date, UUID or registration-reference-like token is refused too, and a URL is
    checked rather than skipped (a spec may hold URLs; free text has no reason to)."""
    text = unicodedata.normalize("NFKC", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")  # invisible
    if _DATE_ANYWHERE.search(text):
        return "a date"
    if _UUID.search(text):
        return "a UUID"
    if _REFERENCE_CODE.search(text):
        return "a registration-reference-like code"
    return _pii_kind(text, keep_urls=True)


def strings_in(value) -> set[str]:
    if isinstance(value, str):
        return {value}
    items = value.values() if isinstance(value, dict) else value
    if isinstance(value, dict | list):
        return set().union(*(strings_in(v) for v in items)) if items else set()
    return set()


def find_personal_data(
    value, known=frozenset(), path: str = "", key: str = ""
) -> list[dict]:
    """``{"path", "found"}`` for each string that looks like personal data and is not
    in ``known`` (the event's current export: text the model did not introduce)."""
    found = []
    if isinstance(value, str):
        if value not in known and key not in _FREE_KEYS:
            kind = _pii_kind(value, is_key=key == "key")
            if kind:
                found.append({"path": path, "found": kind})
    elif isinstance(value, dict):
        for k, v in value.items():
            sub = f"{path}.{k}" if path else str(k)
            found += find_personal_data(v, known, sub, str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            found += find_personal_data(v, known, f"{path}[{i}]", key)
    return found
