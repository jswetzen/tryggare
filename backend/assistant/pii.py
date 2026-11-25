"""Deterministic personal-data patterns, shared by the assistant's spec checks and the
feature-request text checks. A backstop only: human review is the real control."""

import re
import unicodedata
from datetime import date

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


# --- the chat detector: what the organizer typed, for the agent's one-turn hint

PERSONNUMMER = "a personnummer"
EMAIL = "an email address"
PHONE = "a phone number"
BIRTH_DATE = "a birth date"

_ID_NUMBER = re.compile(r"(?<!\d)(\d{6}|\d{8})[-+ ]?(\d{4})(?!\d)")
# Swedish shapes only; "/" and "." are not separators, so price lists and dates do not join.
_SE_PHONE = re.compile(r"(?<![\w+])(?:\+46|0046|0)[\d ()-]{6,}\d(?!\w)")
_NOT_A_PHONE_AFTER = re.compile(r"\s*(?:kr\b|sek\b|%|/)", re.I)
# Dates and clock times, which a brief is full of: "2027-06-20 10:00" otherwise reads
# as a phone number. ";" is outside the phone pattern, so neighbours do not join.
_DATE_OR_TIME = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:[T ]\d{1,2}[:.]\d{2})?|\b\d{1,2}:\d{2}\b"
)
_MONTHS = (
    r"jan(?:uari|uary)?|feb(?:ruari|ruary)?|mar(?:s|ch)?|apr(?:il)?|maj|may"
    r"|jun[ei]?|jul[iy]?|aug(?:usti|ust)?|sep(?:tember)?|o[kc]t(?:ober)?"
    r"|nov(?:ember)?|dec(?:ember)?"
)
_DATE_TEXT = (
    r"\d{4}-\d{1,2}-\d{1,2}|\d{8}|\d{6}|\d{1,2}[./]\d{1,2}[./]\d{2,4}"
    rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})\.?\s+\d{{4}}"
    rf"|(?:{_MONTHS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}"
)
# "född" but not "födda": "barn födda 2015 eller senare" is a rule, not a person.
_BIRTH = re.compile(
    rf"(?<!\w)(?:född|born|f\.)\s*(?:den\s+|on\s+|the\s+)?(?:{_DATE_TEXT})(?!\d)",
    re.I,
)


def _is_date(year: int, month: int, day: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(digits):
        n = int(ch) * (2 if i % 2 == 0 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def valid_personnummer(digits: str) -> bool:
    """A real date (day + 60 for a samordningsnummer) and the Luhn check. An orgnr has
    month 20 or more, so it fails here."""
    if len(digits) == 12:
        if digits[:2] not in ("18", "19", "20"):
            return False
        years, digits = [int(digits[:4])], digits[2:]
    elif len(digits) == 10:
        years = [1900 + int(digits[:2]), 2000 + int(digits[:2])]
    else:
        return False
    month, day = int(digits[2:4]), int(digits[4:6])
    if day > 60:
        day -= 60
    return any(_is_date(y, month, day) for y in years) and _luhn(digits)


def _phone_like(match: re.Match, text: str) -> bool:
    if sum(c.isdigit() for c in match.group()) < 9:
        return False
    before = text[: match.start()].rstrip()
    return not before.endswith("/") and not _NOT_A_PHONE_AFTER.match(text, match.end())


def message_findings(text: str, known=frozenset()) -> list[str]:
    """Every personal-data kind in what the organizer typed, in a fixed order. A match
    that appears in ``known`` (the event's current export) is not theirs, so it is
    dropped. Names and health words are left to the model."""
    text = _normalize_text(text)

    def new(m: re.Match) -> bool:
        return not any(m.group() in k for k in known)

    without_dates = _DATE_OR_TIME.sub(lambda m: " ; ".ljust(len(m.group())), text)
    checks = (
        (
            PERSONNUMMER,
            (
                m
                for m in _ID_NUMBER.finditer(text)
                if valid_personnummer(m.group(1) + m.group(2))
            ),
        ),
        (EMAIL, _EMAIL.finditer(text)),
        (
            PHONE,
            (
                m
                for m in _SE_PHONE.finditer(without_dates)
                if _phone_like(m, without_dates)
            ),
        ),
        (BIRTH_DATE, _BIRTH.finditer(text)),
    )
    return [kind for kind, matches in checks if any(new(m) for m in matches)]


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
