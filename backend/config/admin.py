"""Admin site wiring: branding, app ordering, and the index hide helper.

The failure this exists to prevent: the admin index listed 27 model entries
across nine unordered app blocks, several of which a volunteer can never
usefully open. A coordinator looking for "the ticket screen" had to read
past Extra Choices, Attendees, Print jobs and a deprecated Tickets entry
first.
"""

from django.contrib.admin.apps import AdminConfig
from django.contrib.admin.sites import AdminSite
from django.utils.translation import gettext_lazy as _

# Apps in the order a coordinator needs them, not alphabetical. Events and
# Registrations are the daily surfaces; Imports and Printing are setup and
# machinery, so they sit below. Anything not listed sorts after these, by
# label, so a newly installed app is never silently swallowed.
APP_ORDER = [
    "events",
    "registrations",
    "families",
    "checkins",
    "reports",
    "imports",
    "printing",
    "accounts",
    "auth",
]


class TryggareAdminSite(AdminSite):
    site_header = _("Tryggare administration")
    # The browser tab, not just the page body. Tenant administrators are
    # Django-admin users (decision D4), so this surface is customer-facing —
    # "Django site admin" in the tab is somebody else's product name. Kept
    # shorter than site_header because it renders after a "|" separator.
    site_title = _("Tryggare admin")
    index_title = _("Choose what to manage")

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        order = {label: i for i, label in enumerate(APP_ORDER)}
        app_list.sort(
            key=lambda app: (order.get(app["app_label"], len(order)), app["name"])
        )
        return app_list


class TryggareAdminConfig(AdminConfig):
    """Swapped in for ``django.contrib.admin`` in INSTALLED_APPS so that
    ``django.contrib.admin.site`` resolves to :class:`TryggareAdminSite`."""

    default_site = "config.admin.TryggareAdminSite"


class HiddenFromIndexAdmin:
    """Mixin for a ModelAdmin whose model should not appear on the admin
    index or in the sidebar, while remaining fully usable.

    Returning an empty perms dict from ``get_model_perms`` is what removes
    the entry — deliberately *not* ``admin.site.unregister``, because the
    registration is still needed:

    * ``autocomplete_fields`` on another admin only works if the *target*
      model has its own registered ModelAdmin with ``search_fields``
      (``ExtraChoice`` and ``Attendee`` are registered for exactly that);
    * the change/add views stay reachable by URL, so an inline or a
      "view on site" link still resolves.

    Unregistering any of these would break autocomplete widgets at runtime.
    See ``ExtraChoiceAutocompleteStillWorksTest`` in registrations/tests.py.
    """

    def get_model_perms(self, request):
        return {}
