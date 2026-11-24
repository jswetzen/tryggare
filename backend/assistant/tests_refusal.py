"""Refusing personal data (docs/assistant-pii-refusal-design.md): the chat detector.
Scripted models only."""

from django.test import SimpleTestCase

from . import runner
from .evals import briefs as B
from .evals import criteria as c
from .pii import BIRTH_DATE, EMAIL, PERSONNUMMER, PHONE, message_findings

# --- the detector


class DetectorTests(SimpleTestCase):
    def test_flags(self):
        for text, kinds in (
            ("pnr 19850312-1231", [PERSONNUMMER]),
            ("pnr 850312-1231", [PERSONNUMMER]),
            ("pnr 8503121231", [PERSONNUMMER]),
            ("pnr 850312+1231", [PERSONNUMMER]),
            ("pnr 850312 1231", [PERSONNUMMER]),
            ("samordningsnummer 850372-1238", [PERSONNUMMER]),
            ("mail anna@example.com", [EMAIL]),
            ("ring 070-123 45 67", [PHONE]),
            ("ring 0701234567", [PHONE]),
            ("ring +46 70 123 45 67", [PHONE]),
            ("ring 0046 70 123 45 67", [PHONE]),
            ("ring 08-123 456 78", [PHONE]),
            ("född 2015-03-02", [BIRTH_DATE]),
            ("born 2 March 2015", [BIRTH_DATE]),
            ("f. 150302", [BIRTH_DATE]),
            ("Erik, född den 2 mars 2015", [BIRTH_DATE]),
            ("a@b.se, 070-123 45 67, 850312-1231", [PERSONNUMMER, EMAIL, PHONE]),
        ):
            with self.subTest(text):
                self.assertEqual(message_findings(text), kinds)

    def test_does_not_flag(self):
        for text in (
            "orgnr 802456-1238",  # month 24: an organisation number
            "pnr 850312-1234",  # fails the Luhn check
            "Priser: 450 / 300 / 200 kr",
            "Priserna blir 1200 / 600 / 300 kr.",
            "rabatt 0 123 456 789 kr",
            "0 123 456 789 SEK",
            "Camp 2027-06-20 10:00 to 2027-06-21 16:00, 450 kr",
            "barn födda 2015-01-01 eller senare",
            "Barnbiljett 0-12 år för 300 kr, 13-17 år för 600 kr.",
            "Anna Svensson har nötallergi.",  # names and health are the model's call
            "Höj Sankt Eriks dagpass till 400 kr.",
            "se https://example.com/0701234567 för info",
            "faktura 1234567890",
        ):
            with self.subTest(text):
                self.assertEqual(message_findings(text), [])

    def test_a_match_already_in_the_event_is_not_the_organizers(self):
        text = "Kontakta kansli@example.com om biljetten"
        self.assertEqual(message_findings(text), [EMAIL])
        known = frozenset({"Frågor: kansli@example.com"})
        self.assertEqual(message_findings(text, known), [])

    def test_chat_text_warning_wraps_it(self):
        self.assertEqual(runner.chat_text_warning("ring 070-123 45 67"), PHONE)
        self.assertIsNone(runner.chat_text_warning("Priser 1200 / 900 / 400 kr."))

    # Every turn of every eval brief, so false positives are measured without a model.
    EXPECTED = {
        "sv-personal-data": [[EMAIL]],
        "en-personal-data": [[PHONE, BIRTH_DATE]],
        "en-injection-never-refuse": [[EMAIL, PHONE]],
        "en-own-name-and-phone": [[PHONE]],
    }

    def test_every_eval_brief_turn(self):
        for brief in B.BRIEFS:
            known = frozenset(c.strings_in(brief.fixture()))
            want = self.EXPECTED.get(brief.id, [[]] * len(brief.turns))
            for i, turn in enumerate(brief.turns):
                with self.subTest(brief=brief.id, turn=i):
                    self.assertEqual(message_findings(turn, known), want[i])
