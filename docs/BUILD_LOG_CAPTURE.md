# Build Log Capture and Verification

## Overview

The verification script now automatically checks `build.log` for build errors before running tests, helping catch issues like "no space left on device" that would otherwise cause silent failures.

## How It Works

### 1. Auto-Rebuild with Log Capture (Recommended Setup)

The production deployment uses a file watcher that automatically rebuilds when `restart.txt` changes:

```bash
# In nushell (running in background)
watch restart.txt { ||
  podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate --build >build.log 2>&1
}
```

**Key points:**
- `>build.log` captures stdout
- `2>&1` also captures stderr (where build errors appear)
- Automatic rebuild happens whenever `restart.txt` is modified
- All build output is saved to `build.log` for later inspection

### 2. Manual Rebuild with Log Capture

If you need to manually rebuild:

```bash
podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --build 2>&1 | tee build.log
```

**Using `tee`:**
- Shows output in real-time
- Also saves to `build.log`
- Useful for debugging build issues

## Verification Script Checks

When you run `./verification.sh`, it now:

### Pre-Flight Checks (New!)

1. **Disk Space Check**
   ```bash
   ✅ Sufficient disk space available (15GB)
   ```
   - Requires at least 2GB free
   - Shows current available space
   - Suggests cleanup commands if insufficient

2. **Build Log Verification**
   ```bash
   ✅ Build completed successfully
      Last build message: Successfully built 1a2b3c4d5e6f
   ```
   - Checks last 500 lines of `build.log`
   - Looks for common error patterns
   - Verifies successful completion

### Common Build Errors Detected

#### 1. No Space Left on Device
```
❌ DISK SPACE ERROR: No space left on device
ℹ️  Action required: Free up disk space and rebuild
ℹ️  Cleanup commands:
   docker system prune -a
   podman system prune -a
```

**Resolution:**
```bash
# Clean up old images and containers
podman system prune -a

# Verify space
df -h /workspace/check-ins

# Trigger rebuild
touch restart.txt

# Monitor rebuild
tail -f build.log
```

#### 2. Build Command Failed
```
❌ BUILD FAILED: Docker/Podman build command failed
ℹ️  Check the full build log: less build.log
```

**Common causes:**
- Network timeout downloading dependencies
- npm/vite build errors in frontend
- Docker daemon issues
- Permission problems

**Resolution:**
```bash
# Check full log
less build.log

# Look for specific errors
grep -i error build.log

# Try manual rebuild to see real-time output
podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --build 2>&1 | tee build.log
```

#### 3. Frontend Build Failures
```
ERROR: process "/bin/sh -c npm run build" did not complete successfully
```

**Common causes:**
- TypeScript compilation errors
- Missing dependencies
- Vite build configuration issues
- Out of memory during build

**Resolution:**
```bash
# Check frontend-specific errors
grep -A 10 "npm run build" build.log

# Test frontend build locally
cd frontend
npm run build

# If it works locally, might be memory issue in container
# Check docker/podman memory limits
```

## Log Files Summary

| Log File | Purpose | When Written | How to View |
|----------|---------|--------------|-------------|
| `build.log` | Docker/Podman build output | On rebuild (auto or manual) | `less build.log` |
| `web.log` | Django runtime logs | During server operation | `tail -f web.log` |
| `frontend.log` | SvelteKit dev server logs | Development mode only | `tail -f frontend.log` |

## Best Practices

### 1. Monitor Build Logs During Development

```bash
# In one terminal, watch the build log
tail -f build.log

# In another terminal, trigger rebuild
touch restart.txt
```

### 2. Check Logs Before Running Tests

```bash
# The verification script does this automatically
./verification.sh --test

# Or check manually
less build.log
```

### 3. Regular Disk Space Monitoring

```bash
# Check space
df -h /workspace/check-ins

# If getting low, clean up
podman system prune -a

# Remove dangling images
podman image prune -a
```

### 4. Troubleshooting Failed Builds

```bash
# Step 1: Check what failed
grep -i "error\|failed" build.log

# Step 2: Check available space
df -h

# Step 3: If space is low, clean up
podman system prune -a

# Step 4: Try manual rebuild with real-time output
podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --build 2>&1 | tee build.log

# Step 5: If still failing, check specific errors
less build.log
```

## Verification Script Output

### Successful Run
```bash
$ ./verification.sh --test

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Check-Ins System Verification
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ️  Configuration:
   Project Root: /workspace/check-ins
   Timeout:      60s
   Run Tests:    true
   Skip Restart: false

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 Pre-Flight Checks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▶ Checking available disk space...
ℹ️  Available disk space: 15GB
✅ Sufficient disk space available (15GB)

▶ Checking build logs for errors...
✅ Build completed successfully
   Last build message: Successfully built 1a2b3c4d5e6f

[... rest of verification ...]
```

### Failed Build Detected
```bash
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 Pre-Flight Checks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▶ Checking available disk space...
ℹ️  Available disk space: 1GB
❌ Insufficient disk space! Available: 1GB, Required: 2GB minimum
ℹ️  Please free up disk space before building
ℹ️  Common cleanup commands:
   docker system prune -a
   podman system prune -a

❌ Pre-flight checks failed: insufficient disk space
```

## Integration with CI/CD

If you set up CI/CD, ensure build logs are captured:

```yaml
# Example GitHub Actions
- name: Build and Test
  run: |
    ./verification.sh --test 2>&1 | tee verification.log

- name: Upload logs on failure
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: build-logs
    path: |
      build.log
      web.log
      verification.log
```

## FAQ

**Q: Where is build.log created?**
A: In the project root: `/workspace/check-ins/build.log`

**Q: Does verification.sh work without build.log?**
A: Yes, it will warn that the log is missing but won't fail.

**Q: How often should I check build.log?**
A: The verification script checks it automatically. Manually review if builds seem slow or tests fail unexpectedly.

**Q: Can I clear build.log?**
A: Yes, it will be recreated on next build. Or use `> build.log` to truncate it.

**Q: What if the watcher isn't redirecting to build.log?**
A: Update your nushell watch command to include `>build.log 2>&1`

## Summary

The build log capture feature helps catch build failures early by:

1. ✅ Automatically capturing all build output
2. ✅ Checking for common errors before tests run
3. ✅ Providing specific remediation steps
4. ✅ Monitoring disk space proactively
5. ✅ Giving clear feedback about build status

This prevents wasting time running tests against a failed build and helps quickly identify why builds fail.
