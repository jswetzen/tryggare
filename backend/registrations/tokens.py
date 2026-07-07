"""
Verification-token and reference-code generation for public registrations.

Tokens gate creation/confirmation of a real child health record from the
public internet, so — unlike printing/models.py::generate_printer_token()
(a plaintext, revocable, LAN-only device credential, where that's fine) —
the token itself is never stored: only its SHA-256 hash is, and the plaintext
exists only in the one-time email sent to the guardian.
"""

import hashlib
import secrets

REFERENCE_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # no 0/O, 1/I/l
REFERENCE_CODE_LENGTH = 8


def generate_verification_token() -> str:
    """Generate a URL-safe, high-entropy plaintext token for a verification link."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a plaintext token for at-rest storage/lookup."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_unique_reference_code(max_attempts: int = 100) -> str:
    """
    Generate a short, human-readable reference code (shown to the guardian,
    used for support lookups) that doesn't collide with an existing one.
    """
    from .models import Registration

    for _ in range(max_attempts):
        code = "".join(
            secrets.choice(REFERENCE_CODE_ALPHABET)
            for _ in range(REFERENCE_CODE_LENGTH)
        )
        if not Registration.objects.filter(reference_code=code).exists():
            return code

    raise RuntimeError(
        f"Failed to generate unique reference code after {max_attempts} attempts"
    )
