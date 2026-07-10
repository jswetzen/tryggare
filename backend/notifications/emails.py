"""
Thin transactional-send entrypoint. See providers.py for the hard
constraints on what belongs in a message body and what this path may be
used for.
"""

from .providers import get_provider


def send_transactional_email(to: str, subject: str, body: str) -> None:
    get_provider().send(to, subject, body)
