#!/usr/bin/env sh
# install.sh — one-command setup for printer-client (macOS and Linux)
set -e

# ── 1. Require uv ─────────────────────────────────────────────────────────
if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv not found. Install it first:" >&2
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    echo "Then open a new terminal and re-run this script." >&2
    exit 1
fi
echo "Using uv $(uv --version)"

# ── 2. Install printer-client as a uv tool ────────────────────────────────
# uv tool install creates an isolated venv and links the entry-point onto PATH.
echo "Installing printer-client (Python 3.13)..."
uv tool install --python 3.13 --force .

# ── 3. Copy .env if not present ───────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "Created .env from .env.example — edit it before running:"
    echo "  \$EDITOR .env"
else
    echo ".env already exists, skipping"
fi

# ── Done ──────────────────────────────────────────────────────────────────
echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Set BACKEND_URL in .env. A USB printer is auto-detected and the token"
echo "     is provisioned on first run; set PRINTER_MODEL/LABEL_SIZE for your hardware."
echo "  2. Run: ./start.sh"
echo ""
echo "Linux (non-root USB): you'll likely need a udev rule + the 'lp' group —"
echo "  see the README 'Linux — USB permissions' section."
echo ""
echo "For network printer (SNMP status queries):"
echo "  uv tool install --python 3.13 --force '.[network]'"
