import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from checkins.models import AuditLog, CheckInRecord
from events.models import Event, Session, Ticket
from families.models import Child, Family, Parent


class Command(BaseCommand):
    help = "Seed sample data for local development"

    def handle(self, *args, **options):
        AdminUser = get_user_model()
        admin_user, created = AdminUser.objects.get_or_create(
            username="admin",
            defaults={"name": "Admin User", "is_staff": True, "is_superuser": True},
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created default admin user 'admin' with password 'admin123'"))

        seed_family_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        family, _ = Family.objects.get_or_create(id=seed_family_id)
        Parent.objects.get_or_create(
            family=family,
            name="Alex Parent",
            relationship_type="Guardian",
            defaults={"email": "alex@example.com", "phone": "+10000000000"},
        )
        child, _ = Child.objects.get_or_create(
            family=family,
            first_name="Jamie",
            last_name="River",
            birthdate=timezone.now().date().replace(year=timezone.now().year - 7),
            defaults={"qr_token": None},
        )

        event, _ = Event.objects.get_or_create(
            name="Community Event",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        session, _ = Session.objects.get_or_create(
            event=event,
            name="Morning Session",
            defaults={
                "start_time": timezone.now(),
                "end_time": timezone.now() + timezone.timedelta(hours=2),
                "is_active": True,
                "requires_ticket": False,
            },
        )

        Ticket.objects.get_or_create(child=child, session=session, defaults={"type": Ticket.SESSION_TICKET})

        checkin, _ = CheckInRecord.objects.get_or_create(
            child=child,
            session=session,
            check_in_staff=admin_user,
            defaults={"picked_up_by": "Alex"},
        )

        AuditLog.objects.get_or_create(
            action="CHECK_IN",
            entity_type="Child",
            entity_id=str(child.id),
            user=admin_user,
            defaults={"details": {"session": str(session.id), "check_in_id": str(checkin.id)}},
        )

        self.stdout.write(self.style.SUCCESS("Seed data ensured."))
