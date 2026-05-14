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
git clone https://github.com/jswetzen/check-ins.git
cd check-ins/printer-client
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
| `STAFF_USERNAME` | `admin` | Staff login username |
| `STAFF_PASSWORD` | `admin123` | Staff login password |
| `PRINTER_UUID` | random UUID | Stable printer identity — generate once, keep forever |
| `PRINTER_NAME` | `Label Printer` | Name shown in the UI |
| `PRINTER_IDENTIFIER` | *(auto-detect)* | USB: `usb://0x04f9:0x2042`  Network: `tcp://192.168.1.50` |
| `PRINTER_BACKEND` | `pyusb` | `pyusb`, `network`, or `linux_kernel` |
| `PRINTER_MODEL` | `QL-810W` | Brother QL model string |
| `LABEL_SIZE` | `29x90` | Die-cut: `29x90`, `62x100`  Endless: `29`, `62` |
| `SCREENSHOT_DPI` | `300` | Render DPI — higher means better print quality |
| `DRY_RUN` | `false` | Set `true` to skip actual printing (test connectivity) |

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

### Linux — USB permissions

```bash
sudo usermod -aG lp $USER
# Log out and back in for the group change to take effect
```

### macOS

The `pyusb` backend works on macOS without special permissions. If you run into issues, check that no other driver (e.g. `ipp-usb`) has claimed the device.

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) for known issues including:
- `ipp-usb` USB reset loop on Linux
- QL-810W USB timeout and initialization quirks
- Network backend status query limitations
