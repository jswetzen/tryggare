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
alone. This syncs the group relation; it does not police the column. That is
also why the ``post_clear`` handling below goes to the trouble of remembering
who was in the group rather than simply demoting everyone still flagged
``is_staff``: the second would police the column, and would quietly strip a
flag somebody set on purpose by another route.
"""

from django.db.models.signals import m2m_changed

from .roles import ADMINISTRATOR

# The pks stashed by ``pre_clear`` are hung on the Group instance under this
# name. Django's own m2m_changed docs suggest exactly this pattern: by the time
# ``post_clear`` fires the join rows are gone, so the only chance to learn who
# was affected is before the delete.
_CLEARED_PKS = "_sync_is_staff_cleared_user_pks"


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
    if action not in ("pre_clear", "post_add", "post_remove", "post_clear"):
        return

    from django.contrib.auth.models import Group

    from .models import AdminUser

    if reverse:
        # ``group.user_set.add(user, ...)`` — ``instance`` is the Group.
        if getattr(instance, "name", None) != ADMINISTRATOR:
            return
        if action == "pre_clear":
            # ``group.user_set.clear()``. Per Django's m2m_changed contract
            # ``pk_set`` is None for both pre_clear and post_clear, so the
            # membership has to be read now — a moment later the rows are gone
            # and there is no way to tell whose ``is_staff`` went stale.
            setattr(
                instance,
                _CLEARED_PKS,
                list(instance.user_set.values_list("pk", flat=True)),
            )
            return
        if action == "post_clear":
            pk_set = getattr(instance, _CLEARED_PKS, None) or []
            # Don't let a stale list survive to a second clear on the same
            # in-memory Group.
            if hasattr(instance, _CLEARED_PKS):
                delattr(instance, _CLEARED_PKS)
        users = list(AdminUser.objects.filter(pk__in=pk_set or []))
    else:
        # ``user.groups.add(group, ...)`` — ``instance`` is the AdminUser.
        # Forward clears need no stash: ``instance`` is the one user affected,
        # and ``post_clear`` alone is enough to recompute them.
        if action == "pre_clear":
            return
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
