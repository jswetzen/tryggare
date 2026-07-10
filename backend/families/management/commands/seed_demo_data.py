"""
Management command to seed realistic demo data for screenshots and development.
Idempotent — safe to re-run (uses get_or_create throughout).
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from checkins.models import AuditLog, CheckInRecord, QRCode
from events.models import (
    AppliesTo,
    Event,
    EventTicket,
    Extra,
    ExtraChoice,
    Session,
    SessionTicket,
    Ticket,
    TicketType,
)
from families.models import Child, Family, Parent
from registrations.models import Payment, Registration
from registrations.tokens import generate_verification_token, hash_token


class Command(BaseCommand):
    help = "Seed realistic demo data for development and screenshots"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Wipe all family/event/check-in data (and the 'maria' staff user) before seeding. "
            "For demo sites that reset on every container restart.",
        )

    def handle(self, *args, **options):
        AdminUser = get_user_model()

        if options["reset"]:
            self.stdout.write(
                self.style.WARNING(
                    "Resetting demo data (wiping families, events, check-ins)..."
                )
            )
            # Order matters: delete children/leaves before parents to avoid FK issues,
            # though Django CASCADE handles most of it.
            AuditLog.objects.all().delete()
            QRCode.objects.all().delete()
            CheckInRecord.objects.all().delete()
            SessionTicket.objects.all().delete()
            EventTicket.objects.all().delete()
            Ticket.objects.all().delete()
            Child.objects.all().delete()
            Parent.objects.all().delete()
            Family.objects.all().delete()
            Session.objects.all().delete()
            Event.objects.all().delete()
            AdminUser.objects.filter(username="maria").delete()

        # --- Staff users ---
        admin, created = AdminUser.objects.get_or_create(
            username="admin",
            defaults={"name": "Admin User", "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password("admin123")
            admin.save()
            self.stdout.write("Created admin user")
        elif not admin.check_password("admin123"):
            admin.set_password("admin123")
            admin.save()

        maria, created = AdminUser.objects.get_or_create(
            username="maria",
            defaults={
                "name": "Maria Lindqvist",
                "is_staff": True,
                "is_superuser": False,
            },
        )
        if created:
            maria.set_password("demo123")
            maria.save()
            self.stdout.write("Created staff user 'maria'")

        # --- Event & Sessions ---
        today = date.today()
        event, _ = Event.objects.get_or_create(
            name="Spring Conference 2026",
            defaults={"start_date": today, "end_date": today + timedelta(days=1)},
        )

        morning_start = timezone.now().replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        morning_end = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)
        morning, _ = Session.objects.get_or_create(
            event=event,
            name="Morning Session",
            defaults={
                "start_time": morning_start,
                "end_time": morning_end,
                "is_active": True,
                "requires_ticket": False,
            },
        )

        afternoon_start = timezone.now().replace(
            hour=13, minute=0, second=0, microsecond=0
        )
        afternoon_end = timezone.now().replace(
            hour=16, minute=0, second=0, microsecond=0
        )
        Session.objects.get_or_create(
            event=event,
            name="Afternoon Session",
            defaults={
                "start_time": afternoon_start,
                "end_time": afternoon_end,
                "is_active": False,
                "requires_ticket": False,
            },
        )

        # --- Families ---
        # (last_name, parent_name, relationship, phone, email,
        #  [(first_name, age, allergies, notes)])
        family_data = [
            (
                "Andersson",
                "Sara Andersson",
                "Mother",
                "+46701234567",
                "sara.andersson@example.com",
                [
                    ("Emma", 9, None, None),
                    ("Liam", 6, None, None),
                ],
            ),
            (
                "Bergström",
                "Per Bergström",
                "Father",
                "+46702345678",
                "per.bergstrom@example.com",
                [
                    ("Olivia", 11, None, None),
                ],
            ),
            (
                "Chen",
                "Wei Chen",
                "Mother",
                "+46703456789",
                "wei.chen@example.com",
                [
                    ("Lucas", 7, None, None),
                    ("Mia", 5, None, None),
                ],
            ),
            (
                "Dahl",
                "Ingrid Dahl",
                "Mother",
                "+46704567890",
                "ingrid.dahl@example.com",
                [
                    ("Noah", 8, "Peanuts", None),
                ],
            ),
            (
                "Eriksson",
                "Johan Eriksson",
                "Father",
                "+46705678901",
                "johan.eriksson@example.com",
                [
                    ("Saga", 10, None, None),
                    ("Felix", 4, None, None),
                ],
            ),
            (
                "Flores",
                "Carmen Flores",
                "Mother",
                "+46706789012",
                "carmen.flores@example.com",
                [
                    ("Sofia", 7, None, None),
                ],
            ),
            (
                "Gustafsson",
                "Gunnar Gustafsson",
                "Father",
                "+46707890123",
                "gunnar.gustafsson@example.com",
                [
                    ("Elias", 6, None, None),
                    ("Wilma", 9, None, None),
                    ("Axel", 12, None, None),
                ],
            ),
            (
                "Hansen",
                "Anna Hansen",
                "Mother",
                "+46708901234",
                "anna.hansen@example.com",
                [
                    ("Astrid", 8, None, "Needs extra supervision"),
                ],
            ),
        ]

        families = {}
        children = {}

        for last_name, parent_name, rel, phone, email, kids in family_data:
            family, _ = Family.objects.get_or_create(last_name=last_name)
            families[last_name] = family
            parts = parent_name.split(" ", 1)
            p_first = parts[0]
            p_last = parts[1] if len(parts) > 1 else ""
            Parent.objects.get_or_create(
                family=family,
                first_name=p_first,
                last_name=p_last,
                defaults={"relationship_type": rel, "phone": phone, "email": email},
            )
            for first_name, age, allergies, notes in kids:
                birthdate = today.replace(year=today.year - age)
                child, _ = Child.objects.get_or_create(
                    family=family,
                    first_name=first_name,
                    last_name=last_name,
                    defaults={
                        "birthdate": birthdate,
                        "allergies": allergies,
                        "notes": notes,
                    },
                )
                children[(first_name, last_name)] = child

        # --- Tickets (all children get a Morning Session ticket) ---
        for child in children.values():
            SessionTicket.objects.get_or_create(attendee=child, session=morning)

        # --- Check-ins for Morning Session ---
        # (first_name, last_name, staff_user, hour, minute)
        checkin_data = [
            ("Emma", "Andersson", admin, 8, 52),
            ("Liam", "Andersson", admin, 8, 52),
            ("Olivia", "Bergström", maria, 9, 5),
            ("Lucas", "Chen", admin, 9, 11),
            ("Noah", "Dahl", maria, 9, 18),
            ("Sofia", "Flores", admin, 9, 23),
            ("Elias", "Gustafsson", admin, 9, 31),
            ("Wilma", "Gustafsson", admin, 9, 31),
            ("Axel", "Gustafsson", maria, 9, 34),
        ]

        checkin_records = []
        for first_name, last_name, staff, hour, minute in checkin_data:
            child = children[(first_name, last_name)]
            record, created = CheckInRecord.objects.get_or_create(
                attendee=child,
                session=morning,
                defaults={"check_in_staff": staff},
            )
            if created:
                checkin_records.append((record, hour, minute))

        # Backdate check_in_time (auto_now_add can't be set on save, use update)
        for record, hour, minute in checkin_records:
            checkin_time = timezone.now().replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            CheckInRecord.objects.filter(pk=record.pk).update(
                check_in_time=checkin_time
            )

        # --- QR codes for checked-in children ---
        import random
        import string

        def random_code():
            return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

        all_records = CheckInRecord.objects.filter(session=morning)
        for record in all_records:
            if not hasattr(record, "qr_code") or record.qr_code is None:
                try:
                    code = random_code()
                    while QRCode.objects.filter(code=code).exists():
                        code = random_code()
                    QRCode.objects.get_or_create(
                        checkin_record=record,
                        defaults={"code": code, "allocated_at": timezone.now()},
                    )
                except Exception:
                    pass  # QR code already exists

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data seeded: {len(children)} children in {len(families)} families, "
                f"{len(checkin_data)} checked in to Morning Session."
            )
        )

        self._seed_unpaid_registration_demo_family(event, morning)
        self._seed_registration_demo_event()

    def _seed_unpaid_registration_demo_family(self, event, session):
        """A ninth Spring Conference 2026 family, arrived via self-serve
        registration but not yet paid — showcases the check-in screen's
        "unpaid at the door" banner (case catalog §9.3) without a staff
        member having to submit a real registration first. Distinct from
        every other seed family here: this one has a real Registration/
        Payment pair and a ticket whose registration FK is set, so both
        halves of the feature are demoable out of the box — the amber
        banner with the amount owed, and the check-in gate actually
        blocking the child until staff use "Ta betalt nu" (or the
        override) to clear it.
        """
        family, _ = Family.objects.get_or_create(last_name="Karlsson")
        Parent.objects.get_or_create(
            family=family,
            first_name="Nina",
            last_name="Karlsson",
            defaults={
                "relationship_type": "Mother",
                "phone": "+46709012345",
                "email": "nina.karlsson@example.com",
            },
        )
        today = date.today()
        child, _ = Child.objects.get_or_create(
            family=family,
            first_name="Alice",
            last_name="Karlsson",
            defaults={"birthdate": today.replace(year=today.year - 8)},
        )

        registration, reg_created = Registration.objects.get_or_create(
            event=event,
            family=family,
            contact_email="nina.karlsson@example.com",
            defaults={
                "status": Registration.Status.PENDING_PAYMENT,
                "verification_token_hash": hash_token(generate_verification_token()),
            },
        )
        if reg_created:
            Payment.objects.create(registration=registration, amount=Decimal("500.00"))

        SessionTicket.objects.get_or_create(
            attendee=child, session=session, defaults={"registration": registration}
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Unpaid registration demo family seeded: Karlsson "
                "(500.00 SEK owed, blocks check-in until paid)."
            )
        )

    def _seed_registration_demo_event(self):
        """A second, separate event configured (not populated with
        registrations — those are meant to be created live via the public
        /register/[eventId] form) to showcase self-serve registration's
        itemized ticket types and extras as completely as one event
        reasonably can: birthdate-tiered pricing, a hidden volunteer
        ticket, a session-scoped extra with dietary choices, a
        must-choose-one extra, an opt-out-by-default extra, and a
        per-registration (shared cabin) extra with quantity.
        """
        today = date.today()
        camp, _ = Event.objects.get_or_create(
            name="Sommarläger 2026",
            defaults={
                "start_date": today + timedelta(days=30),
                "end_date": today + timedelta(days=32),
            },
        )
        # Self-serve registration is closed by default (see
        # Event.registration_window_status) — demo/seed events opt in
        # explicitly so the public form stays reachable for testing. Set
        # unconditionally (not just in `defaults`) so a re-run against a
        # dev DB seeded before this field existed still opens it.
        if camp.registration_opens_at is None:
            camp.registration_opens_at = timezone.now() - timedelta(days=1)
            camp.save(update_fields=["registration_opens_at"])

        session_defs = [
            ("Fredag", 0, 16, 22),
            ("Lördag", 1, 8, 22),
            ("Söndag", 2, 8, 14),
        ]
        camp_sessions = {}
        for name, day_offset, start_hour, end_hour in session_defs:
            day = camp.start_date + timedelta(days=day_offset)
            session, _ = Session.objects.get_or_create(
                event=camp,
                name=name,
                defaults={
                    "start_time": timezone.make_aware(
                        timezone.datetime.combine(
                            day, timezone.datetime.min.time()
                        ).replace(hour=start_hour)
                    ),
                    "end_time": timezone.make_aware(
                        timezone.datetime.combine(
                            day, timezone.datetime.min.time()
                        ).replace(hour=end_hour)
                    ),
                    "is_active": False,
                },
            )
            camp_sessions[name] = session

        # --- Ticket types: birthdate-tiered pricing (case 2.2) + a hidden
        # volunteer type unlocked only via a direct link (case 5.4/10.2) ---
        TicketType.objects.get_or_create(
            event=camp,
            name="Barn (0-12 år)",
            defaults={
                "price": 400,
                "applies_to": AppliesTo.CHILD,
                "min_birthdate": camp.start_date.replace(
                    year=camp.start_date.year - 12
                ),
                "max_birthdate": camp.start_date,
                "sort_order": 1,
            },
        )
        TicketType.objects.get_or_create(
            event=camp,
            name="Ungdom (13-17 år)",
            defaults={
                "price": 700,
                "applies_to": AppliesTo.CHILD,
                "min_birthdate": camp.start_date.replace(
                    year=camp.start_date.year - 17
                ),
                "max_birthdate": camp.start_date.replace(
                    year=camp.start_date.year - 13
                ),
                "sort_order": 2,
            },
        )
        TicketType.objects.get_or_create(
            event=camp,
            name="Vuxen",
            defaults={
                "price": 1100,
                "applies_to": AppliesTo.PARENT,
                "sort_order": 3,
            },
        )
        TicketType.objects.get_or_create(
            event=camp,
            name="Ledare",
            defaults={
                "price": 0,
                "applies_to": AppliesTo.EITHER,
                "is_hidden": True,
                "sort_order": 4,
            },
        )

        # --- Extras ---
        # Session-scoped, with a structured dietary choice (case 3.1/3.2) —
        # a kitchen-facing choice, never a disclosed health condition.
        dinner, _ = Extra.objects.get_or_create(
            event=camp,
            name="Lördagsmiddag",
            defaults={
                "session": camp_sessions["Lördag"],
                "price": 150,
                "per_attendee": True,
                "applies_to": AppliesTo.EITHER,
                "requires_choice": True,
            },
        )
        for label, sort_order in [
            ("Vanlig", 0),
            ("Vegetarisk", 1),
            ("Vegansk", 2),
            ("Glutenfri", 3),
        ]:
            ExtraChoice.objects.get_or_create(
                extra=dinner, label=label, defaults={"sort_order": sort_order}
            )

        # Plain choice extra, no session scope.
        shirt, _ = Extra.objects.get_or_create(
            event=camp,
            name="T-shirt",
            defaults={
                "price": 100,
                "per_attendee": True,
                "applies_to": AppliesTo.EITHER,
                "requires_choice": True,
            },
        )
        for label, sort_order in [("S", 0), ("M", 1), ("L", 2), ("XL", 3)]:
            ExtraChoice.objects.get_or_create(
                extra=shirt, label=label, defaults={"sort_order": sort_order}
            )

        # Must-choose-one extra (case 3.2's `required` field — renders as
        # radio, not an optional checkbox).
        accommodation, _ = Extra.objects.get_or_create(
            event=camp,
            name="Boende",
            defaults={
                "price": 0,
                "per_attendee": True,
                "applies_to": AppliesTo.EITHER,
                "requires_choice": True,
                "required": True,
            },
        )
        for label, sort_order in [("Tält (eget)", 0), ("Stuga", 1), ("Bor hemma", 2)]:
            ExtraChoice.objects.get_or_create(
                extra=accommodation, label=label, defaults={"sort_order": sort_order}
            )

        # Opt-out-by-default extra (case 2.1) — meals included unless the
        # guardian actively declines, never modeled as a negative price.
        Extra.objects.get_or_create(
            event=camp,
            name="Måltider hela helgen",
            defaults={
                "price": 300,
                "per_attendee": True,
                "applies_to": AppliesTo.EITHER,
                "default_selected": True,
            },
        )

        # Per-registration extra with quantity (case 3.3) — one shared
        # cabin per family, not per attendee.
        Extra.objects.get_or_create(
            event=camp,
            name="Delat boende (stuga) - extra bäddar",
            defaults={
                "price": 300,
                "per_attendee": False,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Registration demo event seeded: 'Sommarläger 2026' "
                "(4 ticket types, 5 extras) — register at /register/"
                f"{camp.id}"
            )
        )

        self._seed_church_weekend_demo_event()

    def _seed_church_weekend_demo_event(self):
        """A real-world reproduction of a live ChurchSuite event
        ("Weekend 2026", brokyrkan.churchsuite.com/events/sp1vw0ma),
        modeled as faithfully as this system currently allows — see the
        conversation this was built from for the full comparison. Two
        deliberate improvements over the original: the "VIP" special-
        arrangement ticket is hidden (case 5.4/10.2) rather than publicly
        listed on the honor system, and payment reconciliation uses this
        system's per-registration reference code instead of one static
        Swish message shared by every family. One deliberate gap, noted
        rather than faked: ChurchSuite's "which tent/room" question is
        only shown/required if the guardian said they're staying
        overnight — conditional-required fields aren't a case this system
        has a story for yet, so both accommodation questions render
        unconditionally required here.
        """
        today = date.today()
        weekend, _ = Event.objects.get_or_create(
            name="Weekend 2026",
            defaults={
                "start_date": today + timedelta(days=60),
                "end_date": today + timedelta(days=62),
            },
        )
        if weekend.registration_opens_at is None:
            weekend.registration_opens_at = timezone.now() - timedelta(days=1)
            weekend.save(update_fields=["registration_opens_at"])

        TicketType.objects.get_or_create(
            event=weekend,
            name="All inclusive",
            defaults={
                "price": 600,
                "applies_to": AppliesTo.EITHER,
                "sort_order": 1,
            },
        )
        TicketType.objects.get_or_create(
            event=weekend,
            name="0-6 år",
            defaults={
                "price": 0,
                "applies_to": AppliesTo.CHILD,
                "min_birthdate": weekend.start_date.replace(
                    year=weekend.start_date.year - 6
                ),
                "max_birthdate": weekend.start_date,
                "sort_order": 2,
            },
        )
        TicketType.objects.get_or_create(
            event=weekend,
            name="Familjebiljett",
            defaults={
                "price": 2000,
                "applies_to": AppliesTo.EITHER,
                "sort_order": 3,
            },
        )
        TicketType.objects.get_or_create(
            event=weekend,
            name="Familjebiljett - familjemedlem",
            defaults={
                "price": 0,
                "applies_to": AppliesTo.EITHER,
                "sort_order": 4,
            },
        )
        # ChurchSuite lists this publicly, trusting guests not to pick it
        # without a real arrangement — hidden here instead (case 5.4/10.2).
        TicketType.objects.get_or_create(
            event=weekend,
            name="VIP",
            defaults={
                "price": 0,
                "applies_to": AppliesTo.EITHER,
                "is_hidden": True,
                "sort_order": 5,
            },
        )

        Extra.objects.get_or_create(
            event=weekend,
            name="Övernattning",
            defaults={
                "price": 0,
                "per_attendee": True,
                "applies_to": AppliesTo.EITHER,
                "requires_choice": True,
                "required": True,
            },
        )
        overnight = Extra.objects.get(event=weekend, name="Övernattning")
        for label, sort_order in [
            ("Nej", 0),
            ("Fredag - Lördag", 1),
            ("Lördag - Söndag", 2),
            ("Båda nätterna", 3),
        ]:
            ExtraChoice.objects.get_or_create(
                extra=overnight, label=label, defaults={"sort_order": sort_order}
            )

        # Genuinely only relevant if `overnight` != "Nej" — ChurchSuite
        # marks it unconditionally required too, so this isn't a
        # regression, but it's still the gap worth naming: this system has
        # no conditional-required mechanism.
        Extra.objects.get_or_create(
            event=weekend,
            name="Boendeform",
            defaults={
                "price": 0,
                "per_attendee": True,
                "applies_to": AppliesTo.EITHER,
                "requires_choice": True,
                "required": True,
            },
        )
        accommodation_kind = Extra.objects.get(event=weekend, name="Boendeform")
        for label, sort_order in [
            ("Husvagn/husbil", 0),
            ("Tält", 1),
            ("Rum", 2),
            ("Annat", 3),
        ]:
            ExtraChoice.objects.get_or_create(
                extra=accommodation_kind,
                label=label,
                defaults={"sort_order": sort_order},
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Registration demo event seeded: 'Weekend 2026' "
                "(5 ticket types, 2 required extras) — register at "
                f"/register/{weekend.id}"
            )
        )
