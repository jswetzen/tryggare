#!/usr/bin/env sh
# start.sh — run the printer client
export PATH="$HOME/.local/bin:$PATH"
exec printer-client "$@"
