# Deploying Tryggare on Coolify

This guide walks you through deploying the **Tryggare** child check-in system on a self-hosted [Coolify](https://coolify.io) instance. Coolify handles Docker Compose stacks, automatic SSL via Let's Encrypt, and Traefik reverse-proxy routing — so there's less manual server work involved.

---

## 1. Prerequisites

Before you start, make sure you have:

- A VPS or server with **Coolify installed** (see [coolify.io/docs](https://coolify.io/docs) for the one-command install).
- A **domain name** (e.g., `tryggare.yourdomain.com`) with a DNS A record pointing to your server's IP address. DNS changes can take a few minutes to an hour to propagate.
- Your **GitHub repository** URL for the Tryggare project. Coolify will pull and build from it.
- SSH access to your server, or access to Coolify's built-in terminal, for the post-deploy admin setup step.

---

## 2. Add a New Service in Coolify

1. Log into your Coolify dashboard.
2. Click **+ New Resource** (or **Add Service**) from your project or environment.
3. Select **Docker Compose**.
4. Choose **Git Repository** as the source.
5. Paste your repository URL (e.g., `https://github.com/jswetzen/tryggare`).
6. Set the **Compose File** path to:
   ```
   docker-compose.prod.yml
   ```
7. Set the branch to `main` (or whichever branch you deploy from).
8. Click **Save** — Coolify will load the Compose file. Do **not** deploy yet; set up environment variables first.

---

## 3. Environment Variables

In the Coolify UI, find the **Environment Variables** section for your service. Add each variable below. You can paste them as a block if Coolify supports `.env` file paste, or add them one by one.

### Required variables

```env
# Django secret key — must be a long random string, unique to your deployment
SECRET_KEY=replace-with-a-random-string

# Your domain (no protocol, no port, no trailing slash)
ALLOWED_HOSTS=tryggare.yourdomain.com

# Full PostgreSQL connection URL
# db-prod is the internal Docker service name — don't change that hostname
DATABASE_URL=postgresql://checkins_user:yourdbpassword@db-prod:5432/checkins

# Database credentials (must match DATABASE_URL above)
DB_USER=checkins_user
DB_PASSWORD=yourdbpassword
POSTGRES_DB=checkins

# Valkey (Redis-compatible) connection URL with password
VALKEY_URL=redis://:yourredispassword@valkey-prod:6379/0
REDIS_PASSWORD=yourredispassword

# CORS and CSRF — set to your public HTTPS URL
CORS_ALLOWED_ORIGINS=https://tryggare.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://tryggare.yourdomain.com

# Enable secure cookies for HTTPS (required when behind SSL)
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

### Traefik / domain routing variables

Coolify uses Traefik internally. These tell the app to register itself with Traefik:

```env
TRAEFIK_ENABLE=true
TRAEFIK_HOST=tryggare.yourdomain.com
TRAEFIK_ENTRYPOINT=websecure
TRAEFIK_CERTRESOLVER=le
TRAEFIK_NETWORK=traefik
```

### Generating a secure SECRET_KEY

Never use the placeholder value in production. Generate a real one on your local machine or in Coolify's terminal:

```bash
openssl rand -hex 32
```

Copy the output and use it as your `SECRET_KEY` value.

### Generating secure passwords

Do the same for `DB_PASSWORD` and `REDIS_PASSWORD`:

```bash
openssl rand -hex 24
```

Use simple alphanumeric passwords to avoid URL-encoding headaches. If your password contains special characters like `/`, `+`, `=`, or `@`, they must be percent-encoded in the `DATABASE_URL` and `VALKEY_URL` values. For example, a password of `qfON/YM+` becomes `qfON%2FYM%2B` in the URL.

---

## 4. Domain and SSL

Coolify manages Traefik automatically. Once `TRAEFIK_ENABLE=true` and `TRAEFIK_HOST` are set, the app will appear in Traefik's router and Coolify will issue a Let's Encrypt certificate for your domain.

You do **not** need to configure Nginx or Caddy separately.

Make sure:
- Your domain's DNS A record points to the server's IP.
- Port 80 and 443 are open on the server firewall (Coolify needs port 80 for the ACME challenge).
- `TRAEFIK_CERTRESOLVER=le` matches the cert resolver name configured in your Coolify instance (it's `le` by default).

If you're not sure about the Traefik setup in your Coolify instance, check **Settings > Traefik** in the Coolify dashboard.

---

## 5. Deploy

Once environment variables are saved:

1. Click **Deploy** in the Coolify UI.
2. Watch the build log — the first deploy pulls dependencies and builds the SvelteKit frontend inside Docker, so it takes a few minutes.
3. Once all three containers show as **Running** (`web`, `db-prod`, `valkey-prod`), the app is up.
4. Visit `https://tryggare.yourdomain.com` — you should see the login page.

---

## 6. First Run: Create an Admin User

The app has no users by default. You need to create an admin account before anyone can log in.

In the Coolify UI, find your `web` container and open a **terminal** (or use the Exec into container option). Then run:

```bash
uv run python manage.py createsuperuser
```

Follow the prompts to set a username, email, and password. This account can then log into the app and the Django admin panel at `https://tryggare.yourdomain.com/admin`.

---

## 7. Backups

Persistent data lives in the Docker volume `pg_data_prod`. Back it up regularly.

### Manual backup via Coolify terminal

Exec into the `db-prod` container and run:

```bash
pg_dump -U checkins_user checkins > /tmp/checkins-backup.sql
```

Then copy the file out using Coolify's file browser or via `docker cp` from your server.

### Automated backups

Coolify has a **Scheduled Backups** feature for databases. In your Coolify service, look for the **Backups** tab and configure:
- **Type**: PostgreSQL
- **Schedule**: e.g., daily at 2am
- **Retention**: however many days you want to keep

Coolify will store backups in S3-compatible storage if configured, or locally on the server.

### Restoring a backup

Exec into `db-prod` and run:

```bash
psql -U checkins_user checkins < /path/to/checkins-backup.sql
```

---

## 8. Updates

When you push new commits to your repository:

1. Open your service in the Coolify dashboard.
2. Click **Redeploy** (or enable **Auto Deploy** on push if you've set up the Coolify webhook in your GitHub repo).
3. Coolify will pull the latest code, rebuild the Docker image, run database migrations automatically (the entrypoint handles this), and restart the container.

There's no downtime for database or static file changes, but the `web` container itself will restart briefly during a redeploy.

---

## 9. Troubleshooting

### Login redirects to a different port, or the app returns a 400 error

Check `ALLOWED_HOSTS`. It must contain only the hostname — **no port number**.

```env
# Correct
ALLOWED_HOSTS=tryggare.yourdomain.com

# Wrong — will cause "Invalid HTTP_HOST header" errors
ALLOWED_HOSTS=tryggare.yourdomain.com:443
```

### Login works but sessions drop immediately (cookies not saved)

You're likely accessing the app over HTTPS but have `SESSION_COOKIE_SECURE=false`. Set:

```env
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

Then redeploy. Conversely, if you're testing over plain HTTP (not recommended for production), set both to `false`.

### CSRF verification failed / 403 on form submit

`CSRF_TRUSTED_ORIGINS` must match the exact URL your browser uses, including the protocol:

```env
# For HTTPS with Traefik
CSRF_TRUSTED_ORIGINS=https://tryggare.yourdomain.com

# For local HTTP testing (not for real production)
CSRF_TRUSTED_ORIGINS=http://tryggare.yourdomain.com:8080
```

### "502 Bad Gateway" or app not reachable

1. Check that all three containers are running in the Coolify UI.
2. Check the build log for errors (a failed npm/pnpm or pip install will cause the image build to fail silently in some versions).
3. Confirm `TRAEFIK_ENABLE=true` and `TRAEFIK_HOST` matches your domain exactly.
4. Make sure DNS has propagated: `dig tryggare.yourdomain.com` should return your server's IP.

### Database connection errors on startup

Verify that `DATABASE_URL` uses the internal Docker service name `db-prod` (not `localhost`):

```env
DATABASE_URL=postgresql://checkins_user:yourpassword@db-prod:5432/checkins
```

If your password contains special characters, check they are percent-encoded in the URL (the `DB_PASSWORD` variable itself should be unencoded; only the URL value needs encoding).

### Checking logs

In the Coolify UI, click on the `web` container and open the **Logs** tab. Look for Django startup errors, migration output, or Gunicorn/Daphne errors. For the database, open logs on `db-prod`.

---

## Quick Reference: Minimum Required Variables

| Variable | Example Value | Notes |
|---|---|---|
| `SECRET_KEY` | `a3f9...` (64 hex chars) | Generate with `openssl rand -hex 32` |
| `ALLOWED_HOSTS` | `tryggare.yourdomain.com` | Hostname only, no port |
| `DATABASE_URL` | `postgresql://user:pass@db-prod:5432/checkins` | Use `db-prod` as host |
| `DB_USER` | `checkins_user` | Must match DATABASE_URL |
| `DB_PASSWORD` | `strongpassword` | Must match DATABASE_URL |
| `POSTGRES_DB` | `checkins` | Must match DATABASE_URL |
| `VALKEY_URL` | `redis://:pass@valkey-prod:6379/0` | Use `valkey-prod` as host |
| `REDIS_PASSWORD` | `strongpassword` | Must match VALKEY_URL |
| `CORS_ALLOWED_ORIGINS` | `https://tryggare.yourdomain.com` | Must include `https://` |
| `CSRF_TRUSTED_ORIGINS` | `https://tryggare.yourdomain.com` | Must include `https://` |
| `SESSION_COOKIE_SECURE` | `true` | Set `false` only for HTTP testing |
| `CSRF_COOKIE_SECURE` | `true` | Set `false` only for HTTP testing |
| `TRAEFIK_ENABLE` | `true` | Enables Traefik routing |
| `TRAEFIK_HOST` | `tryggare.yourdomain.com` | Domain for Traefik router |
