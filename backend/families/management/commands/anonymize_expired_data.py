"""
GDPR retention command.

Anonymises PII on families that have been inactive (by ``last_participation_date``)
for longer than ``DATA_RETENTION_DAYS``. PII is scrubbed in place — rows,
timestamps and foreign keys are kept so attendance/safeguarding aggregates stay
intact. Families with an active (not-checked-out) check-in are never touched.

This runs automatically once a day at 03:00 via an in-app scheduler (see
``families.apps.FamiliesConfig.ready()`` / ``families.tasks.run_scheduled_retention``),
so no operator-configured cron is required. It can still be invoked manually,
e.g. for an out-of-band run or to pass ``--dry-run``/``--days`` overrides:

    cd /app/backend && python manage.py anonymize_expired_data --dry-run

Use ``--dry-run`` first to see what would be affected.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from checkins.models import AuditLog, CheckInRecord
from families.dsar import scrub_audit_logs_for_children, scrub_family
from families.models import Child, Family


class Command(BaseCommand):
    help = (
        "Anonymize PII on families inactive longer than DATA_RETENTION_DAYS "
        "(GDPR retention). Use --dry-run to preview."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be anonymized without writing anything.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Override DATA_RETENTION_DAYS for this run.",
        )
        parser.add_argument(
            "--include-audit-logs",
            action="store_true",
            help=(
                "Also delete AuditLog rows older than AUDIT_LOG_RETENTION_DAYS "
                "(audit logs otherwise grow indefinitely)."
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        days = (
            options["days"]
            if options["days"] is not None
            else settings.DATA_RETENTION_DAYS
        )
        now = timezone.now()
        cutoff = now - timedelta(days=days)

        # Candidates: inactive past the cutoff, not already anonymized, and with
        # no active (not-checked-out) check-in for any child. We use an Exists
        # subquery rather than an exclude() across the join, because a join-based
        # exclude would also drop families whose children simply have no check-in
        # records at all (their NULL check_out_time matching isnull=True).
        active_checkin = CheckInRecord.objects.filter(
            child__family=OuterRef("pk"), check_out_time__isnull=True
        )
        candidates = Family.objects.filter(
            last_participation_date__lt=cutoff,
            anonymized_at__isnull=True,
        ).exclude(Exists(active_checkin))

        family_count = candidates.count()
        child_ids = list(
            Child.objects.filter(family__in=candidates).values_list("id", flat=True)
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[dry-run] Would anonymize {family_count} families "
                    f"(inactive before {cutoff.date()}, {len(child_ids)} children)."
                )
            )
            if options["include_audit_logs"]:
                audit_cutoff = now - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
                audit_count = AuditLog.objects.filter(
                    timestamp__lt=audit_cutoff
                ).count()
                self.stdout.write(
                    self.style.WARNING(
                        f"[dry-run] Would delete {audit_count} audit logs "
                        f"older than {audit_cutoff.date()}."
                    )
                )
            return

        audit_logs_scrubbed = 0
        audit_logs_deleted = 0
        with transaction.atomic():
            for family in candidates:
                family_child_ids = [str(c.id) for c in family.children.all()]
                scrub_family(family, when=now)
                audit_logs_scrubbed += scrub_audit_logs_for_children(family_child_ids)

            if options["include_audit_logs"]:
                audit_cutoff = now - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
                audit_logs_deleted, _ = AuditLog.objects.filter(
                    timestamp__lt=audit_cutoff
                ).delete()

            # Record the batch operation itself (system action, no user).
            AuditLog.objects.create(
                user=None,
                action="anonymize_retention",
                entity_type="Family",
                entity_id="batch",
                details={
                    "families_anonymized": family_count,
                    "children_anonymized": len(child_ids),
                    "audit_logs_scrubbed": audit_logs_scrubbed,
                    "audit_logs_deleted": audit_logs_deleted,
                    "cutoff": cutoff.isoformat(),
                    "retention_days": days,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Anonymized {family_count} families ({len(child_ids)} children), "
                f"scrubbed {audit_logs_scrubbed} audit logs, "
                f"deleted {audit_logs_deleted} expired audit logs."
            )
        )
