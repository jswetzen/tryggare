"""DRF permission classes built on Django's per-model permission system.

Why this module exists
----------------------
Every DRF endpoint used to be gated on ``IsAuthenticated`` (or the project
default, which is the same thing). That is a single tier: a volunteer who can
open the check-in screen could equally ``GET /api/event-reports/`` and read the
whole event's finances, or ``GET /api/audit-logs/`` and read who revealed which
child's medical notes. The three seeded roles (see ``accounts/roles.py``) only
mean something if the endpoints actually consult ``user.has_perm``.

The read-access decision
------------------------
Stock :class:`rest_framework.permissions.DjangoModelPermissions` maps ``GET`` to
``[]`` — no permission at all. It guards writes only, on the assumption that the
queryset is already scoped per user. That assumption does not hold here: these
viewsets return the whole table. Using it unchanged would leave a volunteer able
to read every endpoint, which is precisely the hole this increment closes.

So :class:`DjangoModelPermissionsWithView` below adds the ``view_*`` requirement
to ``GET``/``HEAD``. This is the subclass pattern DRF documents for exactly this
case. ``OPTIONS`` stays open to any authenticated user: it returns metadata for
the browsable API and DRF's own ``SimpleMetadata`` already reflects what the
caller may do.

Function-based views
--------------------
``DjangoModelPermissions`` derives the model from ``view.queryset`` /
``view.get_queryset()``, which an ``@api_view`` function does not have. Rather
than fall back to a hand-rolled ``BasePermission`` for those (and lose the
single, auditable mapping from HTTP verb to permission codename),
:func:`model_permissions` builds a bound subclass whose model is stated
explicitly. Everything therefore remains one ``DjangoModelPermissions`` lineage.
"""

from rest_framework.permissions import DjangoModelPermissions

# Verb -> required permission codename, with DRF's ``%(app_label)s`` /
# ``%(model_name)s`` interpolation. The one deliberate deviation from stock DRF
# is GET/HEAD, discussed in the module docstring.
_PERMS_MAP = {
    "GET": ["%(app_label)s.view_%(model_name)s"],
    "OPTIONS": [],
    "HEAD": ["%(app_label)s.view_%(model_name)s"],
    "POST": ["%(app_label)s.add_%(model_name)s"],
    "PUT": ["%(app_label)s.change_%(model_name)s"],
    "PATCH": ["%(app_label)s.change_%(model_name)s"],
    "DELETE": ["%(app_label)s.delete_%(model_name)s"],
}


class DjangoModelPermissionsWithView(DjangoModelPermissions):
    """``DjangoModelPermissions`` that also requires ``view_*`` for reads."""

    perms_map = _PERMS_MAP


class _BoundModelPermissions(DjangoModelPermissionsWithView):
    """Base for the classes :func:`model_permissions` generates.

    ``model`` is filled in by the factory; ``_queryset`` is overridden so the
    class works on a view that has no queryset of its own (an ``@api_view``
    function, or a viewset whose model is not the one being authorised).
    """

    model = None

    def _queryset(self, view):
        return self.model._default_manager.all()


def model_permissions(model, *, perms_map=None, name=None):
    """Build a ``DjangoModelPermissions`` subclass bound to ``model``.

    ``perms_map`` overrides individual verbs on top of the default map. The
    override exists for actions whose HTTP verb lies about their semantics: the
    check-in screen's money actions are ``POST`` but modify an existing
    Registration, so mapping them to ``add_registration`` would hand out the
    wrong permission and, worse, one that reads as harmless.
    """
    attrs = {"model": model}
    if perms_map:
        attrs["perms_map"] = {**_PERMS_MAP, **perms_map}
    return type(
        name or f"{model.__name__}ModelPermissions", (_BoundModelPermissions,), attrs
    )


# Convenience maps for the override above, so call sites read as intent rather
# than as format strings.
POST_REQUIRES_CHANGE = {"POST": ["%(app_label)s.change_%(model_name)s"]}
POST_REQUIRES_DELETE = {"POST": ["%(app_label)s.delete_%(model_name)s"]}
