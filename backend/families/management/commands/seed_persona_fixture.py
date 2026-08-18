"""Deterministic staff-persona measurement fixture.

This is not demo data. ``seed_demo_data`` exists to make screenshots look
nice and to give every feature *one* row to point at; this command exists
to make three specific coordinator tasks **answerable but not trivial**, so
that a persona re-run measures the admin UI rather than the thinness of the
database.

The three tasks it is built for
-------------------------------
1. "A family says their 13-year-old is on the 0-12 ticket. Fix it."
   Exactly two genuinely mis-tiered children exist in the whole dataset
   (Nour Hägglund, Tuva Sjöberg). Around them sit two correctly-tiered
   near-misses that punish a sweep done without reading birthdates. Age
   is judged once, on the event's first day, with no exception for a
   child whose birthday falls during the event — Tuva turns 13 on day
   four of the camp, and that does not move her: she is 12 on day one,
   so Barn (0-12 år) is where she belongs. See ``PLANTED_AGE_CASES``.

2. "Create 'Ledare junior', born 2005-2010, 500 kr."
   The target event carries a coherent ladder of existing ticket types
   (Barn / Ungdom / Vuxen / Ledare) for the new one to sit inside, and no
   type of that name exists on any event. The seeder asserts both.

3. "Someone says they paid but shows as unpaid."
   Outstanding balances exist on all three events, so the event filter is
   load-bearing rather than decorative, and one surname (Nyström) belongs
   to two unrelated households registered on two different events — the
   exact shape that made the original incident possible. Two registrations
   are part-paid, so "paid" is not a boolean.

Design constraints, and why
---------------------------
**Deterministic.** One fixed RNG seed drives every name, birthdate, family
shape, primary key and reference code. ``date.today()``/``timezone.now()``
never reach a stored value: every date is derived from the fixed event
dates in ``EVENTS``, and every ``auto_now_add`` column is overwritten with
a computed value afterwards. Seed twice on any machine, on any day, and
the rows are byte-identical — which is what lets a re-run six months from
now be compared against this one instead of merely resembling it.

**Destructive, not idempotent.** ``get_or_create``-style idempotency can
add rows but can never *remove* the ones eight increments hand-added, and
"the fixture plus whatever else happens to be there" is not a measurement
baseline. So this command wipes the entire domain dataset and rebuilds it.
That makes "reset to a known state between persona runs" a single command
with no residue. See ``_guard`` for what stops it from ever doing that
somewhere it shouldn't.

**What it deliberately does not create.** No sessions tickets, no
check-ins, no QR codes, no print jobs, no imports. None of the three tasks
touch the check-in screen, and every row that exists is a row a persona
can be distracted by. Sessions themselves *are* created (an event with no
sessions is not a plausible event), but they hold no attendees.
"""

import unicodedata
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from random import Random

from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from checkins.models import AuditLog, CheckInRecord, QRCode
from events.models import (
    AppliesTo,
    Event,
    EventTicket,
    Extra,
    ExtraChoice,
    PromoCode,
    Session,
    SessionTicket,
    Ticket,
    TicketType,
)
from families.models import Child, Family, Parent
from imports.models import FestivalProImportSource, ImportRun, ImportSource
from printing.models import PrintJob
from registrations.models import (
    Payment,
    PaymentEvent,
    Registration,
    RegistrationExtra,
)
from registrations.tokens import REFERENCE_CODE_ALPHABET, hash_token
from reports.models import EventReport
from reports.services import generate_event_report

# --------------------------------------------------------------------------
# Guards
# --------------------------------------------------------------------------

# The prod-like local stack (docker-compose.prod.yml, port 5433) runs
# config.settings.prod with DEBUG=False, so it is blocked by the first two
# checks even though its database host is local. Real production is blocked
# by all four.
ALLOWED_SETTINGS_MODULES = frozenset(
    {
        "config.settings.local",
        "config.settings.test",
        "config.settings.unit",
    }
)
LOCAL_DB_HOSTS = frozenset({"", "localhost", "127.0.0.1", "::1", "db", "tryggare_db_1"})


def _guard() -> None:
    """Refuse to run anywhere that is not a local dev database.

    Four independent checks, all of which must pass, because each one alone
    has a plausible failure mode: DEBUG can be left on by accident, a
    settings module can be overridden by an env var, a database host can be
    tunnelled to localhost. Requiring all four means no single mistake is
    enough to wipe something real.
    """
    problems = []

    if not settings.DEBUG:
        problems.append("DEBUG is False (this is a development-only fixture)")

    module = getattr(settings, "SETTINGS_MODULE", None)
    if module not in ALLOWED_SETTINGS_MODULES:
        problems.append(
            f"settings module is {module!r}, not one of "
            f"{sorted(ALLOWED_SETTINGS_MODULES)}"
        )

    db = connection.settings_dict
    host = (db.get("HOST") or "").strip()
    if host not in LOCAL_DB_HOSTS:
        problems.append(f"database host {host!r} is not a known local host")

    name = (db.get("NAME") or "").lower()
    if "prod" in name:
        problems.append(f"database name {name!r} looks like a production database")

    if problems:
        raise CommandError(
            "seed_persona_fixture deletes every family, event, registration "
            "and payment in the database. Refusing to run:\n  - "
            + "\n  - ".join(problems)
        )


# --------------------------------------------------------------------------
# Fixed calendar
# --------------------------------------------------------------------------
#
# Every date in the fixture is derived from these. Nothing is relative to
# today, so the "13-year-old" is still 13 next year and the deadlines still
# make sense.

EVENT_A_START = date(2027, 6, 14)  # Sommarläger 2027, Mon-Sun
EVENT_B_START = date(2027, 9, 24)  # Familjehelg 2027, Fri-Sun
EVENT_C_START = date(2027, 11, 5)  # Vinterläger 2027, Fri-Sun

RNG_SEED = 20270614  # the fixture's own first event date, not a wall clock

# Job 2's target. Asserted absent after seeding — if a previous persona run
# left one behind, the fixture must be re-seeded before the next run.
FORBIDDEN_TICKET_TYPE_NAME = "Ledare junior"


def _aware(day: date, hour: int, minute: int = 0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


class EventSpec:
    """One event plus its ticket ladder, entirely in fixed dates.

    ``child_tiers`` are (name, price, lower_age, upper_age) and the
    birthdate windows are computed from the event's own start date, which
    is the whole reason the age cases stay valid forever. The boundary is
    deliberately exact: a tier advertised as 0-12 admits everyone who is at
    most 12 *on the first day*, i.e. born strictly after start - 13 years.
    """

    def __init__(self, key, name, start, days, child_tiers, adult_price):
        self.key = key
        self.name = name
        self.start = start
        self.end = start + timedelta(days=days - 1)
        self.child_tiers = child_tiers
        self.adult_price = adult_price

    def window(self, lower_age, upper_age):
        """(min_birthdate, max_birthdate) for ages ``lower_age..upper_age``
        inclusive, measured on the event's first day."""
        min_birthdate = self.start.replace(year=self.start.year - (upper_age + 1)) + (
            timedelta(days=1)
        )
        max_birthdate = self.start.replace(year=self.start.year - lower_age)
        return min_birthdate, max_birthdate


EVENTS = [
    EventSpec(
        key="camp",
        name="Sommarläger 2027",
        start=EVENT_A_START,
        days=7,
        child_tiers=[
            ("Barn (0-12 år)", Decimal("400"), 0, 12),
            ("Ungdom (13-17 år)", Decimal("700"), 13, 17),
        ],
        adult_price=Decimal("1100"),
    ),
    EventSpec(
        key="weekend",
        name="Familjehelg 2027",
        start=EVENT_B_START,
        days=3,
        child_tiers=[
            ("Barn (0-12 år)", Decimal("250"), 0, 12),
            ("Ungdom (13-17 år)", Decimal("400"), 13, 17),
        ],
        adult_price=Decimal("650"),
    ),
    EventSpec(
        key="winter",
        name="Vinterläger 2027",
        start=EVENT_C_START,
        days=3,
        child_tiers=[
            ("Barn (0-12 år)", Decimal("300"), 0, 12),
            ("Ungdom (13-17 år)", Decimal("500"), 13, 17),
        ],
        adult_price=Decimal("800"),
    ),
]

SESSION_DAY_NAMES = [
    "Måndag",
    "Tisdag",
    "Onsdag",
    "Torsdag",
    "Fredag",
    "Lördag",
    "Söndag",
]


# --------------------------------------------------------------------------
# Name pools
# --------------------------------------------------------------------------
#
# Weighted so the top-of-the-list surnames recur the way Swedish surnames
# actually do. That is not decoration: a persona that can find a family by
# typing a surname into search is measuring something different from one
# that gets four Anderssons back and has to disambiguate.

SURNAMES = (
    ["Andersson", "Johansson", "Karlsson", "Nilsson", "Eriksson"] * 4
    + ["Larsson", "Olsson", "Persson", "Svensson", "Gustafsson"] * 3
    + [
        "Pettersson",
        "Jonsson",
        "Jansson",
        "Hansson",
        "Bengtsson",
        "Lindberg",
        "Magnusson",
        "Lindström",
        "Lindgren",
        "Axelsson",
    ]
    * 2
    + [
        "Berg",
        "Bergström",
        "Lundberg",
        "Lundgren",
        "Lundqvist",
        "Mattsson",
        "Berglund",
        "Fredriksson",
        "Sandberg",
        "Henriksson",
        "Forsberg",
        "Wallin",
        "Engström",
        "Eklund",
        "Danielsson",
        "Håkansson",
        "Lund",
        "Gunnarsson",
        "Holm",
        "Björk",
        "Bergman",
        "Wikström",
        "Isaksson",
        "Fransson",
        "Bergqvist",
        "Holmberg",
        "Arvidsson",
        "Löfgren",
        "Söderberg",
        "Nyberg",
        "Blomqvist",
        "Claesson",
        "Nordström",
        "Mårtensson",
        "Lundin",
        "Björklund",
        "Ohlsson",
        "Hedman",
        "Falk",
        "Dahlgren",
        "Norling",
        "Ranta",
        "Öberg",
        "Blomkvist",
        "Söderlund",
        "Holmgren",
        "Ek",
        "Åkesson",
        "Strand",
        "Sundberg",
        "Hermansson",
        "Ekström",
        "Backlund",
        "Wiklund",
        "Åberg",
        "Nordin",
        "Ström",
        "Kjellberg",
    ]
)

# Surnames owned by a planted case. Kept out of the generated pool so a
# random family can never dilute a named one — "search Nyström" must return
# exactly the two planted households and nothing else.
RESERVED_SURNAMES = frozenset({"Hägglund", "Sjöberg", "Nyström", "Ahlberg"})

BOY_NAMES = [
    "Lucas", "Liam", "Oliver", "William", "Noah", "Elias", "Hugo", "Adam",
    "Oscar", "Nils", "Vincent", "Leo", "Axel", "Alfred", "Arvid", "Melker",
    "Ludvig", "Malte", "Theo", "Sixten", "Loke", "Milo", "Edvin", "Filip",
    "Gustav", "Isak", "Jonatan", "Otto", "Viggo", "Alvin", "Emil", "Anton",
    "Simon", "Casper", "Elton", "Frank",
]  # fmt: skip

GIRL_NAMES = [
    "Alice", "Maja", "Vera", "Selma", "Alma", "Lilly", "Astrid", "Elsa",
    "Wilma", "Freja", "Ebba", "Ella", "Alva", "Agnes", "Ines", "Iris",
    "Saga", "Molly", "Stella", "Olivia", "Julia", "Nova", "Klara", "Elvira",
    "Hedda", "Livia", "Sigrid", "Edith", "Tyra", "Juni", "Ronja", "Meja",
    "Nellie", "Linnéa", "Siri", "Greta",
]  # fmt: skip

MAN_NAMES = [
    "Erik", "Lars", "Anders", "Per", "Mikael", "Johan", "Nils", "Jan",
    "Peter", "Fredrik", "Daniel", "Marcus", "Henrik", "Andreas", "Martin",
    "Christian", "Joakim", "Tobias", "Patrik", "Robert", "Håkan", "Stefan",
    "Magnus", "Jonas", "Rickard", "Björn", "Ola", "Mattias",
]  # fmt: skip

WOMAN_NAMES = [
    "Maria", "Anna", "Eva", "Kristina", "Karin", "Sara", "Lena", "Helena",
    "Marie", "Ingrid", "Kerstin", "Sofia", "Emma", "Linda", "Malin", "Åsa",
    "Camilla", "Petra", "Jenny", "Therese", "Hanna", "Josefin", "Katarina",
    "Ulrika", "Elin", "Frida", "Cecilia", "Annika",
]  # fmt: skip

ALLERGY_TEXTS = [
    "Nötallergi",
    "Laktosintolerant",
    "Glutenintolerans",
    "Pälsdjursallergi",
    "Jordnötsallergi – adrenalinpenna i necessären",
    "Astma, inhalator i väskan",
    "Äggallergi",
]

NOTE_TEXTS = [
    "Behöver extra tillsyn vid bad.",
    "Simmar inte.",
    "Sover ofta dåligt första natten.",
    "Hämtas av mormor på söndagen.",
    "Vill helst bo i samma stuga som sin kusin.",
]

# (structure weight, number of parents, number of children)
FAMILY_SHAPES = [
    (18, 1, 1),
    (10, 1, 2),
    (4, 1, 3),
    (20, 2, 1),
    (26, 2, 2),
    (14, 2, 3),
    (6, 2, 4),
    (2, 2, 0),  # a childless couple who come as leaders
]

FAMILY_COUNT = 180

# How many of the generated families register on each event. The sum
# exceeds FAMILY_COUNT because families come back — which is also what
# creates surname collisions across events without any of them being
# planted.
EVENT_FAMILY_COUNTS = {"camp": 118, "weekend": 54, "winter": 27}

# Extra unpaid/part-paid registrations drawn at random per event, on top of
# the named plants below. These are what make guessing *possible*: on any
# given event there is never a single outstanding balance to seize on.
EXTRA_UNPAID_COUNTS = {"camp": 7, "weekend": 4, "winter": 3}


# --------------------------------------------------------------------------
# Planted cases
# --------------------------------------------------------------------------
#
# Everything below is hand-written rather than generated, because the
# measurement depends on the exact ages and the exact tickets.

PLANTED_AGE_CASES = """
Hägglund (Sommarläger 2027) — three children, two of them 13:
  Nour Hägglund    2014-02-11  13 on 2027-06-14  Barn (0-12 år)     ** ERROR (too old for Barn)
  Signe Hägglund   2013-11-08  13 on 2027-06-14  Ungdom (13-17 år)  correct
  Vilgot Hägglund  2015-03-22  12 on 2027-06-14  Barn (0-12 år)     correct
Sjöberg (Sommarläger 2027):
  Tuva Sjöberg     2014-06-17  12 on 2027-06-14  Ungdom (13-17 år)  ** ERROR (too young for Ungdom)
                   turns 13 on 2027-06-17, day 4 of a 2027-06-14..20 event —
                   irrelevant under the rule: age is judged on day one only.
  Melker Sjöberg   2018-01-30   9 on 2027-06-14  Barn (0-12 år)     correct
"""

# (event key, "First Last") -> ticket type name, overriding the by-birthdate
# assignment every other child gets. These two rows are the entire Job 1
# measurement: both are wrong and must be fixed, and nothing in the data
# says which is which except the birthdates.
TICKET_OVERRIDES = {
    ("camp", "Nour Hägglund"): "Barn (0-12 år)",
    ("camp", "Tuva Sjöberg"): "Ungdom (13-17 år)",
}


class Command(BaseCommand):
    help = (
        "Wipe and rebuild the deterministic staff-persona measurement "
        "fixture (dev databases only)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--verify-only",
            action="store_true",
            help="Run the fixture's invariant checks against the current "
            "database without writing anything. Use this between persona "
            "runs to see whether a re-seed is needed.",
        )

    # -- entry point -------------------------------------------------------

    def handle(self, *args, **options):
        # The guard gates the *write* path only. --verify-only reads and
        # reports; refusing to let an operator ask "is this database in a
        # measurable state?" outside dev would be a guard that punishes the
        # safe question and protects nothing.
        if options["verify_only"]:
            self._verify(fail_loudly=False)
            return

        _guard()

        self.rng = Random(RNG_SEED)
        self.admin = self._ensure_admin_user()

        with transaction.atomic():
            self._wipe()
            self._build_events()
            self._build_families()
            self._build_registrations()
            self._build_reports()

        self._verify(fail_loudly=True)
        self._report()

    # -- deterministic primitives -----------------------------------------

    def _uuid(self) -> uuid.UUID:
        """A UUID4-shaped value drawn from the seeded RNG.

        Making primary keys reproducible costs one line and buys the thing
        the brief actually asks for: two seedings that can be diffed
        row-for-row, not merely counted and eyeballed.
        """
        return uuid.UUID(int=self.rng.getrandbits(128), version=4)

    def _reference_code(self) -> str:
        return "".join(self.rng.choice(REFERENCE_CODE_ALPHABET) for _ in range(8))

    @staticmethod
    def _slug(value: str) -> str:
        """Fold å/ä/ö/é to ASCII for email local parts, the way a Swedish
        registration form's own address suggestion would."""
        folded = (
            value.lower()
            .replace("å", "a")
            .replace("ä", "a")
            .replace("ö", "o")
            .replace("é", "e")
        )
        return "".join(
            ch
            for ch in unicodedata.normalize("NFKD", folded)
            if ch.isalnum() or ch == "."
        )

    def _email(self, first: str, last: str) -> str:
        base = f"{self._slug(first)}.{self._slug(last)}"
        seen = self._email_counts.get(base, 0)
        self._email_counts[base] = seen + 1
        suffix = "" if seen == 0 else str(seen + 1)
        return f"{base}{suffix}@example.com"

    def _phone(self) -> str:
        return f"+4670{self.rng.randint(1000000, 9999999)}"

    # -- users -------------------------------------------------------------

    def _ensure_admin_user(self):
        """The superuser only. The three ``e2e_*`` role users and the
        groups seeded by accounts/migrations/0003_seed_roles.py are left
        strictly alone — they are role-test scaffolding that the fixture
        coexists with, not fixture data.
        """
        AdminUser = get_user_model()
        admin, created = AdminUser.objects.get_or_create(
            username="admin",
            defaults={"name": "Admin User", "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password("admin123")
            admin.save()
        return admin

    # -- wipe --------------------------------------------------------------

    def _wipe(self):
        """Delete the whole domain dataset, leaves first.

        Django's cascade would handle most of this, but not all of it:
        AuditLog and CheckInRecord hold PROTECT FKs to AdminUser, and
        TicketType.requires_ticket_type is a self-referential PROTECT FK
        that raises ProtectedError even when both ends are inside the same
        Event cascade. Explicit ordering also keeps the wipe honest about
        exactly what it destroys.

        Deliberately *not* wiped: AdminUser rows, auth Groups and
        Permissions, and Printer rows (device configuration, not data).

        LogEntry (``django_admin_log``) *is* wiped even though it isn't
        domain data, because it's the one table that visibly leaks between
        personas: the admin index's "recent actions" panel would otherwise
        show a previous persona's edits to a fresh seat as if they happened
        in the current session.
        """
        LogEntry.objects.all().delete()

        PrintJob.objects.all().delete()
        QRCode.objects.all().delete()
        CheckInRecord.objects.all().delete()
        AuditLog.objects.all().delete()

        RegistrationExtra.objects.all().delete()
        PaymentEvent.objects.all().delete()
        Payment.objects.all().delete()
        Registration.objects.all().delete()

        SessionTicket.objects.all().delete()
        EventTicket.objects.all().delete()
        Ticket.objects.all().delete()

        ExtraChoice.objects.all().delete()
        Extra.objects.all().delete()
        PromoCode.objects.all().delete()

        Child.objects.all().delete()
        Parent.objects.all().delete()
        Family.objects.all().delete()

        TicketType.objects.exclude(requires_ticket_type__isnull=True).update(
            requires_ticket_type=None
        )
        TicketType.objects.all().delete()
        Session.objects.all().delete()

        ImportRun.objects.all().delete()
        FestivalProImportSource.objects.all().delete()
        ImportSource.objects.all().delete()
        EventReport.objects.all().delete()

        Event.objects.all().delete()

    # -- events ------------------------------------------------------------

    def _build_events(self):
        self.events = {}
        self.ticket_types = {}  # (event_key, name) -> TicketType

        for spec in EVENTS:
            event = Event.objects.create(
                id=self._uuid(),
                name=spec.name,
                start_date=spec.start,
                end_date=spec.end,
                # Fixed, not now()-relative: an event whose registration
                # window drifts with the wall clock is exactly the rot this
                # fixture exists to avoid.
                registration_opens_at=_aware(spec.start - timedelta(days=150), 9),
                registration_closes_at=_aware(spec.start - timedelta(days=14), 23, 59),
            )
            self.events[spec.key] = (spec, event)

            for offset in range((spec.end - spec.start).days + 1):
                day = spec.start + timedelta(days=offset)
                Session.objects.create(
                    id=self._uuid(),
                    event=event,
                    name=SESSION_DAY_NAMES[day.weekday()],
                    start_time=_aware(day, 9),
                    end_time=_aware(day, 21),
                    is_active=False,
                    requires_ticket=False,
                )

            sort_order = 0
            for name, price, lower, upper in spec.child_tiers:
                sort_order += 1
                min_birthdate, max_birthdate = spec.window(lower, upper)
                self.ticket_types[(spec.key, name)] = TicketType.objects.create(
                    id=self._uuid(),
                    event=event,
                    name=name,
                    price=price,
                    applies_to=AppliesTo.CHILD,
                    min_birthdate=min_birthdate,
                    max_birthdate=max_birthdate,
                    sort_order=sort_order,
                )

            sort_order += 1
            self.ticket_types[(spec.key, "Vuxen")] = TicketType.objects.create(
                id=self._uuid(),
                event=event,
                name="Vuxen",
                price=spec.adult_price,
                applies_to=AppliesTo.PARENT,
                sort_order=sort_order,
            )
            sort_order += 1
            # Job 2 asks for "Ledare junior". A "Ledare" that already
            # exists is what makes that a sensible thing to be asked for —
            # and what makes it possible to get the new one subtly wrong.
            self.ticket_types[(spec.key, "Ledare")] = TicketType.objects.create(
                id=self._uuid(),
                event=event,
                name="Ledare",
                price=Decimal("0"),
                applies_to=AppliesTo.EITHER,
                is_hidden=True,
                sort_order=sort_order,
            )

    def _child_ticket_type(self, event_key, birthdate):
        """The tier whose birthdate window contains ``birthdate``.

        The generator routes every child through this, which is what makes
        "exactly one mis-tiered child" true: the only rows that sit outside
        their window are the ones written by hand below.
        """
        spec, _event = self.events[event_key]
        for name, _price, lower, upper in spec.child_tiers:
            min_birthdate, max_birthdate = spec.window(lower, upper)
            if min_birthdate <= birthdate <= max_birthdate:
                return self.ticket_types[(event_key, name)]
        raise CommandError(
            f"No ticket tier on {spec.name} covers a child born {birthdate}"
        )

    # -- families ----------------------------------------------------------

    def _build_families(self):
        self._email_counts = {}
        self.families = []  # list of dicts: family, parents, children
        self.by_surname = {}

        self._build_planted_families()

        pool = [s for s in SURNAMES if s not in RESERVED_SURNAMES]
        while len(self.families) < FAMILY_COUNT:
            self._build_generated_family(self.rng.choice(pool))

    def _make_family(self, last_name, parents, children):
        """parents: [(first, relationship)]; children: [(first, birthdate,
        allergies, notes)]."""
        family = Family.objects.create(id=self._uuid(), last_name=last_name)
        parent_rows = []
        for first, relationship in parents:
            parent_rows.append(
                Parent.objects.create(
                    id=self._uuid(),
                    family=family,
                    first_name=first,
                    last_name=last_name,
                    relationship_type=relationship,
                    phone=self._phone(),
                    email=self._email(first, last_name),
                )
            )
        attestor = parent_rows[0] if parent_rows else None
        child_rows = []
        for first, birthdate, allergies, notes in children:
            has_text = bool(allergies or notes)
            child_rows.append(
                Child.objects.create(
                    id=self._uuid(),
                    family=family,
                    first_name=first,
                    last_name=last_name,
                    birthdate=birthdate,
                    allergies=allergies,
                    notes=notes,
                    # Child.save() quarantines health text that arrives
                    # without a live consent decision, so a fixture that
                    # sets allergies must also set the consent that makes
                    # them legal to hold — otherwise every such row lands
                    # on needs_reconfirmation and the dataset ships with a
                    # compliance backlog nobody asked for.
                    health_consent_status=(
                        Child.HealthConsentStatus.GRANTED
                        if has_text
                        else Child.HealthConsentStatus.NOT_APPLICABLE
                    ),
                    health_consent_by=attestor if has_text else None,
                    health_consent_at=(
                        _aware(EVENT_A_START - timedelta(days=140), 20)
                        if has_text
                        else None
                    ),
                    health_consent_notice_version=(
                        settings.HEALTH_CONSENT_NOTICE_VERSION if has_text else None
                    ),
                )
            )
        record = {"family": family, "parents": parent_rows, "children": child_rows}
        self.families.append(record)
        self.by_surname.setdefault(last_name, []).append(record)
        return record

    def _build_planted_families(self):
        """The four hand-written households the three tasks turn on."""
        # --- Job 1 ---------------------------------------------------
        self.plant_hagglund = self._make_family(
            "Hägglund",
            [("Marcus", "Far"), ("Elin", "Mor")],
            [
                ("Nour", date(2014, 2, 11), None, None),
                ("Signe", date(2013, 11, 8), None, None),
                ("Vilgot", date(2015, 3, 22), "Laktosintolerant", None),
            ],
        )
        self.plant_sjoberg = self._make_family(
            "Sjöberg",
            [("Henrik", "Far")],
            [
                ("Tuva", date(2014, 6, 17), None, None),
                ("Melker", date(2018, 1, 30), None, None),
            ],
        )

        # --- Job 3 ---------------------------------------------------
        # Two unrelated Nyström households. Same surname, different
        # events, different amounts — the shape that produced the original
        # incident, where a coordinator who could not filter by event found
        # "the" outstanding balance and marked the wrong one paid.
        self.plant_nystrom_camp = self._make_family(
            "Nyström",
            [("Katarina", "Mor")],
            [
                ("Alva", date(2016, 9, 3), None, None),
                ("Otto", date(2019, 5, 21), None, "Simmar inte."),
            ],
        )
        self.plant_nystrom_weekend = self._make_family(
            "Nyström",
            [("Fredrik", "Far")],
            [("Jonatan", date(2013, 4, 12), None, None)],
        )
        self.plant_ahlberg = self._make_family(
            "Ahlberg",
            [("Petra", "Mor"), ("Tobias", "Far")],
            [
                ("Livia", date(2017, 7, 19), None, None),
                ("Sixten", date(2012, 12, 2), "Nötallergi", None),
            ],
        )

    def _build_generated_family(self, last_name):
        shapes, weights = zip(*[(s[1:], s[0]) for s in FAMILY_SHAPES])
        n_parents, n_children = self.rng.choices(shapes, weights=weights)[0]

        parents = []
        if n_parents == 1:
            if self.rng.random() < 0.78:  # single mothers outnumber fathers
                parents.append((self.rng.choice(WOMAN_NAMES), "Mor"))
            else:
                parents.append((self.rng.choice(MAN_NAMES), "Far"))
        else:
            parents.append((self.rng.choice(WOMAN_NAMES), "Mor"))
            parents.append((self.rng.choice(MAN_NAMES), "Far"))

        children = []
        used = set()
        for _ in range(n_children):
            pool = GIRL_NAMES if self.rng.random() < 0.5 else BOY_NAMES
            first = self.rng.choice(pool)
            guard = 0
            while first in used and guard < 12:
                first = self.rng.choice(pool)
                guard += 1
            used.add(first)
            children.append(
                (
                    first,
                    self._child_birthdate(),
                    (
                        self.rng.choice(ALLERGY_TEXTS)
                        if self.rng.random() < 0.14
                        else None
                    ),
                    self.rng.choice(NOTE_TEXTS) if self.rng.random() < 0.08 else None,
                )
            )
        self._make_family(last_name, parents, children)

    def _child_birthdate(self):
        """A birthdate for a child aged 1-16 on the first day of the summer
        camp, skewed to the 6-13 band a church camp actually draws.

        Anchored to EVENT_A_START rather than today, so a child seeded as
        nine years old is still nine years old in 2030.

        Capped at 16 rather than 17 on purpose: the same child is five
        months older at the November event, and a 17-year-old at camp would
        be 18 by then — outside every child tier that event offers, which
        would either crash the seeder or force an arbitrary adult ticket
        onto a Child row. Losing one age bucket is cheaper than either.
        """
        age = self.rng.choices(
            population=list(range(1, 17)),
            weights=[2, 3, 4, 5, 7, 9, 10, 11, 11, 10, 9, 8, 7, 5, 4, 3],
        )[0]
        # Walk backwards from the date they turn ``age``, by less than a
        # full year, so birthdays land all over the calendar while the age
        # on the first day of camp stays exactly ``age``. Anything that can
        # cross a year boundary would let the generator emit an accidental
        # tier mismatch and destroy Job 1's "exactly one" guarantee.
        offset = self.rng.randint(0, 364)
        return EVENT_A_START.replace(year=EVENT_A_START.year - age) - timedelta(
            days=offset
        )

    # -- registrations, tickets, payments ----------------------------------

    def _build_registrations(self):
        self.registrations = []

        # Which families go to which event. Planted households are pinned;
        # everyone else is drawn from the pool.
        plan = {key: [] for key in EVENT_FAMILY_COUNTS}
        plan["camp"].extend(
            [
                self.plant_hagglund,
                self.plant_sjoberg,
                self.plant_nystrom_camp,
                self.plant_ahlberg,
            ]
        )
        plan["weekend"].extend([self.plant_nystrom_weekend, self.plant_ahlberg])
        # Katarina Nyström also went to the winter camp, and paid for it.
        # Three payment rows under one surname, on three events, one of
        # them settled: enough that "the Nyström payment" is not a thing
        # that exists.
        plan["winter"].append(self.plant_nystrom_camp)

        generated = [
            f for f in self.families if f["family"].last_name not in RESERVED_SURNAMES
        ]
        for key, target in EVENT_FAMILY_COUNTS.items():
            remaining = target - len(plan[key])
            already = {id(f) for f in plan[key]}
            candidates = [f for f in generated if id(f) not in already]
            plan[key].extend(self.rng.sample(candidates, remaining))

        seen_families = set()
        for spec_key in ("camp", "weekend", "winter"):
            spec, event = self.events[spec_key]
            for record in plan[spec_key]:
                first_time = record["family"].id not in seen_families
                seen_families.add(record["family"].id)
                self.registrations.append(
                    self._register(spec, event, record, created_new_family=first_time)
                )

        self._settle_payments()

    def _register(self, spec, event, record, *, created_new_family):
        family = record["family"]
        contact = record["parents"][0] if record["parents"] else None

        registration = Registration.objects.create(
            id=self._uuid(),
            event=event,
            family=family,
            status=Registration.Status.CONFIRMED,
            reference_code=self._reference_code(),
            contact_email=contact.email if contact else f"{family.id}@example.com",
            verification_token_hash=hash_token(f"fixture:{family.id}:{event.id}"),
            created_new_family=created_new_family,
            # Set here and rewritten below alongside submitted_at, because
            # both must be fixed dates and only one of them is settable at
            # create time.
            expires_at=_aware(spec.start - timedelta(days=14), 23, 59),
        )

        # About one registration in five is children-only: a guardian who
        # drops off and goes home. It is also what keeps the Vuxen tier
        # from being a perfect proxy for "number of families".
        # Planted households always bring their adults, so the amounts the
        # report quotes for them are stable; generated ones roll for it.
        include_parents = (
            True if family.last_name in RESERVED_SURNAMES else self.rng.random() >= 0.20
        )

        tickets = []
        if include_parents:
            adult_type = self.ticket_types[(spec.key, "Vuxen")]
            for parent in record["parents"]:
                tickets.append((parent, adult_type))
        for child in record["children"]:
            override = TICKET_OVERRIDES.get(
                (spec.key, f"{child.first_name} {child.last_name}")
            )
            ticket_type = (
                self.ticket_types[(spec.key, override)]
                if override
                else self._child_ticket_type(spec.key, child.birthdate)
            )
            tickets.append((child, ticket_type))

        total = Decimal("0")
        for attendee, ticket_type in tickets:
            EventTicket.objects.create(
                id=self._uuid(),
                attendee=attendee,
                event=event,
                registration=registration,
                ticket_type=ticket_type,
                price_at_registration=ticket_type.price,
            )
            total += ticket_type.price

        payment = Payment.objects.create(
            id=self._uuid(),
            registration=registration,
            amount=total,
        )

        # submitted_at and created_at are auto_now_add, so they can only be
        # pinned after the fact. Left alone they would be the one place a
        # wall clock leaks into the dataset.
        submitted = _aware(
            spec.start - timedelta(days=self.rng.randint(21, 145)),
            self.rng.randint(8, 21),
            self.rng.choice([0, 7, 14, 23, 31, 42, 55]),
        )
        Registration.objects.filter(pk=registration.pk).update(
            submitted_at=submitted,
            verified_at=submitted + timedelta(minutes=self.rng.randint(2, 400)),
            verification_sent_at=submitted,
        )
        Payment.objects.filter(pk=payment.pk).update(created_at=submitted)
        registration.submitted_at = submitted

        return {
            "spec": spec,
            "event": event,
            "record": record,
            "registration": registration,
            "payment": payment,
            "submitted": submitted,
        }

    def _settle_payments(self):
        """Decide who has paid, who owes, and who paid part.

        Named plants first, then a deterministic random draw of additional
        debtors per event so that no event has a single obvious outstanding
        balance. Everything not chosen is paid in full.
        """
        by_family_event = {
            (r["record"]["family"].id, r["spec"].key): r for r in self.registrations
        }

        outstanding = {}  # registration dict -> Decimal received so far

        def owe(record, event_key, received=Decimal("0")):
            entry = by_family_event[(record["family"].id, event_key)]
            outstanding[id(entry)] = received
            return entry

        # --- named plants ---
        owe(self.plant_nystrom_camp, "camp")
        owe(self.plant_nystrom_weekend, "weekend")
        # A part payment on each of two events, so "they say they paid" is
        # sometimes half true and the correct answer is a number, not a
        # button.
        owe(self.plant_ahlberg, "camp", Decimal("1000"))
        owe(self.plant_ahlberg, "weekend", Decimal("400"))

        # --- filler debtors ---
        for key, count in EXTRA_UNPAID_COUNTS.items():
            pool = [
                r
                for r in self.registrations
                if r["spec"].key == key
                and id(r) not in outstanding
                and r["record"]["family"].last_name not in RESERVED_SURNAMES
            ]
            for entry in self.rng.sample(pool, count):
                outstanding[id(entry)] = Decimal("0")

        for entry in self.registrations:
            payment = entry["payment"]
            spec = entry["spec"]
            submitted = entry["submitted"]

            if id(entry) in outstanding:
                received = outstanding[id(entry)]
                Registration.objects.filter(pk=entry["registration"].pk).update(
                    status=Registration.Status.PENDING_PAYMENT
                )
                if received > 0:
                    self._ledger(payment, received, submitted, "Delbetalning via Swish")
                    payment.method = Payment.Method.SWISH
                    payment.save(update_fields=["method"])
                payment.refresh_from_db()
                payment.recompute_status()
                continue

            paid_on = submitted + timedelta(days=self.rng.randint(0, 9))
            deadline = _aware(spec.start - timedelta(days=14), 23, 59)
            if paid_on > deadline:
                paid_on = deadline
            self._ledger(payment, payment.amount, paid_on, "Betald i sin helhet")
            payment.method = self.rng.choice(
                [Payment.Method.SWISH, Payment.Method.BANKGIRO]
            )
            payment.marked_by = self.admin
            payment.save(update_fields=["method", "marked_by"])
            payment.refresh_from_db()
            # recompute_status() is the domain's own rule, reused rather
            # than reimplemented so the fixture cannot disagree with the
            # application about what "paid" means. It stamps paid_at from
            # the wall clock, which is then overwritten with the fixed
            # date below — the only reason paid_at is touched twice.
            payment.recompute_status()
            Payment.objects.filter(pk=payment.pk).update(paid_at=paid_on)

    def _ledger(self, payment, amount, when, note):
        event_row = PaymentEvent.objects.create(
            id=self._uuid(),
            payment=payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=amount,
            note=note,
            created_by=self.admin,
        )
        PaymentEvent.objects.filter(pk=event_row.pk).update(created_at=when)

    # -- reports -------------------------------------------------------------

    def _build_reports(self):
        """One EventReport snapshot per event, via the real service.

        ``EventReport`` is the aggregate, non-PII snapshot the retention
        pipeline relies on being taken *before* PII purge — see the model's
        own docstring: "anything not captured at generation time cannot be
        recomputed later." A persona fixture that deletes every report and
        creates none leaves "Rapporter -> Evenemangsrapporter" looking like
        a dead feature, which is exactly the failure this method exists to
        prevent. Reused via ``reports.services.generate_event_report``
        rather than reimplemented, for the same reason payments reuse
        ``recompute_status()``: the fixture must not be able to disagree
        with the application about what a report contains.

        ``generated_at`` is ``auto_now_add`` and so, like every other
        auto-stamped column in this fixture, gets overwritten with a fixed
        value afterwards rather than left to the wall clock.
        """
        for spec, event in self.events.values():
            report = generate_event_report(event, user=self.admin)
            EventReport.objects.filter(pk=report.pk).update(
                generated_at=_aware(spec.end + timedelta(days=1), 8)
            )

    # -- verification ------------------------------------------------------

    def _verify(self, *, fail_loudly):
        """Assert the three tasks are still answerable.

        Run automatically after seeding, and available on its own via
        ``--verify-only`` so the next persona run can be checked for
        residue from the previous one without a re-seed.
        """
        problems = []

        # Job 1: exactly two genuinely mis-tiered children. Age at event
        # start is the whole rule now — there is no third "legitimate
        # birthday-crossing" category left to check for, on purpose.
        mismatches = self._mismatch_sweep()
        expected_names = {"Nour Hägglund", "Tuva Sjöberg"}
        found_names = {m["name"] for m in mismatches}
        if found_names != expected_names:
            problems.append(
                f"expected exactly the mis-tiered children "
                f"{sorted(expected_names)}, found {sorted(found_names)}"
            )

        # Job 2: the ticket type to be created must not already exist.
        clash = TicketType.objects.filter(name__iexact=FORBIDDEN_TICKET_TYPE_NAME)
        if clash.exists():
            problems.append(
                f"{FORBIDDEN_TICKET_TYPE_NAME!r} already exists on "
                + ", ".join(t.event.name for t in clash.select_related("event"))
                + " — re-seed before the next persona run"
            )

        # Job 3: outstanding balances on more than one event, at least one
        # part payment, and a surname on two events.
        events_with_debt = set()
        partial = 0
        for payment in Payment.objects.select_related("registration__event"):
            if payment.balance > 0:
                events_with_debt.add(payment.registration.event.name)
            if payment.status == Payment.Status.PARTIALLY_PAID:
                partial += 1
        if len(events_with_debt) < 2:
            problems.append(
                f"outstanding balances exist on only {len(events_with_debt)} event(s)"
            )
        if partial < 1:
            problems.append("no partially-paid registration exists")

        nystrom_events = {
            p.registration.event.name
            for p in Payment.objects.select_related(
                "registration__event", "registration__family"
            ).filter(registration__family__last_name="Nyström")
            if p.balance > 0
        }
        if len(nystrom_events) < 2:
            problems.append(
                "the Nyström surname does not carry an outstanding balance "
                "on two different events"
            )

        # D1: the admin action log must not carry residue from a previous
        # persona's session into a fresh one.
        log_count = LogEntry.objects.count()
        if log_count:
            problems.append(
                f"django_admin_log has {log_count} row(s); a fresh persona "
                "seat would see a previous session's edits as its own"
            )

        # D2: every event must carry a report snapshot, or "Rapporter ->
        # Evenemangsrapporter" reads as a dead feature rather than an
        # unrelated Job 3 (money) surface it was never meant to answer.
        reported_event_ids = set(EventReport.objects.values_list("event_id", flat=True))
        events_without_report = [
            e.name for e in Event.objects.all() if e.id not in reported_event_ids
        ]
        if events_without_report:
            problems.append(
                "no EventReport snapshot exists for: "
                + ", ".join(events_without_report)
            )

        if problems:
            message = "Fixture invariants violated:\n  - " + "\n  - ".join(problems)
            if fail_loudly:
                raise CommandError(message)
            self.stdout.write(self.style.ERROR(message))
        else:
            self.stdout.write(
                self.style.SUCCESS("Fixture invariants hold for all three tasks.")
            )

    def _mismatch_sweep(self):
        """Every EventTicket whose child sits outside their ticket type's
        birthdate window — the sweep a competent coordinator would do.

        Age is judged once, on the event's first day, full stop. There is
        no "ages into the window during the event" exemption: every row
        this returns is a mis-tiering that needs fixing, not a mix of
        errors and legitimate placements.
        """
        from reports.services import age_on

        rows = []
        tickets = EventTicket.objects.select_related(
            "attendee__child", "event", "ticket_type"
        ).exclude(ticket_type__isnull=True)
        for ticket in tickets:
            try:
                child = ticket.attendee.child
            except Child.DoesNotExist:
                continue  # a parent's ticket — no birthdate to check
            if child.birthdate is None:
                continue
            ticket_type = ticket.ticket_type
            if ticket_type.min_birthdate is None and ticket_type.max_birthdate is None:
                continue
            too_old = (
                ticket_type.min_birthdate is not None
                and child.birthdate < ticket_type.min_birthdate
            )
            too_young = (
                ticket_type.max_birthdate is not None
                and child.birthdate > ticket_type.max_birthdate
            )
            if not (too_old or too_young):
                continue

            start = ticket.event.start_date
            age_at_start = age_on(child.birthdate, start)
            rows.append(
                {
                    "name": f"{child.first_name} {child.last_name}",
                    "birthdate": child.birthdate,
                    "event": ticket.event.name,
                    "ticket_type": ticket_type.name,
                    "age_at_start": age_at_start,
                    "label": (
                        f"{child.first_name} {child.last_name} "
                        f"({child.birthdate}, {age_at_start} at start) "
                        f"on {ticket_type.name} / {ticket.event.name}"
                    ),
                }
            )
        return sorted(rows, key=lambda r: r["name"])

    # -- summary -----------------------------------------------------------

    def _report(self):
        out = self.stdout
        out.write("")
        out.write(self.style.MIGRATE_HEADING("Persona fixture seeded"))
        out.write(
            f"  families              {Family.objects.count()}\n"
            f"  parents               {Parent.objects.count()}\n"
            f"  children              {Child.objects.count()}\n"
            f"  events                {Event.objects.count()}\n"
            f"  ticket types          {TicketType.objects.count()}\n"
            f"  registrations         {Registration.objects.count()}\n"
            f"  event tickets         {EventTicket.objects.count()}\n"
            f"  payments              {Payment.objects.count()}\n"
            f"  payment ledger rows   {PaymentEvent.objects.count()}"
        )

        out.write("")
        out.write(self.style.MIGRATE_HEADING("Per event"))
        for spec, event in self.events.values():
            tickets = EventTicket.objects.filter(event=event)
            out.write(f"  {event.name} ({event.start_date} – {event.end_date})")
            for ticket_type in event.ticket_types.order_by("sort_order"):
                count = tickets.filter(ticket_type=ticket_type).count()
                out.write(
                    f"      {ticket_type.name:<20} {ticket_type.price:>8} {count:>5} sold"
                )

        out.write("")
        out.write(self.style.MIGRATE_HEADING("Job 1 — mis-tiered children"))
        for row in self._mismatch_sweep():
            out.write(f"  {'ERROR':<32} {row['label']}")

        out.write("")
        out.write(self.style.MIGRATE_HEADING("Job 3 — outstanding balances"))
        payments = (
            Payment.objects.select_related(
                "registration__event", "registration__family"
            )
            .exclude(status=Payment.Status.PAID)
            .order_by("registration__event__name", "registration__family__last_name")
        )
        for payment in payments:
            out.write(
                f"  {payment.registration.event.name:<20} "
                f"{payment.registration.family.last_name:<16} "
                f"{payment.reference_code}  "
                f"amount {payment.amount:>8}  balance {payment.balance:>8}  "
                f"{payment.status}"
            )
