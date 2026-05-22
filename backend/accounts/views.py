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
                "user": {
                    "id": str(request.user.id),
                    "username": request.user.username,
                    "name": request.user.name,
                    "is_staff": request.user.is_staff,
                },
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
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "name": user.name,
                    "is_staff": user.is_staff,
                },
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
