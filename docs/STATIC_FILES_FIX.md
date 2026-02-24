# Django Static Files Fix for Docker

## Problem

Django admin CSS and other static files were missing when running in Docker with Daphne (ASGI server). Static files only worked with `manage.py runserver` because the development server automatically serves static files.

## Root Cause

1. **Development vs Production**: Django's `runserver` automatically serves static files, but production servers (Daphne, Gunicorn, etc.) do not.
2. **Missing collectstatic**: Static files from Django and installed apps need to be collected into `STATIC_ROOT` before they can be served.
3. **No static file serving**: Without a static file server (nginx) or middleware (WhiteNoise), collected static files won't be accessible.

## Solution

Implemented WhiteNoise middleware to serve static files efficiently from the Django application itself.

### Changes Made

#### 1. Added WhiteNoise Package

**File: `backend/pyproject.toml`**
```toml
dependencies = [
    # ... other dependencies ...
    "whitenoise>=6.7,<7.0",
]
```

#### 2. Configured WhiteNoise Middleware

**File: `backend/config/settings/base.py`**
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Added - must be after SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    # ... rest of middleware ...
]

# Static files configuration
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise storage backend for compression and caching
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

#### 3. Added collectstatic to Docker Startup

**File: `docker-compose.yml`**
```yaml
web:
  command: >-
    sh -c "uv sync --frozen --no-dev &&
    uv run python manage.py collectstatic --noinput &&
    uv run python manage.py migrate --noinput &&
    exec uv run python -m daphne -b 0.0.0.0 -p 8000 config.asgi:application"
```

This ensures:
1. Dependencies are installed
2. Static files are collected from all apps
3. Database migrations are applied
4. Daphne server starts

#### 4. Added Static Files Volume

**File: `docker-compose.yml`**
```yaml
volumes:
  - ./backend:/app
  - backend_venv:/app/.venv
  - static_files:/app/staticfiles  # Persist collected static files

volumes:
  pg_data:
  backend_venv:
  frontend_node_modules:
  static_files:  # Define volume
```

## How Static Files Work Now

### Development Flow
1. Django starts in Docker container
2. `collectstatic` collects all static files into `/app/staticfiles/`
3. WhiteNoise middleware intercepts requests to `/static/*`
4. WhiteNoise serves files directly from `/app/staticfiles/`
5. Files are compressed and cached for efficiency

### Static File Locations
```
Django Admin CSS/JS:
  Source: django/contrib/admin/static/
  Collected to: /app/staticfiles/admin/

Django REST Framework:
  Source: rest_framework/static/
  Collected to: /app/staticfiles/rest_framework/

Custom app static files:
  Source: <app>/static/
  Collected to: /app/staticfiles/<app>/
```

### WhiteNoise Benefits
1. **No separate web server needed**: Serves static files from Django
2. **Compression**: Gzip/Brotli compression for smaller file sizes
3. **Caching**: Far-future cache headers for better performance
4. **Manifest storage**: Cache busting with hashed filenames
5. **Production ready**: Used by many Django applications in production

## Testing

### 1. Rebuild and Restart Containers
```bash
# Stop containers
docker compose down

# Remove old volumes to ensure clean state
docker volume rm check-ins_static_files

# Rebuild and start
docker compose up --build
```

### 2. Verify Static Files Collection
Check the logs for:
```
X static files copied to '/app/staticfiles', Y post-processed.
```

### 3. Test Django Admin
1. Navigate to http://localhost:8000/admin/
2. Admin interface should have proper styling (blue header, proper layout)
3. Check browser console - no 404 errors for CSS/JS files

### 4. Check Static File URLs
Static files should be accessible at:
- Admin CSS: http://localhost:8000/static/admin/css/base.css
- Admin JS: http://localhost:8000/static/admin/js/core.js
- REST Framework: http://localhost:8000/static/rest_framework/css/bootstrap.min.css

## Troubleshooting

### Issue: "Static files not found" after restart
**Cause**: Static files volume was cleared
**Fix**: Run `docker compose exec web python manage.py collectstatic --noinput`

### Issue: "ValueError: Missing staticfiles manifest entry"
**Cause**: WhiteNoise manifest is corrupt or missing
**Fix**:
```bash
docker compose down
docker volume rm check-ins_static_files
docker compose up --build
```

### Issue: Old CSS styles persisting
**Cause**: Browser cache or WhiteNoise cache
**Fix**:
1. Hard refresh browser (Ctrl+Shift+R)
2. Or rebuild containers with `--build` flag

### Issue: Static files work in runserver but not Docker
**Cause**: `collectstatic` not run or WhiteNoise not configured
**Fix**: Verify both are in place (see Solution section above)

## Production Considerations

### Current Setup (Good for Development)
- WhiteNoise serves static files
- Works well for low-to-medium traffic
- Simple deployment

### Alternative for High Traffic (Optional)
For high-traffic production, consider:
1. **nginx as reverse proxy**: nginx serves static files, Django handles dynamic content
2. **CDN**: Upload static files to CDN (S3 + CloudFront)
3. **django-storages**: Serve static files from S3

### Example nginx Configuration (if needed later)
```nginx
location /static/ {
    alias /app/staticfiles/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}

location / {
    proxy_pass http://web:8000;
}
```

## Summary

✅ **WhiteNoise installed and configured**
✅ **collectstatic runs on container startup**
✅ **Static files volume persists across restarts**
✅ **Django admin CSS/JS now work in Docker**

The Django admin interface should now display correctly with all styles and JavaScript working properly!

## Next Steps

After implementing these changes:
1. Run `uv lock` to update the lock file with WhiteNoise
2. Restart containers: `docker compose down && docker compose up --build`
3. Verify Django admin has proper styling at http://localhost:8000/admin/
4. Check that no static file 404 errors appear in browser console
