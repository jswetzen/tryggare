"""Send one message in a stored assistant conversation (drives runner.run_conversation).

uv run python manage.py assistant_chat --event ID --user NAME [--accept-notice] "Create ..."
"""

import asyncio

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from assistant.models import AssistantConversation
from assistant.runner import RunFailed, chat_text_warning, run_conversation
from events.models import Event


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("text")
        parser.add_argument("--event", required=True)
        parser.add_argument("--user", required=True)
        parser.add_argument("--accept-notice", action="store_true")

    def handle(self, *args, text, event, user, accept_notice=False, **opts):
        event = Event.objects.get(pk=event)
        user = get_user_model().objects.get(username=user)
        if accept_notice:
            conv, _ = AssistantConversation.objects.get_or_create(
                event=event, user=user
            )
            conv.notice_accepted_at = conv.notice_accepted_at or timezone.now()
            conv.save(update_fields=["notice_accepted_at"])
        warning = chat_text_warning(text)
        if warning:
            self.stderr.write(f"Warning: the text looks like it holds {warning}.")
        try:
            out = asyncio.run(run_conversation(event, user, text))
        except RunFailed as exc:
            raise CommandError(f"run failed: {exc.code}") from None
        self.stdout.write(out["text"])
        self.stdout.write(f"DRAFT VERSION: {out['draft_version']}")
