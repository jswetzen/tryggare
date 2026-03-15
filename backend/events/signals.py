from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Session


@receiver(pre_save, sender=Session)
def stash_previous_is_active(sender, instance, **kwargs):
    """Stash the previous is_active value before save so post_save can detect transitions."""
    if instance.pk:
        try:
            instance._previous_is_active = Session.objects.get(pk=instance.pk).is_active
        except Session.DoesNotExist:
            instance._previous_is_active = None
    else:
        instance._previous_is_active = None


@receiver(post_save, sender=Session)
def auto_checkout_on_deactivate(sender, instance, **kwargs):
    """When a session transitions from active to inactive, auto-check-out all open check-ins."""
    previous_was_active = getattr(instance, '_previous_is_active', True)
    if instance.is_active or not previous_was_active:
        return  # Not a True→False transition

    from checkins.models import CheckInRecord, AuditLog
    from checkins.qr_utils import release_code_for_checkout

    open_records = CheckInRecord.objects.filter(
        session=instance,
        check_out_time__isnull=True,
    ).select_related('child')

    if not open_records.exists():
        return

    now = timezone.now()
    channel_layer = get_channel_layer()

    for record in open_records:
        record.check_out_time = now
        record.check_out_staff = None
        record.picked_up_by = ""
        record.save()
        release_code_for_checkout(record)
        AuditLog.objects.create(
            user=None,
            action="auto_check_out",
            entity_type="CheckInRecord",
            entity_id=str(record.id),
            details={
                "child_id": str(record.child.id),
                "child_name": f"{record.child.first_name} {record.child.last_name}",
                "session_id": str(instance.id),
                "session_name": instance.name,
                "reason": "session_deactivated",
            },
        )
        async_to_sync(channel_layer.group_send)(
            "checkins_broadcast",
            {
                "type": "child_checked_out",
                "data": {
                    "record_id": str(record.id),
                    "child_id": str(record.child.id),
                    "child_name": f"{record.child.first_name} {record.child.last_name}",
                    "session_id": str(instance.id),
                    "session_name": instance.name,
                    "check_out_time": record.check_out_time.isoformat(),
                    "picked_up_by": "",
                },
            },
        )

    # Broadcast session_ended after all checkouts
    async_to_sync(channel_layer.group_send)(
        "checkins_broadcast",
        {
            "type": "session_ended",
            "data": {
                "session_id": str(instance.id),
                "session_name": instance.name,
            },
        },
    )
