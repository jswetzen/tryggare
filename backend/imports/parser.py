"""
Pure parsing logic for external booking system JSON exports.
No database access — all functions operate on plain Python dicts.
"""

from __future__ import annotations

import json
from datetime import date


class _DuplicateList(list):
    """
    Sentinel subclass of list to distinguish "this key appeared multiple
    times in the JSON" from a genuine JSON array value.

    When the external booking JSON has the same key (e.g. "Ålder") more than
    once, parse_json_with_duplicate_keys() collects all occurrences into one
    of these.  parse_children_from_prefix() then pops index 0 when it
    consumes a duplicate-key value so the next prefix call gets the next one.
    """


def parse_json_with_duplicate_keys(json_str: str) -> dict:
    """
    Parse a JSON string while preserving duplicate keys.

    Standard json.loads() silently drops all but the last value for duplicate
    keys.  The external booking export uses the same standalone "Ålder" key
    once per child-prefix group, so we need all occurrences.

    Returns a regular dict where any key that appeared more than once has its
    value replaced by a _DuplicateList containing all values in order.
    """

    def _pairs_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                existing = result[key]
                if isinstance(existing, _DuplicateList):
                    existing.append(value)
                else:
                    result[key] = _DuplicateList([existing, value])
            else:
                result[key] = value
        return result

    return json.loads(json_str, object_pairs_hook=_pairs_hook)


def _parse_date(date_str: str) -> date | None:
    """Parse DD/MM/YYYY date string to Python date. Returns None if unparseable."""
    if not date_str or not date_str.strip():
        return None
    try:
        parts = date_str.strip().split("/")
        if len(parts) != 3:
            return None
        day, month, year = parts
        return date(int(year), int(month), int(day))
    except (ValueError, TypeError):
        return None


def _get_alder_key(booking: dict, prefix: str) -> str | None:
    """
    Find the Ålder key for a given prefix — prefixed variants only.

    Returns the explicit prefixed key if present, otherwise None.
    Standalone "Ålder" / "Ålder " keys are handled by build_alder_map().
    """
    stripped = prefix.rstrip()
    for candidate in (
        f"{prefix} Ålder",
        f"{prefix} Ålder ",
        f"{stripped} Ålder",
        f"{stripped} Ålder ",
    ):
        if candidate in booking:
            return candidate
    return None


def build_alder_map(booking: dict, prefixes: list[str]) -> dict[str, str | None]:
    """
    Pre-assign an Ålder value to each prefix by processing prefixes in
    document order (the order their First Name keys appear in the booking).

    The external booking system places a standalone "Ålder" (or "Ålder ")
    key immediately after each child-prefix block.  Because the same key
    name repeats, parse_json_with_duplicate_keys() collects all occurrences
    into a _DuplicateList at a single dict position, in document order.

    Strategy:
    1. Sort prefixes by the position of their First Name key in the booking
       (document order), so we consume values in the same order the source
       file was written.
    2. For each prefix with an explicit prefixed Ålder key, use it directly.
    3. For each prefix using a standalone key, consume the next unconsumed
       value from the appropriate _DuplicateList (or plain string).

    Returns {prefix: alder_value_string_or_None}.
    """
    result: dict[str, str | None] = {}
    keys = list(booking.keys())

    # Sort prefixes by document position of their " First Name" key.
    def _prefix_pos(prefix: str) -> int:
        try:
            return keys.index(f"{prefix} First Name")
        except ValueError:
            return len(keys)  # Put unknowns at the end

    ordered_prefixes = sorted(prefixes, key=_prefix_pos)

    # Cursors into the _DuplicateList (or plain string) for each standalone key.
    # Key: exact dict key string (e.g. "Ålder" or "Ålder "). Value: next index to consume.
    cursors: dict[str, int] = {}

    for prefix in ordered_prefixes:
        # 1. Prefixed Ålder key — unambiguous, use directly.
        explicit_key = _get_alder_key(booking, prefix)
        if explicit_key:
            val = booking[explicit_key]
            if isinstance(val, _DuplicateList):
                result[prefix] = val[0] if val else None
            else:
                result[prefix] = val
            continue

        # 2. Standalone key — find the nearest Ålder key *at or after* this
        #    prefix's First Name position that still has unconsumed values.
        #    Because all occurrences of "Ålder" collapse into one _DuplicateList
        #    at the first occurrence's position, we must check ALL Ålder keys
        #    (not just those after our start) for remaining capacity.
        first_name_key = f"{prefix} First Name"
        try:
            start = keys.index(first_name_key)
        except ValueError:
            result[prefix] = None
            continue

        # First pass: look forward from start (preferred — closest match).
        assigned = _try_consume_alder(booking, keys, start, cursors, result, prefix)

        # Second pass: if nothing found forward, scan all Ålder keys for any
        # remaining unconsumed values (handles cases where all Ålder occurrences
        # were merged into a _DuplicateList earlier in the dict than this prefix).
        if not assigned:
            assigned = _try_consume_alder(booking, keys, 0, cursors, result, prefix)

        if not assigned:
            result[prefix] = None

    return result


def _try_consume_alder(
    booking: dict,
    keys: list,
    start: int,
    cursors: dict,
    result: dict,
    prefix: str,
) -> bool:
    """
    Scan keys[start:] for a standalone Ålder key with remaining capacity.
    Consumes one value and writes to result[prefix]. Returns True if assigned.
    """
    for key in keys[start:]:
        if key.strip() != "Ålder":
            continue
        val = booking[key]
        if isinstance(val, _DuplicateList):
            cursor = cursors.get(key, 0)
            if cursor < len(val):
                result[prefix] = val[cursor]
                cursors[key] = cursor + 1
                return True
        else:
            cursor = cursors.get(key, 0)
            if cursor == 0:
                result[prefix] = val
                cursors[key] = 1
                return True
    return False


def _booking_has_any_alder(booking: dict) -> bool:
    """Return True if the booking contains any form of the Ålder key."""
    return any(k.strip() == "Ålder" for k in booking.keys())


def _is_child_prefix(booking: dict, prefix: str) -> bool:
    """
    A prefix is a child prefix if it has First Name + Last Name and the
    booking contains at least one Ålder key (prefixed or standalone),
    but does NOT have an "{prefix} Email" field (which indicates an adult).
    """
    has_first = f"{prefix} First Name" in booking
    has_last = f"{prefix} Last Name" in booking
    has_email = f"{prefix} Email" in booking

    if not has_first or not has_last or has_email:
        return False

    # Accept if there's any Ålder key in the booking (prefixed or standalone)
    return _get_alder_key(booking, prefix) is not None or _booking_has_any_alder(
        booking
    )


def discover_child_prefixes(data: dict) -> list[dict]:
    """
    Scan all bookings in the JSON and find child ticket prefixes.

    A prefix is "child" if it has:
    - "{prefix} First Name" AND "{prefix} Last Name" in some booking
    - EITHER "{prefix} Ålder" or "{prefix} Ålder " (trailing space variant)
    - Does NOT have "{prefix} Email" (which indicates an adult attendee)

    Returns list of {prefix, sample_children, booking_count} sorted by
    booking_count descending.
    """
    prefix_stats: dict[str, dict] = {}  # prefix -> {count, sample_children}

    for booking_key, booking in data.items():
        if not isinstance(booking, dict):
            continue

        # Collect all keys that end in " First Name"
        for key in list(booking.keys()):
            if not isinstance(key, str) or not key.endswith(" First Name"):
                continue
            prefix = key[: -len(" First Name")]
            if not prefix:
                continue

            if not _is_child_prefix(booking, prefix):
                continue

            # Get first name value(s) for sample
            first_name_val = booking.get(f"{prefix} First Name")
            names = []
            if isinstance(first_name_val, list):
                names = [n for n in first_name_val if n and str(n).strip()]
            elif first_name_val and str(first_name_val).strip():
                names = [str(first_name_val).strip()]

            if not names:
                continue  # Skip empty/blank name buckets

            if prefix not in prefix_stats:
                prefix_stats[prefix] = {"count": 0, "sample_children": []}

            prefix_stats[prefix]["count"] += 1
            # Collect up to 3 sample names
            for name in names:
                if len(prefix_stats[prefix]["sample_children"]) < 3:
                    if name not in prefix_stats[prefix]["sample_children"]:
                        prefix_stats[prefix]["sample_children"].append(name)

    result = [
        {
            "prefix": prefix,
            "sample_children": stats["sample_children"],
            "booking_count": stats["count"],
        }
        for prefix, stats in prefix_stats.items()
    ]
    result.sort(key=lambda x: x["booking_count"], reverse=True)
    return result


def parse_children_from_prefix(
    booking: dict, prefix: str, alder_value: str | None = None
) -> list[dict]:
    """
    Extract children from a single prefix bucket in a booking.

    Handles:
    - Single child: First Name is a string, Ålder is a single DD/MM/YYYY date
    - Multiple children: First Name is a list, Ålder is pipe-separated dates
    - Trailing space in "Ålder " key
    - Empty names → skip that child

    alder_value: pre-resolved birthdate string from build_alder_map().
    If not provided, falls back to _get_alder_key() for backward compatibility
    (works correctly when each prefix has its own prefixed Ålder key).

    Returns list of:
    {
        "first_name": str,
        "last_name": str,
        "birthdate": date | None,
        "allergies": str | None,
        "eticket_code": str | None,
    }
    """
    first_name_val = booking.get(f"{prefix} First Name")
    last_name_val = booking.get(f"{prefix} Last Name")

    if first_name_val is None:
        return []

    # Normalize to lists
    if isinstance(first_name_val, list):
        first_names = first_name_val
    else:
        first_names = [first_name_val]

    if isinstance(last_name_val, list):
        last_names = last_name_val
    else:
        last_names = [last_name_val] * len(first_names)

    # Use pre-resolved alder value if provided; otherwise fall back to direct lookup.
    if alder_value is not None:
        alder_val: str | None = alder_value
    else:
        alder_key = _get_alder_key(booking, prefix)
        raw_alder = booking.get(alder_key) if alder_key else None
        if isinstance(raw_alder, _DuplicateList):
            alder_val = raw_alder[0] if raw_alder else None
        else:
            alder_val = raw_alder

    if alder_val and "|" in str(alder_val):
        birthdates_raw = [s.strip() for s in str(alder_val).split("|")]
    elif alder_val:
        birthdates_raw = [str(alder_val).strip()]
    else:
        birthdates_raw = []

    # Pad birthdates list if shorter than names list
    while len(birthdates_raw) < len(first_names):
        birthdates_raw.append("")

    # ETicket code — key is "ETicket {prefix}" (may have trailing space)
    eticket_code = (
        booking.get(f"ETicket {prefix}")
        or booking.get(f"ETicket {prefix.rstrip()} ")
        or None
    )
    if eticket_code:
        eticket_code = str(eticket_code).strip() or None

    # Allergies — use booking-level key (Python dicts deduplicate, so last "Allergier" wins)
    allergies = booking.get(f"{prefix} Allergier") or booking.get("Allergier") or None
    if allergies:
        allergies = str(allergies).strip() or None

    children = []
    for i, first_name in enumerate(first_names):
        fn = str(first_name).strip() if first_name else ""
        if not fn:
            continue

        ln = str(last_names[i]).strip() if i < len(last_names) and last_names[i] else ""
        bd_raw = birthdates_raw[i] if i < len(birthdates_raw) else ""
        birthdate = _parse_date(bd_raw)

        children.append(
            {
                "first_name": fn,
                "last_name": ln,
                "birthdate": birthdate,
                "allergies": allergies,
                "eticket_code": eticket_code,
            }
        )

    return children


def parse_contact(booking: dict) -> dict:
    """Extract primary contact (parent) info from a booking."""
    return {
        "first_name": str(booking.get("Contact First Name", "") or "").strip(),
        "last_name": str(booking.get("Contact Last Name", "") or "").strip(),
        "email": str(booking.get("Contact Email", "") or "").strip() or None,
        "phone": str(booking.get("Cell/Mobile", "") or "").strip() or None,
    }


def _first_nonempty(val) -> str:
    """Return the first non-empty string from a value that may be a list or plain string."""
    if isinstance(val, list):
        for item in val:
            s = str(item).strip()
            if s:
                return s
        return ""
    return str(val or "").strip()


def parse_extra_guardian(booking: dict) -> dict | None:
    """
    Extract extra guardian info if present.
    Fields start with "Extra vårdnadshavare kontaktinformation".
    Returns None if all relevant fields are empty.
    """
    prefix = "Extra vårdnadshavare kontaktinformation"
    first = _first_nonempty(booking.get(f"{prefix} First Name", ""))
    last = _first_nonempty(booking.get(f"{prefix} Last Name", ""))
    email = _first_nonempty(booking.get(f"{prefix} Email", "")) or None
    phone = _first_nonempty(booking.get(f"{prefix} Phone", "")) or None

    if not first and not last and not email and not phone:
        return None

    return {
        "first_name": first,
        "last_name": last,
        "email": email,
        "phone": phone,
    }


def parse_booking(booking: dict, prefix_mappings: dict) -> dict:
    """
    Parse a complete booking using saved prefix_mappings.

    prefix_mappings: {prefix: "full_event" | "<session_uuid>" | "ignore"}

    Returns:
    {
        "booking_id": str,
        "contact": {...},
        "extra_guardian": {...} | None,
        "children": [
            {
                "first_name": str,
                "last_name": str,
                "birthdate": date | None,
                "allergies": str | None,
                "eticket_code": str | None,
                "mapping": "full_event" | "<session_uuid>",
            }
        ]
    }
    """
    booking_id = str(booking.get("Booking ID", "") or "").strip()
    contact = parse_contact(booking)
    extra_guardian = parse_extra_guardian(booking)

    # Pre-assign Ålder values in document order so that standalone duplicate
    # keys ("Ålder" appearing once per prefix group) are consumed correctly
    # regardless of the order prefix_mappings is iterated.
    active_prefixes = [p for p, m in prefix_mappings.items() if m != "ignore"]
    alder_map = build_alder_map(booking, active_prefixes)

    children = []
    for prefix, mapping in prefix_mappings.items():
        if mapping == "ignore":
            continue
        for child in parse_children_from_prefix(
            booking, prefix, alder_value=alder_map.get(prefix)
        ):
            child["mapping"] = mapping
            children.append(child)

    return {
        "booking_id": booking_id,
        "contact": contact,
        "extra_guardian": extra_guardian,
        "children": children,
    }
