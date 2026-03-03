"""
Pure parsing logic for external booking system JSON exports.
No database access — all functions operate on plain Python dicts.
"""

from __future__ import annotations

from datetime import date


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
    Find the Ålder key for a given prefix.

    The booking system uses both prefixed ("SK26 Barnkonferens Ålder") and
    standalone ("Ålder" / "Ålder ") Ålder keys depending on the bucket type.
    Check prefixed variants first, then fall back to standalone.
    """
    # Try prefixed variants first (explicit match)
    stripped = prefix.rstrip()
    for candidate in (
        f"{prefix} Ålder",
        f"{prefix} Ålder ",
        f"{stripped} Ålder",
        f"{stripped} Ålder ",
    ):
        if candidate in booking:
            return candidate

    # Fall back to standalone Ålder keys (used by some booking systems)
    for candidate in ("Ålder", "Ålder "):
        if candidate in booking:
            return candidate

    return None


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
    return _get_alder_key(booking, prefix) is not None or _booking_has_any_alder(booking)


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


def parse_children_from_prefix(booking: dict, prefix: str) -> list[dict]:
    """
    Extract children from a single prefix bucket in a booking.

    Handles:
    - Single child: First Name is a string, Ålder is a single DD/MM/YYYY date
    - Multiple children: First Name is a list, Ålder is pipe-separated dates
    - Trailing space in "Ålder " key
    - Empty names → skip that child

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

    # Get Ålder (age/birthdate) — may be pipe-separated for multiple children.
    # Standalone "Ålder"/"Ålder " keys are deduplicated by Python dict parsing;
    # we get whatever value the last occurrence had. This is a known limitation
    # of the source format and is accepted per PRD.
    alder_key = _get_alder_key(booking, prefix)
    alder_val = booking.get(alder_key) if alder_key else None

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
    eticket_code = booking.get(f"ETicket {prefix}") or booking.get(f"ETicket {prefix.rstrip()} ") or None
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


def parse_extra_guardian(booking: dict) -> dict | None:
    """
    Extract extra guardian info if present.
    Fields start with "Extra vårdnadshavare kontaktinformation".
    Returns None if all relevant fields are empty.
    """
    prefix = "Extra vårdnadshavare kontaktinformation"
    first = str(booking.get(f"{prefix} First Name", "") or "").strip()
    last = str(booking.get(f"{prefix} Last Name", "") or "").strip()
    email = str(booking.get(f"{prefix} Email", "") or "").strip() or None
    phone = str(booking.get(f"{prefix} Phone", "") or "").strip() or None

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

    children = []
    for prefix, mapping in prefix_mappings.items():
        if mapping == "ignore":
            continue
        for child in parse_children_from_prefix(booking, prefix):
            child["mapping"] = mapping
            children.append(child)

    return {
        "booking_id": booking_id,
        "contact": contact,
        "extra_guardian": extra_guardian,
        "children": children,
    }
