"""
Unit tests for imports/parser.py — pure parsing logic with no DB access.
"""

from datetime import date


from imports.parser import (
    _DuplicateList,
    build_alder_map,
    discover_child_prefixes,
    parse_booking,
    parse_children_from_prefix,
    parse_contact,
    parse_extra_guardian,
    parse_json_with_duplicate_keys,
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
# Realistic booking matching the ACTUAL export format from the real file.
#
# Key differences from SAMPLE_BOOKING:
#   - SK26 Barnkonferens uses "Ålder " (trailing space, standalone)
#   - Dagsbiljett prefixes use "Ålder"  (no space, standalone) ×3
#   - Both standalone variants coexist in the same booking object
#   - This dict is built via parse_json_with_duplicate_keys() to preserve them
# ---------------------------------------------------------------------------

_REAL_FORMAT_JSON = (
    '{"contact13": {'
    '"Booking ID": "10869",'
    '"Contact First Name": "Jtest",'
    '"Contact Last Name": "Enamn",'
    '"Contact Email": "mail@exempel.se",'
    '"Cell/Mobile": "070730403030",'
    '"SK26 Barnkonferens  First Name": "Barn1",'
    '"SK26 Barnkonferens  Last Name": "Enamn",'
    '"ETicket SK26 Barnkonferens ": "ICCEQUGOWB",'
    '"Ålder ": "04/02/2020",'
    '"Allergier": "",'
    '"Dagsbiljett barn (torsdag 26 juni) First Name": ["Barn2", "Barn22"],'
    '"Dagsbiljett barn (torsdag 26 juni) Last Name": ["Enamn", "Enamn"],'
    '"ETicket Dagsbiljett barn (torsdag 26 juni)": "EDMKIOBKJX",'
    '"Ålder": "15/01/2019|07/03/2014",'
    '"Allergier": "Inget",'
    '"Dagsbiljett barn (fredag 27 juni) First Name": "Barn3",'
    '"Dagsbiljett barn (fredag 27 juni) Last Name": "Enman",'
    '"ETicket Dagsbiljett barn (fredag 27 juni)": "UIWRMAAOTB",'
    '"Ålder": "21/02/2017",'
    '"Allergier": "",'
    '"Dagsbiljett barn (lördag 26 juni) First Name": "Barn4",'
    '"Dagsbiljett barn (lördag 26 juni) Last Name": "Enamn",'
    '"ETicket Dagsbiljett barn (lördag 26 juni)": "EPUYSASVCQ",'
    '"Ålder": "12/02/2019",'
    '"Allergier": ""'
    "}}"
)

_REAL_FORMAT_DATA = parse_json_with_duplicate_keys(_REAL_FORMAT_JSON)
REAL_BOOKING = _REAL_FORMAT_DATA["contact13"]
REAL_DATA = _REAL_FORMAT_DATA

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
        thursday = next((p for p in prefixes if "torsdag 26 juni" in p["prefix"]), None)
        assert thursday is not None
        assert (
            "Barn2" in thursday["sample_children"]
            or "Barn22" in thursday["sample_children"]
        )

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

    def test_array_one_filled_slot(self):
        booking = {
            "Extra vårdnadshavare kontaktinformation First Name": ["Mark ", ""],
            "Extra vårdnadshavare kontaktinformation Last Name": ["Psson ", ""],
        }
        guardian = parse_extra_guardian(booking)
        assert guardian is not None
        assert guardian["first_name"] == "Mark"
        assert guardian["last_name"] == "Psson"

    def test_array_both_filled_slots(self):
        booking = {
            "Extra vårdnadshavare kontaktinformation First Name": ["Mark ", "Jane"],
            "Extra vårdnadshavare kontaktinformation Last Name": ["Psson ", "Doe"],
        }
        guardian = parse_extra_guardian(booking)
        assert guardian is not None
        assert guardian["first_name"] == "Mark"
        assert guardian["last_name"] == "Psson"

    def test_array_all_empty(self):
        booking = {
            "Extra vårdnadshavare kontaktinformation First Name": ["", ""],
            "Extra vårdnadshavare kontaktinformation Last Name": ["", ""],
            "Extra vårdnadshavare kontaktinformation Email": ["", ""],
            "Extra vårdnadshavare kontaktinformation Phone": ["", ""],
        }
        guardian = parse_extra_guardian(booking)
        assert guardian is None

    def test_plain_string_regression(self):
        booking = {
            "Extra vårdnadshavare kontaktinformation First Name": "Mark",
            "Extra vårdnadshavare kontaktinformation Last Name": "Psson",
        }
        guardian = parse_extra_guardian(booking)
        assert guardian is not None
        assert guardian["first_name"] == "Mark"
        assert guardian["last_name"] == "Psson"


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


# ---------------------------------------------------------------------------
# parse_json_with_duplicate_keys
# ---------------------------------------------------------------------------


class TestParseJsonWithDuplicateKeys:
    def test_normal_json_unchanged(self):
        """Non-duplicate keys parse identically to json.loads."""
        import json

        text = '{"a": 1, "b": "hello", "c": [1, 2, 3]}'
        result = parse_json_with_duplicate_keys(text)
        assert result == json.loads(text)

    def test_duplicate_scalar_values_become_duplicate_list(self):
        """When the same key appears twice, both values are preserved."""
        text = '{"key": "first", "key": "second"}'
        result = parse_json_with_duplicate_keys(text)
        assert isinstance(result["key"], _DuplicateList)
        assert list(result["key"]) == ["first", "second"]

    def test_three_duplicate_values(self):
        """All occurrences are collected in order."""
        text = '{"k": "a", "k": "b", "k": "c"}'
        result = parse_json_with_duplicate_keys(text)
        assert isinstance(result["k"], _DuplicateList)
        assert list(result["k"]) == ["a", "b", "c"]

    def test_genuine_array_value_not_wrapped(self):
        """A key whose single value is an array is NOT wrapped in _DuplicateList."""
        text = '{"names": ["Alice", "Bob"]}'
        result = parse_json_with_duplicate_keys(text)
        assert not isinstance(result["names"], _DuplicateList)
        assert result["names"] == ["Alice", "Bob"]

    def test_duplicate_alder_keys_real_shape(self):
        """
        Simulate the real booking JSON: three consecutive 'Ålder' keys, one
        after each child-prefix group.  All three values must survive.
        """
        # Build the JSON string manually (Python dict literals collapse duplicates)
        json_text = (
            '{"contact1": {'
            '"Dagsbiljett barn (torsdag) First Name": ["Barn2", "Barn22"],'
            '"Dagsbiljett barn (torsdag) Last Name": ["Enamn", "Enamn"],'
            '"Ålder": "15/01/2019|07/03/2014",'
            '"Dagsbiljett barn (fredag) First Name": "Barn3",'
            '"Dagsbiljett barn (fredag) Last Name": "Enman",'
            '"Ålder": "21/02/2017",'
            '"Dagsbiljett barn (lördag) First Name": "Barn4",'
            '"Dagsbiljett barn (lördag) Last Name": "Enman",'
            '"Ålder": "12/02/2019"'
            "}}"
        )
        data = parse_json_with_duplicate_keys(json_text)
        booking = data["contact1"]
        alder = booking["Ålder"]
        assert isinstance(alder, _DuplicateList)
        assert list(alder) == ["15/01/2019|07/03/2014", "21/02/2017", "12/02/2019"]

    def test_real_format_trailing_space_key_isolated(self):
        """
        "Ålder " (trailing space) and "Ålder" (no space) are stored under
        separate dict keys — the parser must not merge them.
        """
        data = parse_json_with_duplicate_keys(
            '{"b": {"Ålder ": "04/02/2020", "Ålder": "15/01/2019"}}'
        )
        booking = data["b"]
        assert "Ålder " in booking
        assert "Ålder" in booking
        assert booking["Ålder "] == "04/02/2020"
        assert booking["Ålder"] == "15/01/2019"

    def test_build_alder_map_assigns_values_in_document_order(self):
        """
        build_alder_map() correctly assigns each standalone Ålder value to
        the right prefix by document order, even when all occurrences are
        merged into a single _DuplicateList.
        """
        json_text = (
            '{"contact1": {'
            '"Dagsbiljett barn (torsdag) First Name": ["Barn2", "Barn22"],'
            '"Dagsbiljett barn (torsdag) Last Name": ["Enamn", "Enamn"],'
            '"Ålder": "15/01/2019|07/03/2014",'
            '"Dagsbiljett barn (fredag) First Name": "Barn3",'
            '"Dagsbiljett barn (fredag) Last Name": "Enman",'
            '"Ålder": "21/02/2017",'
            '"Dagsbiljett barn (lördag) First Name": "Barn4",'
            '"Dagsbiljett barn (lördag) Last Name": "Enman",'
            '"Ålder": "12/02/2019"'
            "}}"
        )
        data = parse_json_with_duplicate_keys(json_text)
        booking = data["contact1"]

        prefixes = [
            "Dagsbiljett barn (torsdag)",
            "Dagsbiljett barn (fredag)",
            "Dagsbiljett barn (lördag)",
        ]
        amap = build_alder_map(booking, prefixes)

        assert amap["Dagsbiljett barn (torsdag)"] == "15/01/2019|07/03/2014"
        assert amap["Dagsbiljett barn (fredag)"] == "21/02/2017"
        assert amap["Dagsbiljett barn (lördag)"] == "12/02/2019"

        # Verify children parse correctly when alder_value is supplied
        thu = parse_children_from_prefix(
            booking,
            "Dagsbiljett barn (torsdag)",
            alder_value=amap["Dagsbiljett barn (torsdag)"],
        )
        assert len(thu) == 2
        assert thu[0]["birthdate"] == date(2019, 1, 15)
        assert thu[1]["birthdate"] == date(2014, 3, 7)

        fri = parse_children_from_prefix(
            booking,
            "Dagsbiljett barn (fredag)",
            alder_value=amap["Dagsbiljett barn (fredag)"],
        )
        assert len(fri) == 1
        assert fri[0]["first_name"] == "Barn3"
        assert fri[0]["birthdate"] == date(2017, 2, 21)

        sat = parse_children_from_prefix(
            booking,
            "Dagsbiljett barn (lördag)",
            alder_value=amap["Dagsbiljett barn (lördag)"],
        )
        assert len(sat) == 1
        assert sat[0]["first_name"] == "Barn4"
        assert sat[0]["birthdate"] == date(2019, 2, 12)


# ---------------------------------------------------------------------------
# Real export format: mixed "Ålder " (trailing space) + standalone "Ålder"
# This is the actual shape from the production booking system.
# ---------------------------------------------------------------------------


class TestRealFormatBooking:
    """
    Tests against REAL_BOOKING — a booking parsed from JSON that matches the
    exact field layout of the production export, including:
      - "Ålder " (trailing space) for SK26 Barnkonferens
      - standalone "Ålder" (no space) × 3 for the three Dagsbiljett prefixes
      - SK26 prefix has a trailing double-space in its name
    """

    ALL_PREFIXES = [
        "SK26 Barnkonferens ",
        "Dagsbiljett barn (torsdag 26 juni)",
        "Dagsbiljett barn (fredag 27 juni)",
        "Dagsbiljett barn (lördag 26 juni)",
    ]

    def _parse(self, prefix):
        """Helper: parse one prefix using the pre-built alder map."""
        amap = build_alder_map(REAL_BOOKING, self.ALL_PREFIXES)
        return parse_children_from_prefix(
            REAL_BOOKING, prefix, alder_value=amap.get(prefix)
        )

    def test_sk26_gets_correct_birthdate(self):
        """SK26 Barnkonferens  must pick up "Ålder " (trailing space), not "Ålder"."""
        children = self._parse("SK26 Barnkonferens ")
        assert len(children) == 1
        assert children[0]["first_name"] == "Barn1"
        assert children[0]["birthdate"] == date(2020, 2, 4)

    def test_thursday_barn2_gets_birthdate(self):
        children = self._parse("Dagsbiljett barn (torsdag 26 juni)")
        assert len(children) == 2
        assert children[0]["first_name"] == "Barn2"
        assert children[0]["birthdate"] == date(2019, 1, 15)

    def test_thursday_barn22_gets_birthdate(self):
        """The original bug: Barn22 (index 1) must get its birthdate from the pipe-delimited string."""
        children = self._parse("Dagsbiljett barn (torsdag 26 juni)")
        assert len(children) == 2
        assert children[1]["first_name"] == "Barn22"
        assert children[1]["birthdate"] == date(2014, 3, 7)

    def test_friday_gets_correct_birthdate(self):
        children = self._parse("Dagsbiljett barn (fredag 27 juni)")
        assert len(children) == 1
        assert children[0]["first_name"] == "Barn3"
        assert children[0]["birthdate"] == date(2017, 2, 21)

    def test_saturday_gets_correct_birthdate(self):
        children = self._parse("Dagsbiljett barn (lördag 26 juni)")
        assert len(children) == 1
        assert children[0]["first_name"] == "Barn4"
        assert children[0]["birthdate"] == date(2019, 2, 12)

    def test_all_four_prefixes_via_parse_booking(self):
        """End-to-end parse with all four prefixes — total 5 children, all with birthdates."""
        mappings = {
            "SK26 Barnkonferens ": "full_event",
            "Dagsbiljett barn (torsdag 26 juni)": "session-thu",
            "Dagsbiljett barn (fredag 27 juni)": "session-fri",
            "Dagsbiljett barn (lördag 26 juni)": "session-sat",
        }
        result = parse_booking(REAL_BOOKING, mappings)
        assert len(result["children"]) == 5
        for child in result["children"]:
            assert child["birthdate"] is not None, (
                f"{child['first_name']} {child['last_name']} has no birthdate"
            )


# ---------------------------------------------------------------------------
# Allergier — same standalone-duplicate-key shape as Ålder.
#
# In the production export, "Allergier" repeats once per child-prefix group
# (collapsing into a _DuplicateList) and is pipe-separated per child within a
# prefix.  The original bug str()'d the whole _DuplicateList and assigned the
# blob to every child, e.g.
#   ['Vegetariskt, glutenfritt, sockerfritt|Vegetariskt, sockerfritt',
#    'Vegetariskt, sockerfritt|Vegetariskt, sockerfritt|Vegetariskt, sockerfritt',
#    '', '', '']
# These tests pin the per-child split.
# ---------------------------------------------------------------------------

_ALLERGY_FORMAT_JSON = (
    '{"contact13": {'
    '"Booking ID": "10869",'
    '"Contact First Name": "Jtest",'
    '"Contact Last Name": "Enamn",'
    '"Contact Email": "mail@exempel.se",'
    # prefix 1: two children, two pipe-separated allergies
    '"Dagsbiljett barn (torsdag 26 juni) First Name": ["Barn1", "Barn11"],'
    '"Dagsbiljett barn (torsdag 26 juni) Last Name": ["Enamn", "Enamn"],'
    '"Ålder": "15/01/2019|07/03/2014",'
    '"Allergier": "Vegetariskt, glutenfritt, sockerfritt|Vegetariskt, sockerfritt",'
    # prefix 2: three children, three pipe-separated allergies
    '"Dagsbiljett barn (fredag 27 juni) First Name": ["Barn2", "Barn22", "Barn222"],'
    '"Dagsbiljett barn (fredag 27 juni) Last Name": ["Enamn", "Enamn", "Enamn"],'
    '"Ålder": "21/02/2017|01/01/2016|02/02/2015",'
    '"Allergier": "Vegetariskt, sockerfritt|Vegetariskt, sockerfritt|Vegetariskt, sockerfritt",'
    # prefixes 3-5: one child each, no allergies
    '"Dagsbiljett barn (lördag 28 juni) First Name": "Barn3",'
    '"Dagsbiljett barn (lördag 28 juni) Last Name": "Enamn",'
    '"Ålder": "12/02/2019",'
    '"Allergier": "",'
    '"Dagsbiljett barn (söndag 29 juni) First Name": "Barn4",'
    '"Dagsbiljett barn (söndag 29 juni) Last Name": "Enamn",'
    '"Ålder": "12/02/2018",'
    '"Allergier": "",'
    '"Dagsbiljett barn (måndag 30 juni) First Name": "Barn5",'
    '"Dagsbiljett barn (måndag 30 juni) Last Name": "Enamn",'
    '"Ålder": "12/02/2017",'
    '"Allergier": ""'
    "}}"
)

ALLERGY_BOOKING = parse_json_with_duplicate_keys(_ALLERGY_FORMAT_JSON)["contact13"]


class TestAllergierPerChild:
    MAPPINGS = {
        "Dagsbiljett barn (torsdag 26 juni)": "full_event",
        "Dagsbiljett barn (fredag 27 juni)": "full_event",
        "Dagsbiljett barn (lördag 28 juni)": "full_event",
        "Dagsbiljett barn (söndag 29 juni)": "full_event",
        "Dagsbiljett barn (måndag 30 juni)": "full_event",
    }

    def _children(self):
        result = parse_booking(ALLERGY_BOOKING, self.MAPPINGS)
        return {c["first_name"]: c for c in result["children"]}

    def test_no_child_gets_the_raw_duplicate_list_blob(self):
        """Regression: nobody should get the str() of the whole _DuplicateList."""
        for child in parse_booking(ALLERGY_BOOKING, self.MAPPINGS)["children"]:
            allergies = child["allergies"] or ""
            assert "[" not in allergies and "'" not in allergies, (
                f"{child['first_name']} got a list blob: {allergies!r}"
            )

    def test_first_prefix_splits_allergies_per_child(self):
        kids = self._children()
        assert kids["Barn1"]["allergies"] == "Vegetariskt, glutenfritt, sockerfritt"
        assert kids["Barn11"]["allergies"] == "Vegetariskt, sockerfritt"

    def test_second_prefix_splits_allergies_per_child(self):
        kids = self._children()
        assert kids["Barn2"]["allergies"] == "Vegetariskt, sockerfritt"
        assert kids["Barn22"]["allergies"] == "Vegetariskt, sockerfritt"
        assert kids["Barn222"]["allergies"] == "Vegetariskt, sockerfritt"

    def test_empty_allergies_become_none(self):
        kids = self._children()
        assert kids["Barn3"]["allergies"] is None
        assert kids["Barn4"]["allergies"] is None
        assert kids["Barn5"]["allergies"] is None

    def test_allergies_align_with_birthdates(self):
        """The allergy split must use the same per-child index as Ålder."""
        kids = self._children()
        assert kids["Barn1"]["birthdate"] == date(2019, 1, 15)
        assert kids["Barn11"]["birthdate"] == date(2014, 3, 7)


# ---------------------------------------------------------------------------
# parse_contact — Cell/Mobile and Contact Email duplicate-key regression.
#
# In some exports "Cell/Mobile" (and potentially "Contact Email") appears more
# than once, collapsing into a _DuplicateList.  The old str() call converted
# the whole list to a blob like "['070...', '070...']".  The fix uses
# _first_nonempty() which already handles lists, consistent with the same
# treatment in parse_extra_guardian.
# ---------------------------------------------------------------------------

_PHONE_DUPE_JSON = (
    '{"contact1": {'
    '"Booking ID": "99999",'
    '"Contact First Name": "Test",'
    '"Contact Last Name": "Person",'
    '"Contact Email": "first@example.se",'
    '"Cell/Mobile": "0707111111",'
    '"Cell/Mobile": "0707222222"'
    "}}"
)

_EMAIL_DUPE_JSON = (
    '{"contact1": {'
    '"Booking ID": "99998",'
    '"Contact First Name": "Test",'
    '"Contact Last Name": "Person",'
    '"Contact Email": "first@example.se",'
    '"Contact Email": "second@example.se",'
    '"Cell/Mobile": "0707333333"'
    "}}"
)

PHONE_DUPE_BOOKING = parse_json_with_duplicate_keys(_PHONE_DUPE_JSON)["contact1"]
EMAIL_DUPE_BOOKING = parse_json_with_duplicate_keys(_EMAIL_DUPE_JSON)["contact1"]


class TestParseContactDuplicateKeys:
    def test_phone_no_blob_when_duplicate(self):
        """Regression: phone must not be a str() of the _DuplicateList."""
        contact = parse_contact(PHONE_DUPE_BOOKING)
        phone = contact["phone"] or ""
        assert "[" not in phone and "'" not in phone, (
            f"phone is a raw list blob: {phone!r}"
        )

    def test_phone_uses_first_value(self):
        contact = parse_contact(PHONE_DUPE_BOOKING)
        assert contact["phone"] == "0707111111"

    def test_email_no_blob_when_duplicate(self):
        """Regression: email must not be a str() of the _DuplicateList."""
        contact = parse_contact(EMAIL_DUPE_BOOKING)
        email = contact["email"] or ""
        assert "[" not in email and "'" not in email, (
            f"email is a raw list blob: {email!r}"
        )

    def test_email_uses_first_value(self):
        contact = parse_contact(EMAIL_DUPE_BOOKING)
        assert contact["email"] == "first@example.se"

    def test_single_values_unchanged(self):
        """Non-duplicate keys still work as before."""
        contact = parse_contact(SAMPLE_BOOKING)
        assert contact["phone"] == "070730403030"
        assert contact["email"] == "mail@exempel.se"
