"""OpenAI-compatible chat API: OpenAI, OpenRouter, Ollama, LM Studio, vLLM."""

import ipaddress
import json
import socket
import time
from urllib.parse import urlsplit

import requests
from django.views.decorators.debug import sensitive_variables

from .base import ProviderError

CONNECT_TIMEOUT_SECONDS = 3  # a closed port should fail fast
TIMEOUT_SECONDS = 10
MAX_RESPONSE_BYTES = 4 * 1024 * 1024  # OpenRouter's list is ~1 MB
TOTAL_DEADLINE_SECONDS = 30
# Metadata endpoints that are not link-local: EC2's IPv6 one and Alibaba Cloud's.
BLOCKED_ADDRESSES = {
    ipaddress.ip_address("fd00:ec2::254"),
    ipaddress.ip_address("100.100.100.200"),
}


def _headers(api_key: str) -> dict:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _read_json(response: requests.Response):
    body = bytearray()
    deadline = time.monotonic() + TOTAL_DEADLINE_SECONDS
    for chunk in response.iter_content(64 * 1024):
        body += chunk
        if len(body) > MAX_RESPONSE_BYTES:
            raise ProviderError("bad_response")
        if time.monotonic() > deadline:
            raise ProviderError("unreachable")
    try:
        return json.loads(body)
    except (ValueError, RecursionError):
        raise ProviderError("bad_response") from None


def _embedded_ipv4(addr: ipaddress.IPv6Address):
    """The IPv4 address an IPv6 one carries (mapped, 6to4, NAT64, IPv4-compatible)."""
    if addr.ipv4_mapped:
        return addr.ipv4_mapped
    if addr.sixtofour:
        return addr.sixtofour
    packed = addr.packed
    if packed[:12] == bytes.fromhex("0064ff9b" + "00" * 8) or packed[:12] == bytes(12):
        return ipaddress.IPv4Address(packed[12:])
    return None


def check_address(base_url: str) -> None:
    # Link-local covers the cloud metadata endpoints (169.254.169.254 and
    # friends). Private and loopback stay allowed: Ollama lives there.
    parts = urlsplit(base_url)
    if not parts.hostname:
        raise ProviderError("unreachable")
    try:
        infos = socket.getaddrinfo(
            parts.hostname,
            parts.port or (443 if parts.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except (OSError, UnicodeError, ValueError):
        raise ProviderError("unreachable") from None
    for info in infos:
        try:
            addr = ipaddress.ip_address(info[4][0].split("%")[0])
        except ValueError:
            raise ProviderError("unreachable") from None
        if isinstance(addr, ipaddress.IPv6Address):
            addr = _embedded_ipv4(addr) or addr
        if addr.is_link_local or addr in BLOCKED_ADDRESSES:
            raise ProviderError("address_blocked")


@sensitive_variables("api_key")
def list_models(base_url: str, api_key: str = "") -> list[str]:
    """Model ids from ``GET {base_url}/models``, sorted."""
    check_address(base_url)
    url = base_url.rstrip("/") + "/models"
    try:
        # No redirects: a redirect is either a wrong URL or a host we did not
        # choose, and neither should receive the key.
        response = requests.get(
            url,
            headers=_headers(api_key),
            timeout=(CONNECT_TIMEOUT_SECONDS, TIMEOUT_SECONDS),
            allow_redirects=False,
            stream=True,
        )
    except requests.RequestException:
        raise ProviderError("unreachable") from None

    with response:
        status = response.status_code
        if status in (401, 403):
            raise ProviderError("auth_failed", status)
        if status in (404, 405):
            raise ProviderError("models_not_supported", status)
        if not 200 <= status < 300:
            raise ProviderError("http_error", status)
        payload = _read_json(response)

    entries = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise ProviderError("bad_response", status)
    ids = {
        entry["id"]
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"]
    }
    return sorted(ids)
