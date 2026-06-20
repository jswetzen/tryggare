#!/usr/bin/env bash
# Ensure the external network required by docker-compose.prod.yml exists.
#
# docker-compose.prod.yml declares the 'traefik' network as `external: true`
# (it carries the reverse-proxy router labels). On a host that has no pre-existing
# traefik deployment, `podman compose ... up` aborts before building with:
#   RuntimeError: External network [traefik] does not exists
# Creating it here (idempotently) lets prod build/run anywhere, including local
# hosts that don't run traefik. The network name honours TRAEFIK_NETWORK from
# .env.prod, defaulting to "traefik".
set -euo pipefail

# Pull TRAEFIK_NETWORK from .env.prod if present and not already set.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_PROD="$SCRIPT_DIR/../.env.prod"
if [ -z "${TRAEFIK_NETWORK:-}" ] && [ -f "$ENV_PROD" ]; then
    TRAEFIK_NETWORK="$(grep -E '^TRAEFIK_NETWORK=' "$ENV_PROD" | head -1 | cut -d= -f2- | tr -d '"' || true)"
fi
NET="${TRAEFIK_NETWORK:-traefik}"

if podman network exists "$NET" 2>/dev/null; then
    echo "✓ External network '$NET' already exists"
else
    echo "Creating external network '$NET'..."
    podman network create "$NET"
    echo "✓ External network '$NET' created"
fi
