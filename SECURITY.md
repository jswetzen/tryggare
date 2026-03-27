# Security Policy

## Supported Versions

This project is currently pre-1.0. Security fixes are applied to the latest version on `main`.

| Version | Supported |
|---------|-----------|
| latest (main) | ✅ |

## Reporting a Vulnerability

**Please do not report security vulnerabilities via public GitHub issues.**

Report vulnerabilities privately by emailing **security@swetzen.com**.

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (optional)

You should receive an acknowledgement within 48 hours. We aim to release a fix within 14 days of a confirmed report.

## Scope

This is a self-hosted application. The threat model assumes:
- The server running this app is on a trusted local network or behind a reverse proxy (Traefik/Nginx/Caddy)
- Admin credentials are managed by the deploying organization
- The database is not publicly accessible

**In scope:** Authentication bypasses, privilege escalation, data exposure via the API, CSRF/XSS in the web UI.

**Out of scope:** Vulnerabilities requiring physical access to the server, issues in third-party dependencies (report those upstream), denial-of-service against a self-hosted instance.

## Security Configuration

When deploying, ensure:
- `SECRET_KEY` is set to a random value (`openssl rand -hex 32`)
- `DEBUG=false` in production
- `ALLOWED_HOSTS` is set to your actual hostname (not `*`)
- `SESSION_COOKIE_SECURE=true` and `CSRF_COOKIE_SECURE=true` if serving over HTTPS
- Default `admin` / `admin123` credentials are changed immediately after first login
