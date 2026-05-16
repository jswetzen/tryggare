"""
Management command to seed realistic demo data for screenshots and development.
Idempotent — safe to re-run (uses get_or_create throughout).
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from checkins.models import AuditLog, CheckInRecord, QRCode
from events.models import Event, EventTicket, Session, SessionTicket, Ticket
from families.models import Child, Family, Parent


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
            self.stdout.write(self.style.WARNING("Resetting demo data (wiping families, events, check-ins)..."))
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
            defaults={"name": "Maria Lindqvist", "is_staff": True, "is_superuser": False},
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

        morning_start = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
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

        afternoon_start = timezone.now().replace(hour=13, minute=0, second=0, microsecond=0)
        afternoon_end = timezone.now().replace(hour=16, minute=0, second=0, microsecond=0)
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
                "Sara Andersson", "Mother", "+46701234567", "sara.andersson@example.com",
                [
                    ("Emma", 9, None, None),
                    ("Liam", 6, None, None),
                ],
            ),
            (
                "Bergström",
                "Per Bergström", "Father", "+46702345678", "per.bergstrom@example.com",
                [
                    ("Olivia", 11, None, None),
                ],
            ),
            (
                "Chen",
                "Wei Chen", "Mother", "+46703456789", "wei.chen@example.com",
                [
                    ("Lucas", 7, None, None),
                    ("Mia", 5, None, None),
                ],
            ),
            (
                "Dahl",
                "Ingrid Dahl", "Mother", "+46704567890", "ingrid.dahl@example.com",
                [
                    ("Noah", 8, "Peanuts", None),
                ],
            ),
            (
                "Eriksson",
                "Johan Eriksson", "Father", "+46705678901", "johan.eriksson@example.com",
                [
                    ("Saga", 10, None, None),
                    ("Felix", 4, None, None),
                ],
            ),
            (
                "Flores",
                "Carmen Flores", "Mother", "+46706789012", "carmen.flores@example.com",
                [
                    ("Sofia", 7, None, None),
                ],
            ),
            (
                "Gustafsson",
                "Gunnar Gustafsson", "Father", "+46707890123", "gunnar.gustafsson@example.com",
                [
                    ("Elias", 6, None, None),
                    ("Wilma", 9, None, None),
                    ("Axel", 12, None, None),
                ],
            ),
            (
                "Hansen",
                "Anna Hansen", "Mother", "+46708901234", "anna.hansen@example.com",
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
            Parent.objects.get_or_create(
                family=family,
                name=parent_name,
                defaults={"relationship_type": rel, "phone": phone, "email": email},
            )
            for first_name, age, allergies, notes in kids:
                birthdate = today.replace(year=today.year - age)
                child, _ = Child.objects.get_or_create(
                    family=family,
                    first_name=first_name,
                    last_name=last_name,
                    defaults={"birthdate": birthdate, "allergies": allergies, "notes": notes},
                )
                children[(first_name, last_name)] = child

        # --- Tickets (all children get a Morning Session ticket) ---
        for child in children.values():
            SessionTicket.objects.get_or_create(child=child, session=morning)

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
                child=child,
                session=morning,
                defaults={"check_in_staff": staff},
            )
            if created:
                checkin_records.append((record, hour, minute))

        # Backdate check_in_time (auto_now_add can't be set on save, use update)
        for record, hour, minute in checkin_records:
            checkin_time = timezone.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            CheckInRecord.objects.filter(pk=record.pk).update(check_in_time=checkin_time)

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

        self.stdout.write(self.style.SUCCESS(
            f"Demo data seeded: {len(children)} children in {len(families)} families, "
            f"{len(checkin_data)} checked in to Morning Session."
        ))
