import base64
import hashlib
import json

from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken  # noqa: F401 — re-exported for callers


def _get_fernet() -> Fernet:
    raw = settings.SECRET_KEY.encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt_credentials(username: str, password: str) -> bytes:
    plaintext = json.dumps({"username": username, "password": password}).encode()
    return _get_fernet().encrypt(plaintext)


def decrypt_credentials(token: bytes) -> dict:
    # bytes() call handles memoryview returned by psycopg3 for BinaryField
    return json.loads(_get_fernet().decrypt(bytes(token)).decode())
