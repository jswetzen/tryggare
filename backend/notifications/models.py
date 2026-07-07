import uuid

from django.db import models


class EmailSendLog(models.Model):
    """One row per successful SmtpProvider send.

    Exists solely to let the send-budget circuit breaker in providers.py
    count sends in a trailing window — no other part of the app reads this.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["sent_at"])]
