"""
QR code generation and pool management utilities.

Codes are 5-character random alphanumeric strings from a safe alphabet
(no confusable characters like 0/O, 1/I/l).
"""
import secrets
from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone

# Alphabet without confusable characters (0/O, 1/I/l removed)
QR_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
CODE_LENGTH = 5


def generate_random_code() -> str:
    """Generate a random code from the safe alphabet."""
    return "".join(secrets.choice(QR_ALPHABET) for _ in range(CODE_LENGTH))


def generate_unique_code(max_attempts: int = 100) -> str:
    """
    Generate a code that doesn't exist in the database.
    Uses retry with fresh random codes (not sequential).
    """
    from .models import QRCode

    for _ in range(max_attempts):
        code = generate_random_code()
        if not QRCode.objects.filter(code=code).exists():
            return code

    raise RuntimeError(f"Failed to generate unique code after {max_attempts} attempts")


@transaction.atomic
def allocate_code_for_checkin(checkin_record) -> "QRCode":
    """
    Allocate a QR code for a check-in record.

    Strategy:
    1. Try to reuse an available code from the pool (released > 24h ago)
    2. If pool exhausted, generate a new code

    Uses SELECT FOR UPDATE to prevent race conditions.

    Args:
        checkin_record: The CheckInRecord to allocate a code for

    Returns:
        QRCode instance allocated to this check-in
    """
    from .models import QRCode

    cutoff = timezone.now() - timedelta(hours=24)

    # Try to get an available code from the pool
    # Use select_for_update to lock the row and prevent race conditions
    # skip_locked=True means concurrent requests will skip to next available
    available_code = (
        QRCode.objects.select_for_update(skip_locked=True)
        .filter(
            checkin_record__isnull=True,  # Not currently assigned
        )
        .filter(
            # Either never released, or released more than 24h ago
            models.Q(released_at__isnull=True) | models.Q(released_at__lt=cutoff)
        )
        .first()
    )

    if available_code:
        # Reuse existing code
        available_code.checkin_record = checkin_record
        available_code.allocated_at = timezone.now()
        available_code.released_at = None  # Clear release timestamp
        available_code.save()
        return available_code

    # Generate a new code
    new_code = generate_unique_code()
    return QRCode.objects.create(
        code=new_code,
        checkin_record=checkin_record,
        allocated_at=timezone.now(),
        released_at=None,
    )


def release_code_for_checkout(checkin_record) -> None:
    """
    Mark the code as released when checkout occurs.
    Code remains associated for 24h grace period before becoming available again.

    Args:
        checkin_record: The CheckInRecord being checked out
    """
    from .models import QRCode

    try:
        qr_code = checkin_record.qr_code
        qr_code.released_at = timezone.now()
        # Keep checkin_record association during grace period for lookup
        qr_code.save()
    except QRCode.DoesNotExist:
        pass  # No code to release (shouldn't happen, but be defensive)


def get_code_for_active_checkin(code: str):
    """
    Get the QR code if it's currently allocated to an active check-in.

    Args:
        code: The short alphanumeric QR code (e.g., "A3B7K")

    Returns:
        QRCode instance if active, None if code doesn't exist or is not active
    """
    from .models import QRCode

    try:
        qr_code = QRCode.objects.select_related(
            "checkin_record__child",
            "checkin_record__child__family",
            "checkin_record__session",
        ).get(code=code.upper())  # Normalize to uppercase

        # Must have an active check-in (not checked out)
        if qr_code.checkin_record and qr_code.checkin_record.check_out_time is None:
            return qr_code

        return None
    except QRCode.DoesNotExist:
        return None
