# QR Code Scanning on Check-in

## Goal

Allow staff to scan a ticket QR code at check-in instead of typing a name.
The QR code encodes the `external_ticket_code` field imported from FestivalPro.

## How it works

1. Staff opens the check-in page and taps "Scan QR"
2. Camera opens and scans the attendee's printed ticket
3. The scanned code is looked up against `external_ticket_code` on `EventTicket` / `SessionTicket`
4. The matching family is found and pre-filled / auto-checked-in

## Implementation

### Backend
- Add a search endpoint (or extend existing family search) to accept `?qr=<code>`
- Look up `EventTicket.external_ticket_code` and `SessionTicket.external_ticket_code`
- Return the family associated with that ticket

### Frontend
- Add a QR scan button to the check-in page
- Use `html5-qrcode` library (an early React prototype lives in git history if needed for reference)
- On scan success: call the lookup endpoint and populate/auto-checkin the family
- Handle not-found gracefully (show error, let staff fall back to name search)

## Dependencies

- `external_ticket_code` must be populated (requires FestivalPro import)
- Planning.Center import would need equivalent ticket code mapping

## Priority

Medium. Speeds up high-traffic check-in lanes significantly.
