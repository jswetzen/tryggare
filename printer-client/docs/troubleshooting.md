# Getting the Brother QL-810W printing

## System issue: ipp-usb causing USB reset loop

The `ipp-usb` service (IPP over USB daemon) was continuously resetting the USB device every ~2 seconds, making all communication impossible. Visible in `dmesg` as a cycle of `usblp1: USB Bidirectional printer` followed by `usblp1: removed`.

**Fix:** `systemctl stop ipp-usb.service`

This must be done before any USB communication with the printer will work. The service is "static" (not enabled) so it won't auto-start on reboot, but it may be triggered by udev when the printer is plugged in.

## Permissions: `[Errno 13] Access denied (insufficient permissions)`

The `pyusb` backend (the default) uses libusb to claim the raw USB device, which
needs read/write access to `/dev/bus/usb/...`. That node is `root`-owned by
default, so a non-root user can't open it — discovery fails before it finds
anything:

```
Printer discovery failed: [Errno 13] Access denied (insufficient permissions)
No PRINTER_IDENTIFIER set and discovery failed
```

This is **not** fixed by adding the printer to CUPS or joining `lpadmin` — those
govern the CUPS/IPP path, not raw libusb access. On Debian-based systems (Debian,
Ubuntu, Linux Mint) the fix is a udev rule assigning the node to `plugdev`, the
conventional libusb/hotplug group (already in a normal desktop session, so no
relogin is usually needed). It is *not* `lp` — `lp` is for the kernel printer
node (`/dev/usb/lp0`) that only the `linux_kernel` backend uses:

```bash
sudo tee /etc/udev/rules.d/99-brother-ql.rules >/dev/null <<'EOF'
SUBSYSTEM=="usb", ATTRS{idVendor}=="04f9", GROUP="plugdev", MODE="0664"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
# replug the printer. If `id` doesn't list plugdev, add yourself and re-login:
#   sudo usermod -aG plugdev $USER   # then log out/in or `newgrp plugdev`
```

Without the udev rule the raw node stays `root:root`, so group membership
changes nothing for `pyusb`. With the rule it becomes `root:plugdev` +
mode `0664`, and any `plugdev` member can open it. Confirm with:

```bash
lsusb -d 04f9:                     # note the Bus/Device numbers
ls -l /dev/bus/usb/<bus>/<device>  # expect: crw-rw-r-- root plugdev
```

If you'd rather avoid the udev rule, set `PRINTER_BACKEND=linux_kernel`: it
prints via the kernel's `usblp` driver (`/dev/usb/lp0`, already `root:lp`), so
`lp` membership alone suffices — but it can't query status and conflicts with
`ipp-usb` (above). See the README "Linux — USB permissions" section.

## Code changes

### 1. Missing initialization before status request (`helpers.py`)

The `get_status()` function sent only `ESC i S` (status information request). The QL-810W requires an `ESC @` (initialize) command first, otherwise it returns a zero-length USB packet instead of the 32-byte status response.

```python
# Before (broken)
printer.write(b"\x1b\x69\x53")  # "ESC i S" only

# After (working)
printer.write(b"\x1b\x40")      # "ESC @" Initialize
printer.write(b"\x1b\x69\x53")  # "ESC i S" Status information request
```

### 2. USB read timeout too short (`pyusb.py`)

`read_timeout` was 10ms. After receiving `ESC @`, the QL-810W first sends a zero-length packet (ZLP), then delivers the actual 32-byte status response ~100ms later. The old `try_twice` strategy with 10ms between attempts always missed it.

- Changed `read_timeout` from `10` ms to `500` ms
- Added a third retry attempt to `_read()` so it can skip past the initial ZLP

### 3. Network backend status blocked (`helpers.py`)

`get_printer()` raised a bare `NotImplementedError` for the network backend. Changed to a descriptive `ValueError` explaining that the network backend (port 9100) does not support bidirectional communication needed for status queries.

### 4. Network read timeout too short (`network.py`)

`read_timeout` was `0.01` seconds (10ms). Increased to `2.0` seconds for reliability when sending print jobs over the network.

## Printing: label size and rotation

- Label key: `29x90` (not bare `29` which is continuous tape)
- Printable area: **306×991 px** at 300 DPI (portrait: 306 wide, 991 tall)
- Use `rotate="90"` (not `"auto"`) — `auto` did not reliably rotate the image; explicit `"90"` was required for correct output
- The image fed into `convert()` should be portrait 306×991; `rotate="90"` tells brother_ql to rotate it internally before sending to the printer
