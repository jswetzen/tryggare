# Printer Client

Python client for automated label printing. Runs on a LAN machine with a USB or WiFi Brother QL printer attached.

## How it works

1. Authenticates to the Django backend using staff credentials
2. Opens a persistent WebSocket connection
3. Sends `printer_register` to announce itself
4. Listens for `print_job` messages
5. For each job: fetches the label URL, renders it with Playwright (headless Chromium), screenshots the `.label` div, and sends the PNG to `brother_ql` for printing
6. Reports `print_job_completed` or `print_job_failed` back via WebSocket
7. Reconnects automatically with exponential backoff on disconnect

## Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright Chromium
playwright install chromium

# Copy and edit environment config
cp .env.example .env
$EDITOR .env
```

## Running

```bash
python client.py
```

## Dry-run mode (no actual printing)

```bash
DRY_RUN=true python client.py
```

This connects to the backend and processes jobs but skips the `brother_ql` print call. Useful for testing WebSocket connectivity.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8000` | Backend server URL |
| `STAFF_USERNAME` | `admin` | Staff login username |
| `STAFF_PASSWORD` | `admin123` | Staff login password |
| `PRINTER_UUID` | random UUID | Stable printer identity (generate once) |
| `PRINTER_NAME` | `Label Printer` | Human-readable printer name shown in UI |
| `PRINTER_IDENTIFIER` | `` | USB (`usb://0x04f9:0x2042`) or network (`tcp://192.168.1.50`) |
| `PRINTER_BACKEND` | `pyusb` | `pyusb`, `network`, or `linux_kernel` |
| `PRINTER_MODEL` | `QL-700` | Brother QL model string |
| `LABEL_SIZE` | `62` | Label width in mm |
| `SCREENSHOT_DPI` | `300` | Playwright screenshot DPI |
| `DRY_RUN` | `false` | Skip actual printing when `true` |

## Requirements

- Python 3.11+
- Chromium (via `playwright install chromium`)
- USB access to Brother QL printer (or network access for WiFi models)
