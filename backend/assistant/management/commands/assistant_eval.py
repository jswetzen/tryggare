"""Eval the assistant against a real model: briefs with deterministic criteria.

Run it against a scratch database, never one that holds real events: each brief
creates a fixture event and deletes it again.

DATABASE_URL=postgres://.../checkins_eval uv run python manage.py assistant_eval \
    --base-url http://host:11434/v1 --model NAME --runs 2 [--briefs sv-,pii]

For a hosted endpoint, name the environment variable holding the key (it is never
stored or written to the report): --base-url https://openrouter.ai/api/v1
--model vendor/name --api-key-env OPENROUTER_API_KEY
"""

import json
import os
import re
import urllib.request
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from assistant.agent import RUN_DEADLINE_SECONDS, build_model
from assistant.evals.briefs import BRIEFS
from assistant.evals.harness import (
    run_brief,
    static_capabilities_size,
    summarize,
)
from assistant.evals.report import build_report, render_markdown
from assistant.models import LLMProvider

RESULTS = Path(__file__).resolve().parents[2] / "evals" / "results"


def ollama_num_ctx(base_url: str, model: str) -> int | None:
    """The Modelfile's num_ctx via Ollama's /api/show; None on any other server."""
    root = re.sub(r"/v1/?$", "", base_url.rstrip("/"))
    try:
        req = urllib.request.Request(
            f"{root}/api/show",
            json.dumps({"model": model}).encode(),
            {"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            params = json.load(resp).get("parameters", "")
        match = re.search(r"num_ctx\s+(\d+)", params)
        return int(match.group(1)) if match else None
    except Exception:
        return None


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--base-url", default="")
        parser.add_argument("--model", default="")
        parser.add_argument("--api-key-env", default="", help="env var holding the key")
        parser.add_argument("--runs", type=int, default=1)
        parser.add_argument(
            "--briefs", default="", help="comma-separated substrings of brief ids"
        )
        parser.add_argument("--out", default=str(RESULTS), help="directory for reports")
        parser.add_argument("--deadline", type=float, default=RUN_DEADLINE_SECONDS)

    def handle(
        self,
        *args,
        base_url,
        model,
        runs,
        briefs,
        out,
        deadline,
        api_key_env="",
        **opts,
    ):
        saved = LLMProvider.load()
        provider = (
            LLMProvider(base_url=base_url, model=model or saved.model)
            if base_url
            else saved
        )
        if not provider.base_url or not provider.model:
            raise CommandError("give --base-url and --model, or save a provider first")
        wanted = [w for w in briefs.split(",") if w]
        chosen = [b for b in BRIEFS if not wanted or any(w in b.id for w in wanted)]
        if not chosen:
            raise CommandError("no brief matches --briefs")
        if api_key_env:
            key = os.environ.get(api_key_env, "")
            if not key:
                raise CommandError(f"{api_key_env} is not set")
            provider.set_api_key(key)  # in memory only; provider is never saved
            saved = provider

        def llm():
            return build_model(provider, saved=saved)

        meta = {
            "model": provider.model,
            "base_url": provider.base_url,
            "started": datetime.now().isoformat(timespec="seconds"),
            "runs_per_brief": runs,
            "num_ctx": ollama_num_ctx(provider.base_url, provider.model),
            "capabilities": static_capabilities_size(),
        }
        stem = (
            re.sub(r"[^\w.-]+", "_", provider.model)
            + "-"
            + meta["started"][:16].replace(":", "")
        )
        directory = Path(out)
        directory.mkdir(parents=True, exist_ok=True)
        results = []
        for brief in chosen:
            for n in range(1, runs + 1):
                res = run_brief(brief, llm, run=n, deadline=deadline)
                results.append(res)
                self.stdout.write(
                    f"{'PASS' if res.passed else 'FAIL'} {brief.id} #{n} {res.wall_s}s "
                    f"req={res.requests} ctx={res.peak_context} {res.reason}"
                )
                # Written after every run: a long eval cut short still leaves a report.
                self.write(directory, stem, meta, results)
        summary = summarize(results)
        self.stdout.write(json.dumps(summary, indent=1))
        self.stdout.write(f"report: {directory / stem}.md")

    def write(self, directory, stem, meta, results):
        report = build_report(meta, results, summarize(results))
        (directory / f"{stem}.json").write_text(
            json.dumps(report, indent=1, ensure_ascii=False)
        )
        (directory / f"{stem}.md").write_text(render_markdown(report))
