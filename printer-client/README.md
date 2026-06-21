# printer-client

Label printer client for the Conference Child Management System. Connects to the Django backend via WebSocket, renders labels with WeasyPrint, and sends them to a Brother QL USB or network printer.

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) — the only required dependency. Install with:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
  `uv` manages its own Python interpreter, so you don't need a system Python.
- macOS or Linux (Windows not supported)
- A Brother QL printer connected via USB or WiFi

## Install

```bash
git clone https://github.com/jswetzen/tryggare.git
cd tryggare/printer-client
./install.sh
```

The script installs `printer-client` as a `uv tool` (isolated venv, Python 3.13) and creates `.env` from the template.

## Configure

```bash
$EDITOR .env
```

| Variable | Default | Description |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8000` | Django server URL |
| `PRINTER_TOKEN` | *(auto)* | Per-printer auth token. Provisioned on first run (interactive login by default); can also be set manually (see below). |
| `STAFF_USERNAME` / `STAFF_PASSWORD` | *(empty)* | Optional. Skip the interactive login by pre-seeding credentials; used once, then removed from `.env`. |
| `PRINTER_NAME` | `Label Printer` | Name shown in the UI (and the provisioned printer name) |
| `PRINTER_IDENTIFIER` | *(auto-detect)* | USB: `usb://0x04f9:0x2042`  Network: `tcp://192.168.1.50` |
| `PRINTER_BACKEND` | `pyusb` | `pyusb`, `network`, or `linux_kernel` |
| `PRINTER_MODEL` | `QL-810W` | Brother QL model string |
| `LABEL_SIZE` | `29x90` | Die-cut: `29x90`, `62x100`  Endless: `29`, `62` |
| `SCREENSHOT_DPI` | `300` | Render DPI — higher means better print quality |
| `DRY_RUN` | `false` | Set `true` to skip actual printing (test connectivity) |

> **USB printer (the default):** you don't need to set `PRINTER_IDENTIFIER` — a
> single connected Brother QL is auto-detected. The only value you must set is
> `BACKEND_URL`; set `PRINTER_MODEL` / `LABEL_SIZE` to match your hardware, and
> `PRINTER_TOKEN` is provisioned for you on first run. The **network** backend is
> the exception — it requires `PRINTER_IDENTIFIER=tcp://<ip>`. On Linux, see
> **Platform notes → Linux — USB permissions** for non-root access.

### Authentication

Each printer authenticates with a **revocable token** bound to a printer record
in the backend (not a staff login).

**First run (interactive, default).** Leave `PRINTER_TOKEN` blank and start the
client. It prompts for a staff username/password, provisions its own printer,
writes `PRINTER_TOKEN` into `.env`, and removes any credential lines from `.env`.
From then on it connects with the token only.

**Headless / scripted.** Two ways to avoid the prompt:

- Pre-seed `STAFF_USERNAME` / `STAFF_PASSWORD` in `.env`. They're used once to
  provision the token, then stripped from `.env`.
- Provision a token yourself and set `PRINTER_TOKEN` directly:
  - **Django admin** → *Printing → Printers → Add printer*, copy the read-only
    **Token** field.
  - **API** (staff session): `POST /api/printing/printers/provision/` with
    `{"name": "Foyer printer"}`; the response includes `token` **once**.

Run with `--non-interactive` (e.g. under systemd or in a container) to *never*
prompt: the client requires `PRINTER_TOKEN` or `STAFF_*` to be set and fails
fast otherwise.

```bash
./start.sh --non-interactive
```

To replace a token, rotate it (admin action or
`POST /api/printing/printers/{id}/rotate-token/`). Revoking
(`.../revoke-token/`) disconnects the client; if `STAFF_*` env credentials are
still set it auto-provisions a fresh token, otherwise set a new `PRINTER_TOKEN`.

## Run

```bash
./start.sh
```

The client connects, registers itself with the backend, and processes print jobs. It reconnects automatically on disconnect.

### Dry-run mode

```bash
DRY_RUN=true ./start.sh
```

Processes jobs end-to-end but skips sending to the printer. Useful for testing the WebSocket connection.

## Network printer backend (optional)

For WiFi/network printers with SNMP status queries, reinstall with the `network` extra:

```bash
uv tool install --python 3.13 --force '.[network]'
```

## Platform notes

### Linux — USB permissions (non-root)

The default `pyusb` backend talks to the printer through **libusb**, which needs
read/write access to the raw USB device node (`/dev/bus/usb/...`). That node is
owned by `root` by default, so running as a normal user fails with:

```
Printer discovery failed: [Errno 13] Access denied (insufficient permissions)
```

Joining the `lp` group is only **half** the fix — you also need a **udev rule**
that assigns the printer to that group. (Adding the printer to **CUPS** or
joining `lpadmin` does *not* help the `pyusb` backend: CUPS is a separate path
and can even hold the device open. See [troubleshooting](docs/troubleshooting.md).)

```bash
# 1. Install a udev rule giving the lp group rw access to Brother QL devices.
sudo tee /etc/udev/rules.d/99-brother-ql.rules >/dev/null <<'EOF'
# Brother QL label printers (vendor 04f9) — grant the lp group rw access
SUBSYSTEM=="usb", ATTRS{idVendor}=="04f9", GROUP="lp", MODE="0664"
EOF

# 2. Make sure you're in the lp group.
sudo usermod -aG lp $USER

# 3. Reload udev and re-trigger (or just unplug/replug the printer).
sudo udevadm control --reload-rules
sudo udevadm trigger

# 4. Log out and back in (or run `newgrp lp`) so the group change takes effect,
#    then re-run ./start.sh
```

Verify the device node is now group-`lp` and group-writable:

```bash
lsusb -d 04f9:                     # note the Bus/Device numbers
ls -l /dev/bus/usb/<bus>/<device>  # expect: crw-rw-r-- root lp
```

> **nushell:** `sudo usermod -aG lp,lpadmin $env.USER` adds you to the groups,
> but without the udev rule above the raw USB node stays `root:root` and the
> membership has no effect on the `pyusb` backend.

**Alternative — `uaccess` (desktop sessions only).** On a normal desktop login
you can skip the group entirely and let `systemd-logind` grant the logged-in
user an ACL on the device — no group, no relogin:

```bash
sudo tee /etc/udev/rules.d/99-brother-ql.rules >/dev/null <<'EOF'
# Brother QL label printers (vendor 04f9) — grant the active seat user access
SUBSYSTEM=="usb", ATTRS{idVendor}=="04f9", TAG+="uaccess"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
# then replug the printer
```

The catch: `uaccess` only grants the user logged in at the local **graphical
seat**. It gives **nothing** to a systemd service, an SSH session, or a
kiosk/appliance running as a dedicated user — for those, use the `GROUP="lp"`
rule above (it works regardless of how the client is launched), which is why
that's the default here.

**Alternative — the `linux_kernel` backend.** If you'd rather not add a udev
rule, set `PRINTER_BACKEND=linux_kernel` in `.env`. It prints through the
kernel's `usblp` driver (`/dev/usb/lp0`), which is already owned by `root:lp`,
so `lp` group membership alone is enough. Trade-offs: it can't query printer
status, and it conflicts with `ipp-usb` (stop that service first — see
[troubleshooting](docs/troubleshooting.md)).

### macOS

The `pyusb` backend works on macOS without special permissions. If you run into issues, check that no other driver (e.g. `ipp-usb`) has claimed the device.

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) for known issues including:
- `[Errno 13] Access denied` on Linux (non-root USB permissions / udev)
- `ipp-usb` USB reset loop on Linux
- QL-810W USB timeout and initialization quirks
- Network backend status query limitations
