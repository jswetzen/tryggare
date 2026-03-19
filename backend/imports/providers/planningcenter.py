from __future__ import annotations

import json
from typing import TYPE_CHECKING

import requests

from imports.importer import ProviderFetchError
from .base import ImportSourceProvider

if TYPE_CHECKING:
    from imports.models import ImportSource


class PlanningCenterProvider(ImportSourceProvider):
    """
    Fetches all households and their members from Planning Center People API v2.

    Auth: Personal Access Token — app_id stored as username, secret as password
    in the existing encrypted credentials field.

    Paginates GET /people/v2/households, then for each household paginates
    GET /people/v2/households/{id}/people?include=emails,phone_numbers.

    Returns a JSON-serialised list of household dicts ready for run_import_planningcenter().

    Raises ProviderFetchError on non-2xx or RequestException.
    Raises ValueError if credentials cannot be decrypted.
    """

    BASE_URL = "https://api.planningcenteronline.com/people/v2"

    def fetch(self, source: "ImportSource") -> str:
        from imports.encryption import decrypt_credentials
        from cryptography.fernet import InvalidToken

        try:
            creds = decrypt_credentials(bytes(source.credentials))
        except (InvalidToken, TypeError) as exc:
            raise ValueError(f"Cannot decrypt credentials for source {source.id}") from exc

        app_id = creds["username"]
        secret = creds["password"]

        session = requests.Session()
        session.auth = (app_id, secret)
        session.headers["Accept"] = "application/json"

        households = self._fetch_all_households(session)

        return json.dumps(households)

    def _fetch_all_households(self, session: requests.Session) -> list[dict]:
        households = []
        url = f"{self.BASE_URL}/households"
        params: dict = {"per_page": 100, "offset": 0}

        while True:
            resp = self._get(session, url, params)
            data = resp.get("data", [])
            if not data:
                break

            for household in data:
                hid = household["id"]
                attrs = household.get("attributes", {})
                primary_contact_id = household.get("relationships", {}).get(
                    "primary_contact", {}
                ).get("data", {})
                if isinstance(primary_contact_id, dict):
                    primary_contact_id = primary_contact_id.get("id")
                else:
                    primary_contact_id = None

                members = self._fetch_household_members(session, hid)
                households.append(
                    {
                        "id": hid,
                        "name": attrs.get("name", ""),
                        "primary_contact_id": primary_contact_id,
                        "members": members,
                    }
                )

            meta = resp.get("meta", {})
            total_count = meta.get("total_count", 0)
            next_offset = params["offset"] + len(data)
            if next_offset >= total_count:
                break
            params = {"per_page": 100, "offset": next_offset}

        return households

    def _fetch_household_members(self, session: requests.Session, household_id: str) -> list[dict]:
        members = []
        url = f"{self.BASE_URL}/households/{household_id}/people"
        params: dict = {
            "per_page": 100,
            "offset": 0,
            "include": "emails,phone_numbers",
        }

        while True:
            resp = self._get(session, url, params)
            data = resp.get("data", [])
            if not data:
                break

            # Build lookup: resource type+id -> attributes from included sideloads
            included_by_key: dict[str, dict] = {}
            for inc in resp.get("included", []):
                key = f"{inc['type']}:{inc['id']}"
                included_by_key[key] = inc.get("attributes", {})

            for person in data:
                attrs = person.get("attributes", {})
                rels = person.get("relationships", {})

                # Resolve first email from sideloaded relationships
                email = self._first_related_value(
                    rels, "emails", included_by_key, "address"
                )
                # Resolve first phone from sideloaded relationships
                phone = self._first_related_value(
                    rels, "phone_numbers", included_by_key, "number"
                )

                members.append(
                    {
                        "id": person["id"],
                        "first_name": attrs.get("first_name", ""),
                        "last_name": attrs.get("last_name", ""),
                        "child": bool(attrs.get("child", False)),
                        "birthdate": attrs.get("birthdate") or None,
                        "medical_notes": attrs.get("medical_notes") or None,
                        "email": email,
                        "phone": phone,
                    }
                )

            meta = resp.get("meta", {})
            total_count = meta.get("total_count", 0)
            next_offset = params["offset"] + len(data)
            if next_offset >= total_count:
                break
            params = {
                "per_page": 100,
                "offset": next_offset,
                "include": "emails,phone_numbers",
            }

        return members

    def _first_related_value(
        self,
        relationships: dict,
        rel_key: str,
        included_by_key: dict[str, dict],
        attr_field: str,
    ) -> str | None:
        rel_data = relationships.get(rel_key, {}).get("data", [])
        if not isinstance(rel_data, list):
            rel_data = [rel_data] if rel_data else []
        for ref in rel_data:
            if not isinstance(ref, dict):
                continue
            key = f"{ref.get('type')}:{ref.get('id')}"
            attrs = included_by_key.get(key, {})
            val = attrs.get(attr_field)
            if val:
                return val
        return None

    def _get(self, session: requests.Session, url: str, params: dict) -> dict:
        try:
            resp = session.get(url, params=params, timeout=30)
        except requests.RequestException as exc:
            raise ProviderFetchError(f"Network error fetching {url}: {exc}") from exc
        if not resp.ok:
            raise ProviderFetchError(
                f"Planning Center API returned HTTP {resp.status_code} for {url}"
            )
        return resp.json()

    def requires_event(self) -> bool:
        return False
