FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS base

WORKDIR /app

# gettext provides msgfmt, needed to compile .po -> .mo translation catalogs
# below (see locale/*/LC_MESSAGES). Without it, Django's _() renders English
# regardless of locale, app-wide.
RUN apt-get update && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY manage.py ./
COPY config ./config
COPY accounts ./accounts
COPY families ./families
COPY events ./events
COPY checkins ./checkins
COPY printing ./printing
COPY imports ./imports
COPY reports ./reports
COPY demo ./demo
COPY notifications ./notifications
COPY registrations ./registrations
COPY locale ./locale

ENV PYTHONUNBUFFERED=1

# Use django-admin (not manage.py) here: it doesn't need DJANGO_SETTINGS_MODULE
# configured, so compiling .po -> .mo isn't tangled up with runtime settings
# (e.g. SECRET_KEY/email-config validation) that aren't available at build time.
RUN uv run django-admin compilemessages

ENV DJANGO_SETTINGS_MODULE=config.settings.prod

EXPOSE 8000
CMD ["uv", "run", "python", "-m", "daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
