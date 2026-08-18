import os

from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.translation import gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Rate throttle specifically for login attempts.
    Rate is read from settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login']
    so prod and dev can configure it independently.
    """

    scope = "login"


def session_user_payload(user):
    """The shape the SPA gates on.

    ``is_staff`` used to carry two unrelated jobs: "can reach Django admin" and
    "is trusted with the app's privileged screens". The frontend read it for
    both, so promoting a coordinator to see reports meant handing them the
    Django admin as well, and demoting them took the admin away as a side
    effect. Under the seeded roles ``is_staff`` keeps exactly one meaning — can
    reach Django admin — and every app-tier decision moves to ``permissions``.

    Fields:

    ``id``/``username``/``name``
        Unchanged.
    ``is_staff``
        Now means only "this user can open /admin/". Nothing in the app should
        branch on it except a link to the admin.
    ``is_superuser``
        Ours, not one of the three roles. Present so the frontend can tell "has
        every permission implicitly" apart from "was granted them", which
        matters for any screen that explains *why* an action is available.
    ``roles``
        Group names, sorted — e.g. ``["Koordinator"]``. For display ("you are
        signed in as…") and nothing else. Gating on a role name would re-create
        the ``is_staff`` problem one level up: an organisation that composes a
        fourth group in the admin gets a name this frontend has never heard of.
    ``permissions``
        Sorted ``"app_label.codename"`` strings from ``get_all_permissions()``,
        i.e. group permissions and per-user permissions combined, and every
        permission for a superuser. This is the list to gate on. The /reports
        guard the companion increment adds should check
        ``permissions.includes("reports.view_eventreport")`` — the same string
        the backend checks — rather than any derived flag, so a permission moved
        between roles needs no frontend change at all.
    """
    return {
        "id": str(user.id),
        "username": user.username,
        "name": user.name,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "roles": sorted(user.groups.values_list("name", flat=True)),
        "permissions": sorted(user.get_all_permissions()),
    }


@require_http_methods(["GET"])
@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def csrf_token(request):
    """
    Returns CSRF token for authentication.
    Used before any POST request.
    """
    return Response({"csrfToken": get_token(request)})


@api_view(["GET"])
@permission_classes([AllowAny])
def check_auth(request):
    """
    Returns authentication status and user data.
    Used by SvelteKit to verify session validity.
    """
    demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
    if request.user.is_authenticated:
        return Response(
            {
                "authenticated": True,
                "demo_mode": demo_mode,
                "user": session_user_payload(request.user),
            }
        )
    return Response({"authenticated": False, "demo_mode": demo_mode, "user": None})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    """
    Authenticates user and creates session.
    Accepts {username, password} JSON.
    Sets session cookie automatically.
    Rate limited to 5 attempts per minute per IP address.
    """
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {"error": _("Username and password are required")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        return Response(
            {
                "success": True,
                "user": session_user_payload(user),
            }
        )

    return Response(
        {"error": _("Invalid credentials")}, status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(["POST"])
def logout_view(request):
    """
    Logs out the user and clears session cookie.
    """
    logout(request)
    return Response({"success": True})
