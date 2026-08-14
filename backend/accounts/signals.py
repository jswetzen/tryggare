"""Keep ``is_staff`` in step with membership of the Administratör group.

Under the settled role design ``is_staff`` has exactly one meaning — "can reach
Django admin" — and exactly one role carries it. But ``is_staff`` is a column on
the user, and a Group cannot set a column. Without this, adding somebody to
Administratör in the admin does nothing observable: they log in, see the same
app as a Koordinator, and get bounced from ``/admin/`` with no explanation. The
operator's only clue would be a second checkbox they had no reason to connect
to the group they just picked.

So membership drives the flag:

* added to Administratör -> ``is_staff = True``
* removed from Administratör -> ``is_staff = False``, unless the user is a
  superuser (ours) or is still in Administratör by some other route.

The removal direction is the deliberate half. It means "revoke the admin role"
actually revokes admin access, rather than leaving a stale ``is_staff`` behind
that nobody thinks to clear. That is only safe because ``is_staff`` no longer
means anything else: every app-tier grant that used to ride on it now rides on
a permission instead.

One deliberate gap: ``is_staff`` set directly in a shell or a fixture is left
alone. This syncs the group relation; it does not police the column.
"""

from django.db.models.signals import m2m_changed

from .roles import ADMINISTRATOR


def connect(app_config):
    """Wire the receiver to the AdminUser<->Group through model."""
    AdminUser = app_config.get_model("AdminUser")
    m2m_changed.connect(
        sync_is_staff_with_administrator_group,
        sender=AdminUser.groups.through,
        dispatch_uid="accounts.sync_is_staff_with_administrator_group",
    )


def sync_is_staff_with_administrator_group(
    sender, instance, action, reverse, pk_set, **kwargs
):
    if action not in ("post_add", "post_remove", "post_clear"):
        return

    from django.contrib.auth.models import Group

    from .models import AdminUser

    if reverse:
        # ``group.user_set.add(user, ...)`` — ``instance`` is the Group.
        if getattr(instance, "name", None) != ADMINISTRATOR:
            return
        users = list(AdminUser.objects.filter(pk__in=pk_set or []))
    else:
        # ``user.groups.add(group, ...)`` — ``instance`` is the AdminUser.
        # ``post_clear`` carries no pk_set, so it always has to be considered.
        if pk_set is not None:
            touched = Group.objects.filter(pk__in=pk_set, name=ADMINISTRATOR)
            if not touched.exists():
                return
        users = [instance]

    for user in users:
        if user.is_superuser:
            continue
        should_be_staff = user.groups.filter(name=ADMINISTRATOR).exists()
        if user.is_staff != should_be_staff:
            user.is_staff = should_be_staff
            user.save(update_fields=["is_staff"])
