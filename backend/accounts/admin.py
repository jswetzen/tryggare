"""User and group administration, with the escalation paths closed.

Administratör is a customer-facing role: it is ``is_staff``, it reaches Django
admin, and it manages the organisation's own accounts and groups. That is the
point — an organisation must be able to add a volunteer, or compose a fourth
role, without us. But the same screens are, by default, three separate routes
straight to superuser:

1. ``AdminUserAdmin`` renders ``is_superuser`` as an ordinary checkbox.
2. ``AdminUserAdmin`` renders ``user_permissions`` (and ``groups``) as a picker
   over *every* permission in the system — including ``delete_auditlog`` and
   ``add_printer``, the two grants the role definition explicitly withholds.
3. ``GroupAdmin`` does the same for a group the editor can then join.

A Django model permission cannot express "this field but not that one", so
these have to be closed in the admin classes. The rule applied throughout is
the standard one: **a non-superuser may never grant a permission they do not
themselves hold, and may never edit a superuser.** With that in place the
"three things no role gets" list in ``accounts/roles.py`` is enforced rather
than merely intended — an Administratör cannot route around it by writing
themselves a fourth group.
"""

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, Permission
from django.db.models import Value
from django.db.models.functions import Concat

from .models import AdminUser


def permissions_held_by(user):
    """The Permission rows ``user`` actually holds, as a queryset.

    ``get_all_permissions()`` returns ``"app_label.codename"`` strings; the
    label is rebuilt in SQL so this is one query rather than an OR over ~150
    Q objects.
    """
    held = user.get_all_permissions()
    return (
        Permission.objects.annotate(
            _label=Concat("content_type__app_label", Value("."), "codename")
        )
        .filter(_label__in=held)
        .select_related("content_type")
    )


def groups_assignable_by(user):
    """Groups whose permission set is a subset of what ``user`` already holds.

    Deliberately *not* "groups the user is a member of": an Administratör is
    not in the Volontär group and still has to be able to put people in it.
    Subset-of-my-own-permissions allows that while keeping the grant from being
    an escalation.
    """
    held = user.get_all_permissions()
    assignable = [
        group.pk
        for group in Group.objects.prefetch_related("permissions__content_type")
        if {
            f"{perm.content_type.app_label}.{perm.codename}"
            for perm in group.permissions.all()
        }
        <= held
    ]
    return Group.objects.filter(pk__in=assignable)


class NoEscalationAdminMixin:
    """Confines a non-superuser's grants to permissions they already hold."""

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name in ("permissions", "user_permissions"):
                kwargs["queryset"] = permissions_held_by(request.user)
            elif db_field.name == "groups":
                kwargs["queryset"] = groups_assignable_by(request.user)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(AdminUser)
class AdminUserAdmin(NoEscalationAdminMixin, UserAdmin):
    model = AdminUser
    list_display = ("username", "name", "is_staff", "is_active", "last_login")
    list_filter = ("is_staff", "is_active", "groups")
    ordering = ("username",)
    search_fields = ("username", "name")

    fieldsets = (
        (None, {"fields": ("username", "password", "name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "created_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "name",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    @staticmethod
    def _without_superuser(fieldsets):
        return tuple(
            (
                title,
                {
                    **options,
                    "fields": tuple(
                        field for field in options["fields"] if field != "is_superuser"
                    ),
                },
            )
            for title, options in fieldsets
        )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if request.user.is_superuser:
            return fieldsets
        # A checkbox that hands out every permission in the system is not
        # something an organisation administrator gets to see, let alone tick.
        return self._without_superuser(fieldsets)

    def has_change_permission(self, request, obj=None):
        # Editing a superuser means being able to reset their password and then
        # sign in as them — the same escalation by a slower route.
        if obj is not None and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)


class ScopedGroupAdmin(NoEscalationAdminMixin, GroupAdmin):
    """Django's GroupAdmin with the permission picker scoped to the editor.

    This is what makes "an organisation composes its own fourth role" safe.
    Without it, ``change_group`` is a superset of every permission in the
    system: compose a group holding ``checkins.delete_auditlog``, add yourself
    to it, log out, log back in. The withheld grants in ``accounts/roles.py``
    would be a comment rather than a control.
    """


# django.contrib.auth's admin module registered the stock GroupAdmin on our
# site before this module was imported (INSTALLED_APPS order), so swap it.
admin.site.unregister(Group)
admin.site.register(Group, ScopedGroupAdmin)
