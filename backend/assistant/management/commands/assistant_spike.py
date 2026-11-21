"""Spike: run the assistant on one event against the saved (or --base-url) provider.

uv run python manage.py assistant_spike --event ID --user NAME "Create ..."
"""

import asyncio
import json
import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from assistant import tools
from assistant.agent import (
    build_agent,
    build_model,
    guarded_http_client,
    run_assistant,
)
from assistant.models import LLMProvider
from assistant.providers import ProviderError
from events.models import Event

SHOWN = ("ToolCallPart", "ToolReturnPart", "RetryPromptPart")


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("prompt")
        parser.add_argument("--event", required=True)
        parser.add_argument("--user", required=True, help="username acting on --event")
        parser.add_argument("--base-url", default="")
        parser.add_argument("--model", default="")
        parser.add_argument(
            "--debug",
            action="store_true",
            help="print the body of non-2xx provider responses (spike only)",
        )

    def handle(self, *args, prompt, base_url, model, event, user, debug=False, **opts):
        saved = LLMProvider.load()
        provider = LLMProvider(base_url=base_url, model=model) if base_url else saved
        toolset, drafts = tools.build_toolset(
            Event.objects.get(pk=event), get_user_model().objects.get(username=user)
        )
        http_client = None
        if debug:
            http_client = guarded_http_client(provider.base_url.strip())

            async def dump(response):
                if response.status_code >= 400:
                    await response.aread()
                    self.stderr.write(
                        f"HTTP {response.status_code} BODY: {response.text[:2000]}"
                    )

            http_client.event_hooks["response"].append(dump)
        model_obj = build_model(provider, http_client=http_client) if debug else None
        agent = build_agent(provider, toolset, model=model_obj)
        started = time.monotonic()
        try:
            result = asyncio.run(run_assistant(agent, prompt))
        except ProviderError as exc:
            self.stdout.write(f"PROVIDER ERROR: {exc.code} status={exc.status}")
            raise
        except Exception as exc:
            self.show(getattr(exc, "transcript", []))
            raise
        self.show(result.all_messages())
        self.stdout.write(f"FINAL: {result.output}")
        self.stdout.write(f"WALL: {time.monotonic() - started:.1f}s")
        for token, draft in drafts.items.items():
            self.stdout.write(f"DRAFT {token}: {json.dumps(draft['diff'], indent=1)}")

    def show(self, messages):
        for msg in messages:
            for part in msg.parts:
                if type(part).__name__ in SHOWN:
                    self.stdout.write(f"{type(part).__name__}: {part}")
