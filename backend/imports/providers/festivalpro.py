from __future__ import annotations

from typing import TYPE_CHECKING

import requests

from imports.importer import ProviderFetchError, ProviderLoginError
from .base import ImportSourceProvider

if TYPE_CHECKING:
    from imports.models import ImportSource


class FestivalProProvider(ImportSourceProvider):
    """
    Authenticates with a FestivalPro-style booking system and fetches the JSON export.

    Login: POST form-encoded to fp_config.login_url
    - Fields: USERNAME, PASSWORD, CODESAVED=CODE%3D, TZ=1, checker=on, X=
    - Expect HTTP 302; session established via TARCH cookie in response

    Export: POST fp_config.export_url with stored export_body plus session cookies
    - Returns raw JSON string

    Raises ProviderLoginError, ProviderFetchError, ValueError (bad credentials blob).
    """

    def fetch(self, source: "ImportSource") -> str:
        from imports.encryption import decrypt_credentials
        from cryptography.fernet import InvalidToken

        fp_config = source.festivalpro_config

        try:
            creds = decrypt_credentials(bytes(source.credentials))
        except (InvalidToken, TypeError) as exc:
            raise ValueError(f"Cannot decrypt credentials for source {source.id}") from exc

        session = requests.Session()

        # Login — form-encoded, do NOT follow redirect (cookies are set before the 302)
        try:
            login_resp = session.post(
                fp_config.login_url,
                data={
                    "USERNAME": creds["username"],
                    "PASSWORD": creds["password"],
                    "CODESAVED": "CODE=",
                    "TZ": "1",
                    "checker": "on",
                    "X": "",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                allow_redirects=False,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise ProviderLoginError(f"Network error during login: {exc}") from exc

        # Expect 302 with TARCH cookie; any non-redirect is a failure
        if login_resp.status_code not in (301, 302, 303):
            raise ProviderLoginError(
                f"Login returned HTTP {login_resp.status_code} (expected redirect)"
            )
        if "TARCH" not in session.cookies:
            raise ProviderLoginError("Login succeeded but no TARCH session cookie was returned")

        # Export fetch — POST with the stored form-encoded body (contains QUERYQ, EVENTID, etc.)
        try:
            export_resp = session.post(
                fp_config.export_url,
                data=fp_config.export_body,  # raw form-encoded string, sent as-is
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=60,
            )
        except requests.RequestException as exc:
            raise ProviderFetchError(f"Network error fetching export: {exc}") from exc

        if not export_resp.ok:
            raise ProviderFetchError(
                f"Export fetch returned HTTP {export_resp.status_code}"
            )

        return export_resp.text

    def requires_event(self) -> bool:
        return True
