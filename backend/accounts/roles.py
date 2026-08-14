"""The three seeded roles, and the permission set each one carries.

This module is the single authoritative statement of what a Volontär, a
Koordinator and an Administratör may do. The data migration
``accounts/0003_seed_roles`` reads it to create the groups; the tests read it to
assert the endpoints agree with it. Nothing else derives a role from
``is_staff`` any more — see ``accounts/views.py`` for the one meaning
``is_staff`` retains.

Group names are fixed Swedish, not translated msgids
----------------------------------------------------
``Group.name`` is a unique database key that code and operators look rows up
by. If it were a msgid rendered per active language, the same group would have
a different identity depending on who ran the migration, ``get(name="Volontär")``
would start failing, and an English-locale deploy would silently create a fourth
group on the next seed. Django itself treats ``Group.name`` as data rather than
UI text for the same reason. These are also the product's own Swedish domain
words — a Swedish-first deployment calls the role "Volontär" in an English
sentence too — so there is nothing to translate.

What each role is for
---------------------
Volontär
    Works the door. Reads the operational data needed to check a family in,
    creates and closes check-ins, prints labels, and takes payment from the
    family standing in front of them. Cannot browse anyone else's finances,
    cannot read the audit log, cannot change events or families.

Koordinator
    Runs the event. Everything in the app, including reports and the audit log
    (read-only — see below), with no Django-admin access.

Administratör
    Koordinator plus ``is_staff``, i.e. plus Django admin, plus the ability to
    manage the organisation's own users and compose additional groups.

Three things no role gets, deliberately
---------------------------------------
``printing.add_printer`` / ``printing.delete_printer``
    Provisioning a printer and rotating its token mint the credential the
    printer client authenticates with. That is a security operation, and it
    stays with ``is_superuser`` (us). Note this is not only an admin-page
    concern: ``rotate-token`` and ``revoke-token`` are ``POST`` actions on the
    printer viewset, so withholding ``add_printer`` closes the API path too.

``checkins.delete_auditlog`` (and add/change)
    The audit log is the record that protects the organisation and the family
    equally. An administrator who can erase it can erase evidence about
    themselves. Every role reads it at most.

``accounts.AdminUser`` superuser promotion
    Administratör can manage users but must not be able to promote one (or
    themselves) to superuser. A permission cannot express "this field but not
    that one", so the enforcement lives in ``accounts/admin.py``, which hides
    ``is_superuser`` from non-superusers, and in ``config/admin.py``, which
    stops a non-superuser granting a permission they do not themselves hold.
"""

VOLUNTEER = "Volontär"
COORDINATOR = "Koordinator"
ADMINISTRATOR = "Administratör"

ROLE_NAMES = (VOLUNTEER, COORDINATOR, ADMINISTRATOR)


# --------------------------------------------------------------------------
# Volontär — the door shift.
# --------------------------------------------------------------------------
_VOLUNTEER_PERMISSIONS = {
    # Look up the family at the door and see who is in it. Read-only: a
    # volunteer never edits a record. (The *restricted* roster that hides
    # balances is step 2's own view; until it exists this is the roster the
    # check-in screen reads, so the read stays granted.)
    "families.view_family",
    "families.view_attendee",
    "families.view_parent",
    "families.view_child",
    # See what the family bought, so the check-in screen can say what they are
    # entitled to attend.
    "events.view_event",
    "events.view_session",
    "events.view_eventticket",
    "events.view_sessionticket",
    "events.view_tickettype",
    "events.view_extra",
    "events.view_extrachoice",
    # The actual job: check in, check out, undo. ``delete_checkinrecord`` is
    # not here on purpose — "undo" is a POST action that closes a record, not a
    # deletion, and nothing should let a volunteer make a check-in never have
    # happened.
    "checkins.view_checkinrecord",
    "checkins.add_checkinrecord",
    "checkins.change_checkinrecord",
    # Print the label. Choosing a printer needs to read the printer list;
    # provisioning one does not follow from that.
    "printing.view_printer",
    "printing.view_printjob",
    "printing.add_printjob",
    # Reassigning a queued job to a different printer, for when the one by the
    # door is offline. A door fix, not configuration.
    "printing.change_printjob",
    # Door money only (case catalog §9.3): take payment from the family at the
    # front of the queue, or let them in and settle later. Both are POST
    # actions mapped to ``change_registration`` rather than ``add_``, so this
    # grant does not also mean "can create registrations".
    "registrations.view_registration",
    "registrations.change_registration",
    "registrations.view_payment",
    "registrations.change_payment",
}


# --------------------------------------------------------------------------
# Koordinator — everything in the app, no Django admin.
# --------------------------------------------------------------------------
_COORDINATOR_PERMISSIONS = _VOLUNTEER_PERMISSIONS | {
    # Full family management, including the two GDPR duties. DSAR export and
    # erasure get their own permissions (families/models.py) rather than being
    # inferred from view/delete: an export of everything held about a family —
    # including a child's allergy and medical text — is a different act from
    # opening the family page, and mapping erasure onto DRF's default
    # "POST means add" would have made it reachable with ``add_family``.
    "families.add_family",
    "families.change_family",
    "families.delete_family",
    "families.add_attendee",
    "families.change_attendee",
    "families.delete_attendee",
    "families.add_parent",
    "families.change_parent",
    "families.delete_parent",
    "families.add_child",
    "families.change_child",
    "families.delete_child",
    "families.export_family_dsar",
    "families.erase_family_dsar",
    # Full event configuration.
    "events.add_event",
    "events.change_event",
    "events.delete_event",
    "events.add_session",
    "events.change_session",
    "events.delete_session",
    "events.add_tickettype",
    "events.change_tickettype",
    "events.delete_tickettype",
    "events.view_promocode",
    "events.add_promocode",
    "events.change_promocode",
    "events.delete_promocode",
    "events.add_extra",
    "events.change_extra",
    "events.delete_extra",
    "events.add_extrachoice",
    "events.change_extrachoice",
    "events.delete_extrachoice",
    "events.add_eventticket",
    "events.change_eventticket",
    "events.delete_eventticket",
    "events.add_sessionticket",
    "events.change_sessionticket",
    "events.delete_sessionticket",
    # The deprecated Ticket model still has a routed viewset; granting it here
    # keeps that endpoint working for the role that owns configuration, and
    # withholding it from Volontär costs nothing since nothing new writes it.
    "events.view_ticket",
    "events.add_ticket",
    "events.change_ticket",
    "events.delete_ticket",
    # Check-in corrections, and read access to the audit log. Read only: see
    # the module docstring.
    "checkins.delete_checkinrecord",
    "checkins.view_auditlog",
    # Printer housekeeping short of minting credentials.
    "printing.change_printer",
    "printing.delete_printjob",
    # Full money. This is the line the roles exist to draw: Volontär handles the
    # family in front of them, Koordinator browses everyone's finances.
    "registrations.add_registration",
    "registrations.delete_registration",
    "registrations.add_payment",
    "registrations.delete_payment",
    "registrations.view_paymentevent",
    "registrations.add_paymentevent",
    "registrations.view_registrationextra",
    "registrations.add_registrationextra",
    "registrations.change_registrationextra",
    "registrations.delete_registrationextra",
    # Reports — the aggregate financial and attendance picture.
    "reports.view_eventreport",
    "reports.add_eventreport",
    "reports.delete_eventreport",
    # Import configuration, and running an import. The import API was the last
    # corner of the API still gated on ``IsAdminUser`` — i.e. on ``is_staff`` —
    # which left these grants dead letters for a Koordinator. ``imports/views``
    # now binds each endpoint to the permission it actually needs, so these are
    # live and the frontend's /import guard can read them.
    "imports.view_importsource",
    "imports.add_importsource",
    "imports.change_importsource",
    "imports.delete_importsource",
    "imports.view_festivalproimportsource",
    "imports.add_festivalproimportsource",
    "imports.change_festivalproimportsource",
    "imports.delete_festivalproimportsource",
    "imports.view_importrun",
    "imports.add_importrun",
    "imports.delete_importrun",
}


# --------------------------------------------------------------------------
# Administratör — Koordinator plus Django admin, plus user/role management.
# --------------------------------------------------------------------------
_ADMINISTRATOR_PERMISSIONS = _COORDINATOR_PERMISSIONS | {
    # Manage the organisation's own accounts. Superuser promotion is blocked in
    # accounts/admin.py, not here — a model permission cannot scope a field.
    "accounts.view_adminuser",
    "accounts.add_adminuser",
    "accounts.change_adminuser",
    "accounts.delete_adminuser",
    # Compose a fourth role. This is what "custom ACL" means in this product,
    # and why increment 0.4 kept auth.Group on the admin index. config/admin.py
    # restricts the permission picker to permissions the editor already holds,
    # so this is not a route to the three grants withheld above.
    "auth.view_group",
    "auth.add_group",
    "auth.change_group",
    "auth.delete_group",
}


ROLE_PERMISSIONS = {
    VOLUNTEER: frozenset(_VOLUNTEER_PERMISSIONS),
    COORDINATOR: frozenset(_COORDINATOR_PERMISSIONS),
    ADMINISTRATOR: frozenset(_ADMINISTRATOR_PERMISSIONS),
}


def split_permission(label: str) -> tuple[str, str]:
    """``"events.view_event"`` -> ``("events", "view_event")``."""
    app_label, codename = label.split(".", 1)
    return app_label, codename


def grant(user, role_name: str):
    """Add ``user`` to a seeded role group and drop their cached permissions.

    ``ModelBackend`` memoises ``get_all_permissions`` on the user instance the
    first time anything asks, so a group added after that point is invisible
    until the object is reloaded — a failure mode that looks exactly like a
    missing grant. Clearing the caches here means callers (tests, the demo
    seeder, a future invite flow) never have to know that.
    """
    from django.contrib.auth.models import Group

    user.groups.add(Group.objects.get(name=role_name))
    for attribute in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
        user.__dict__.pop(attribute, None)
    return user
