FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS base

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY manage.py ./
COPY config ./config
COPY accounts ./accounts
COPY families ./families
COPY events ./events
COPY checkins ./checkins
COPY printing ./printing

ENV DJANGO_SETTINGS_MODULE=config.settings.prod
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uv", "run", "python", "-m", "daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
