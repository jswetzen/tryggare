"""
Unit tests for imports/parser.py — pure parsing logic with no DB access.
"""

from datetime import date

import pytest

from imports.parser import (
    discover_child_prefixes,
    parse_booking,
    parse_children_from_prefix,
    parse_contact,
    parse_extra_guardian,
)

# ---------------------------------------------------------------------------
# Realistic sample booking (based on the actual export format)
# ---------------------------------------------------------------------------

SAMPLE_BOOKING = {
    "Booking ID": "10869",
    "Invoice ID": "5867",
    "Contact ID": "20733",
    "Contact First Name": "Jtest",
    "Contact Last Name": "Enamn",
    "Contact Email": "mail@exempel.se",
    "Cell/Mobile": "070730403030",
    # Adult ticket prefix — has Email, so should NOT be detected as child
    "SK26 Helkonferens - ink fika First Name": "Jtest",
    "SK26 Helkonferens - ink fika Last Name": "Enamn",
    "SK26 Helkonferens - ink fika Email": "mail@test.se",
    "SK26 Helkonferens - ink fika Phone": " 0707070",
    "ETicket SK26 Helkonferens - ink fika": "ZOPBWIEWQE",
    # Extra guardian
    "Extra vårdnadshavare kontaktinformation First Name": "Extra",
    "Extra vårdnadshavare kontaktinformation Last Name": "Kontakt",
    "Extra vårdnadshavare kontaktinformation Email": "kanske@mormor.tex",
    "Extra vårdnadshavare kontaktinformation Phone": " 0707007000",
    # Child prefix: single child with PREFIXED Ålder (so it doesn't collide)
    "SK26 Barnkonferens First Name": "Barn1",
    "SK26 Barnkonferens Last Name": "Enamn",
    "ETicket SK26 Barnkonferens": "ICCEQUGOWB",
    "SK26 Barnkonferens Ålder": "04/02/2020",
    "SK26 Barnkonferens Allergier": "",
    # Child prefix: multiple children (array) with PREFIXED Ålder
    "Dagsbiljett barn (torsdag 26 juni) First Name": ["Barn2", "Barn22"],
    "Dagsbiljett barn (torsdag 26 juni) Last Name": ["Enamn", "Enamn"],
    "ETicket Dagsbiljett barn (torsdag 26 juni)": "EDMKIOBKJX",
    "Dagsbiljett barn (torsdag 26 juni) Ålder": "15/01/2019|07/03/2014",
    "Dagsbiljett barn (torsdag 26 juni) Allergier": "Inget",
    # Child prefix: single child for friday with PREFIXED Ålder
    "Dagsbiljett barn (fredag 27 juni) First Name": "Barn3",
    "Dagsbiljett barn (fredag 27 juni) Last Name": "Enman",
    "ETicket Dagsbiljett barn (fredag 27 juni)": "UIWRMAAOTB",
    "Dagsbiljett barn (fredag 27 juni) Ålder": "21/02/2017",
    "Dagsbiljett barn (fredag 27 juni) Allergier": "",
}

# Full data dict with one booking
SAMPLE_DATA = {"contact13": SAMPLE_BOOKING}


# ---------------------------------------------------------------------------
# discover_child_prefixes
# ---------------------------------------------------------------------------


class TestDiscoverChildPrefixes:
    def test_finds_single_child_prefix(self):
        # SK26 Barnkonferens (with trailing space) has First Name + Last Name + Ålder, no Email
        prefixes = discover_child_prefixes(SAMPLE_DATA)
        prefix_names = [p["prefix"] for p in prefixes]
        assert any("SK26 Barnkonferens" in p for p in prefix_names)

    def test_finds_array_child_prefix(self):
        prefixes = discover_child_prefixes(SAMPLE_DATA)
        prefix_names = [p["prefix"] for p in prefixes]
        assert any("Dagsbiljett barn (torsdag 26 juni)" in p for p in prefix_names)

    def test_excludes_adult_prefix(self):
        # SK26 Helkonferens - ink fika has Email → adult, should be excluded
        prefixes = discover_child_prefixes(SAMPLE_DATA)
        prefix_names = [p["prefix"] for p in prefixes]
        assert not any("SK26 Helkonferens - ink fika" in p for p in prefix_names)

    def test_excludes_extra_guardian_prefix(self):
        prefixes = discover_child_prefixes(SAMPLE_DATA)
        prefix_names = [p["prefix"] for p in prefixes]
        assert not any("Extra vårdnadshavare" in p for p in prefix_names)

    def test_returns_sample_children(self):
        prefixes = discover_child_prefixes(SAMPLE_DATA)
        # Find the thursday day-pass prefix
        thursday = next(
            (p for p in prefixes if "torsdag 26 juni" in p["prefix"]), None
        )
        assert thursday is not None
        assert "Barn2" in thursday["sample_children"] or "Barn22" in thursday["sample_children"]

    def test_booking_count(self):
        prefixes = discover_child_prefixes(SAMPLE_DATA)
        for p in prefixes:
            assert p["booking_count"] >= 1

    def test_skips_non_dict_entries(self):
        data = {"meta": "some string", "contact1": SAMPLE_BOOKING}
        prefixes = discover_child_prefixes(data)
        assert len(prefixes) > 0  # Should not crash


# ---------------------------------------------------------------------------
# parse_children_from_prefix
# ---------------------------------------------------------------------------


class TestParseChildrenFromPrefix:
    def test_single_child(self):
        prefix = "SK26 Barnkonferens"
        children = parse_children_from_prefix(SAMPLE_BOOKING, prefix)
        assert len(children) == 1
        child = children[0]
        assert child["first_name"] == "Barn1"
        assert child["last_name"] == "Enamn"
        assert child["eticket_code"] == "ICCEQUGOWB"

    def test_multiple_children_array(self):
        prefix = "Dagsbiljett barn (torsdag 26 juni)"
        children = parse_children_from_prefix(SAMPLE_BOOKING, prefix)
        assert len(children) == 2
        assert children[0]["first_name"] == "Barn2"
        assert children[1]["first_name"] == "Barn22"
        # Both share the same eticket code
        assert children[0]["eticket_code"] == "EDMKIOBKJX"
        assert children[1]["eticket_code"] == "EDMKIOBKJX"

    def test_pipe_separated_birthdates(self):
        prefix = "Dagsbiljett barn (torsdag 26 juni)"
        children = parse_children_from_prefix(SAMPLE_BOOKING, prefix)
        assert children[0]["birthdate"] == date(2019, 1, 15)
        assert children[1]["birthdate"] == date(2014, 3, 7)

    def test_single_birthdate(self):
        # For friday: Ålder is "21/02/2017" (single date)
        prefix = "Dagsbiljett barn (fredag 27 juni)"
        children = parse_children_from_prefix(SAMPLE_BOOKING, prefix)
        assert len(children) == 1
        assert children[0]["birthdate"] == date(2017, 2, 21)

    def test_skips_empty_first_name(self):
        booking = {
            "Test Prefix First Name": "",
            "Test Prefix Last Name": "Enamn",
            "Test Prefix Ålder": "01/01/2020",
        }
        children = parse_children_from_prefix(booking, "Test Prefix")
        assert len(children) == 0

    def test_missing_prefix_returns_empty(self):
        children = parse_children_from_prefix(SAMPLE_BOOKING, "Nonexistent Prefix")
        assert children == []


# ---------------------------------------------------------------------------
# parse_contact
# ---------------------------------------------------------------------------


class TestParseContact:
    def test_basic_contact(self):
        contact = parse_contact(SAMPLE_BOOKING)
        assert contact["first_name"] == "Jtest"
        assert contact["last_name"] == "Enamn"
        assert contact["email"] == "mail@exempel.se"
        assert contact["phone"] == "070730403030"

    def test_empty_booking(self):
        contact = parse_contact({})
        assert contact["first_name"] == ""
        assert contact["last_name"] == ""
        assert contact["email"] is None
        assert contact["phone"] is None


# ---------------------------------------------------------------------------
# parse_extra_guardian
# ---------------------------------------------------------------------------


class TestParseExtraGuardian:
    def test_present_guardian(self):
        guardian = parse_extra_guardian(SAMPLE_BOOKING)
        assert guardian is not None
        assert guardian["first_name"] == "Extra"
        assert guardian["last_name"] == "Kontakt"
        assert guardian["email"] == "kanske@mormor.tex"
        assert guardian["phone"] == "0707007000"

    def test_absent_guardian(self):
        booking = {
            "Extra vårdnadshavare kontaktinformation First Name": "",
            "Extra vårdnadshavare kontaktinformation Last Name": "",
            "Extra vårdnadshavare kontaktinformation Email": "",
            "Extra vårdnadshavare kontaktinformation Phone": "",
        }
        guardian = parse_extra_guardian(booking)
        assert guardian is None

    def test_no_guardian_fields(self):
        guardian = parse_extra_guardian({})
        assert guardian is None


# ---------------------------------------------------------------------------
# parse_booking
# ---------------------------------------------------------------------------


class TestParseBooking:
    def test_full_parse(self):
        prefix_mappings = {
            "SK26 Barnkonferens": "full_event",
            "Dagsbiljett barn (torsdag 26 juni)": "full_event",
            "Dagsbiljett barn (fredag 27 juni)": "full_event",
        }
        result = parse_booking(SAMPLE_BOOKING, prefix_mappings)
        assert result["booking_id"] == "10869"
        assert result["contact"]["first_name"] == "Jtest"
        assert result["extra_guardian"] is not None
        # SK26 = 1, torsdag = 2, fredag = 1 → 4 children total
        assert len(result["children"]) == 4

    def test_ignore_mapping(self):
        prefix_mappings = {
            "SK26 Barnkonferens": "ignore",
            "Dagsbiljett barn (torsdag 26 juni)": "full_event",
        }
        result = parse_booking(SAMPLE_BOOKING, prefix_mappings)
        # Only torsdag children (2) should be included
        assert len(result["children"]) == 2

    def test_children_have_mapping(self):
        prefix_mappings = {
            "Dagsbiljett barn (torsdag 26 juni)": "full_event",
        }
        result = parse_booking(SAMPLE_BOOKING, prefix_mappings)
        for child in result["children"]:
            assert "mapping" in child
            assert child["mapping"] == "full_event"
