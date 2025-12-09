# Verification Quick Reference

## Common Commands

```bash
# Full verification with tests
./verification.sh --test

# Just run tests (skip restart)
./verification.sh --no-restart --test

# Just restart and verify (no tests)
./verification.sh

# Run specific test file
./verification.sh --test backend/test_selenium_login.py
```

## What Gets Checked

### Automatic Pre-Flight Checks (New!)

1. **Disk Space** - Ensures at least 2GB free
2. **Build Logs** - Checks for build errors in `build.log`

### Build Log Errors Detected

- ❌ "no space left on device"
- ❌ "Build command failed"
- ❌ Frontend build failures
- ❌ npm/vite errors

## If Build Fails

### Quick Fix for Disk Space

```bash
# Clean up old images and containers
podman system prune -a

# Or with docker
docker system prune -a

# Check space
df -h /workspace/check-ins

# Trigger rebuild
touch restart.txt

# Monitor
tail -f build.log
```

### Debug Build Failures

```bash
# Check what failed
less build.log

# Search for errors
grep -i error build.log

# Try manual rebuild with live output
podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --build 2>&1 | tee build.log
```

## Log Files

| File | What | How to View |
|------|------|-------------|
| `build.log` | Docker build output | `less build.log` |
| `web.log` | Django runtime | `tail -f web.log` |
| `frontend.log` | Dev server (dev mode only) | `tail -f frontend.log` |

## Typical Workflow

### After Code Changes

```bash
# 1. Touch restart.txt to trigger rebuild
touch restart.txt

# 2. Wait ~30-60 seconds for build

# 3. Run verification with tests
./verification.sh --test
```

### If Tests Fail

```bash
# 1. Check if build succeeded
less build.log

# 2. Check runtime logs
tail -50 web.log

# 3. Check test screenshots
ls -lh /tmp/*.png

# 4. Re-run just tests
./verification.sh --no-restart --test
```

## Exit Codes

- `0` - All checks passed
- `1` - Build errors, disk space, or test failures

## Common Issues

### "Build log not found"

The watcher isn't redirecting output. Update your nushell watch command:

```nushell
watch restart.txt { ||
  podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate --build >build.log 2>&1
}
```

### "Insufficient disk space"

```bash
podman system prune -a
```

### "Build command failed"

Check the full log:
```bash
less build.log
```

Look for the actual error (usually near the end).

### Tests fail but build succeeded

Check runtime logs:
```bash
tail -100 web.log
```

## Help

```bash
./verification.sh --help
```

## See Also

- [BUILD_LOG_CAPTURE.md](./BUILD_LOG_CAPTURE.md) - Detailed build log documentation
- [VERIFICATION_GUIDE.md](./VERIFICATION_GUIDE.md) - Complete verification guide
- [CLAUDE.md](./CLAUDE.md) - Main deployment documentation
