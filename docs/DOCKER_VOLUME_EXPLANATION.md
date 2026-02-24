# Docker Volume Layering Explained

## How Named Volumes Enable Hot Reload

### The Problem
When you mount your entire project directory into a Docker container, you want:
- ✅ Your source code changes to be instantly visible (hot reload)
- ❌ Your host's `node_modules` to NOT overwrite the container's dependencies
- ❌ Your host's `.next` build cache to NOT interfere with container builds

### The Solution: Volume Layering

Docker allows you to mount volumes **on top of** other volumes. Later mounts take precedence for their specific paths.

```yaml
volumes:
  - .:/app                              # Mount everything from host
  - node_modules_dev:/app/node_modules  # Override node_modules with named volume
  - nextjs_cache_dev:/app/.next         # Override .next with named volume
```

## How It Works

### Visual Representation

```
┌─────────────────────────────────────────────────────────┐
│  HOST FILESYSTEM                                         │
│  /workspace/check-ins/                                   │
│  ├── src/                 (your code - changes often)    │
│  ├── package.json         (changes occasionally)         │
│  ├── node_modules/        (large, host-specific)        │
│  └── .next/               (build cache, can conflict)   │
└─────────────────────────────────────────────────────────┘
                    │
                    │ Mount: .:/app
                    ▼
┌─────────────────────────────────────────────────────────┐
│  CONTAINER FILESYSTEM                                    │
│  /app/                                                   │
│  ├── src/                 ◄── FROM HOST (hot reload)    │
│  ├── package.json         ◄── FROM HOST (hot reload)    │
│  ├── node_modules/        ◄── FROM NAMED VOLUME (node_modules_dev)
│  └── .next/               ◄── FROM NAMED VOLUME (nextjs_cache_dev)
└─────────────────────────────────────────────────────────┘
```

### Order of Operations

1. **Base Layer**: `.:/app` mounts your entire project
   - Everything from your host appears in `/app`
   - This includes `src/`, `package.json`, `node_modules/`, etc.

2. **Overlay Layer 1**: `node_modules_dev:/app/node_modules`
   - Mounts OVER the `node_modules/` from step 1
   - Hides the host's `node_modules`
   - Shows the container's `node_modules` instead

3. **Overlay Layer 2**: `nextjs_cache_dev:/app/.next`
   - Mounts OVER the `.next/` from step 1
   - Keeps container's build cache separate from host

## Real-World Behavior

### When You Edit a File on Your Host

```bash
# On your host machine
echo "export default function NewComponent() {}" > src/components/New.tsx
```

**What happens:**
1. File appears in host directory: `/workspace/check-ins/src/components/New.tsx`
2. Volume mount `.:/app` makes it instantly visible in container: `/app/src/components/New.tsx`
3. Next.js dev server detects the change (via filesystem watch)
4. Hot reload triggers in browser
5. ✅ **You see your changes instantly!**

**node_modules is NOT affected** because it's protected by the overlay volume.

### When You Install a Package in the Container

```bash
# Inside the container
pnpm add lodash
```

**What happens:**
1. `pnpm` installs `lodash` to `/app/node_modules/lodash`
2. This writes to the `node_modules_dev` named volume
3. Your **host's** `node_modules/` is NOT touched
4. The package persists across container restarts (in the named volume)
5. ✅ **Container keeps its dependencies separate from host!**

## Why Named Volumes Instead of Anonymous Volumes?

### Anonymous Volume (Bad)
```yaml
volumes:
  - .:/app
  - /app/node_modules  # Anonymous - no name
```

**Problems:**
- ❌ Empty on first mount
- ❌ Not reusable across container recreations
- ❌ Hard to inspect or debug
- ❌ Gets deleted when you run `docker-compose down -v`

### Named Volume (Good)
```yaml
volumes:
  - .:/app
  - node_modules_dev:/app/node_modules  # Named - explicitly defined

volumes:
  node_modules_dev:
    driver: local
```

**Benefits:**
- ✅ Persists across container restarts
- ✅ Persists across `docker-compose down` (unless you use `-v`)
- ✅ Easy to inspect: `docker volume ls`, `docker volume inspect node_modules_dev`
- ✅ Can be explicitly managed: `docker volume rm node_modules_dev`
- ✅ Reusable if you recreate containers

## Practical Examples

### Example 1: Adding a New Component

**On your host:**
```bash
# Create new component
cat > src/components/Button.tsx << 'EOF'
export default function Button() {
  return <button>Click me</button>
}
EOF
```

**In the container (automatic):**
- File appears at `/app/src/components/Button.tsx`
- Next.js dev server detects change
- Browser hot reloads with new component
- **No container restart needed!**

### Example 2: Installing Dependencies

**In the container:**
```bash
docker-compose -f docker-compose.dev.yml exec app pnpm add react-icons
```

**What happens:**
- Package installed to `node_modules_dev` volume
- Import works: `import { FaHome } from 'react-icons'`
- **Host's node_modules unchanged**
- Persists even if you restart the container

### Example 3: Updating package.json

**On your host:**
```bash
# Edit package.json to add a new script
vim package.json
```

**In the container:**
- Updated `package.json` visible immediately at `/app/package.json`
- You can run: `docker-compose exec app pnpm install`
- New dependencies install to `node_modules_dev` volume
- **Both host and container stay in sync for source files**

## Filesystem Watch and Hot Reload

### How Next.js Detects Changes

Next.js dev server uses **filesystem watchers** (like `fs.watch` or `chokidar`) to monitor files:

```javascript
// Simplified: What Next.js does internally
const watcher = fs.watch('/app/src', { recursive: true }, (event, filename) => {
  if (filename.endsWith('.tsx') || filename.endsWith('.ts')) {
    console.log('File changed:', filename)
    triggerHotReload()
  }
})
```

### Volume Mounts Support File Watching

Docker volume mounts **propagate filesystem events** from host to container:

1. You edit `src/app/page.tsx` on your host
2. Host OS generates an `inotify` event (Linux) or `FSEvents` (macOS)
3. Docker propagates this event through the volume mount
4. Container's filesystem sees the change
5. Next.js watcher detects the event
6. Hot reload triggers

**This is why hot reload works seamlessly!**

## Common Questions

### Q: Why not just use the host's node_modules?

**A:** Host and container have different environments:

| Aspect | Host (macOS/Windows) | Container (Linux Alpine) |
|--------|---------------------|--------------------------|
| OS | macOS/Windows | Linux |
| Architecture | x86_64/arm64 | x86_64/arm64 |
| Node version | Might differ | Exact version in Dockerfile |
| Binary dependencies | Compiled for host OS | Compiled for Alpine Linux |

**Example issue:**
- `bcrypt` has native bindings
- Host macOS builds: `bcrypt_lib.node` for macOS
- Container needs: `bcrypt_lib.node` for Linux Alpine
- ❌ **They are NOT compatible!**

### Q: Does the overlay slow down file access?

**A:** Negligible performance impact:

- Docker's volume mount system is very fast (uses bind mounts internally)
- Overlay mounts are just additional mount points
- No data copying occurs
- Read/write performance is near-native

**Benchmark (approximate):**
- No volumes: ~1000 ops/sec
- With overlays: ~950 ops/sec
- **Impact: ~5% slower, barely noticeable**

### Q: What happens if I delete node_modules on my host?

**A:** Nothing! The container is isolated:

```bash
# On host
rm -rf node_modules

# Container is unaffected
docker-compose exec app ls /app/node_modules
# Shows: react, next, etc. (still there!)
```

The container's `node_modules` lives in the `node_modules_dev` volume, completely separate from your host.

### Q: How do I update dependencies?

**Option 1: Inside the container (recommended)**
```bash
docker-compose -f docker-compose.dev.yml exec app pnpm add new-package
```

**Option 2: Rebuild the container**
```bash
# Update package.json on host
vim package.json

# Rebuild container (slow but thorough)
docker-compose -f docker-compose.dev.yml up --build
```

### Q: How do I reset node_modules if something breaks?

```bash
# Remove the named volume
docker-compose -f docker-compose.dev.yml down
docker volume rm check-ins_node_modules_dev

# Restart - will reinstall fresh
docker-compose -f docker-compose.dev.yml up --build
```

## Debugging Tips

### Inspect What's in a Volume

```bash
# List all volumes
docker volume ls

# Inspect a specific volume
docker volume inspect check-ins_node_modules_dev

# See actual contents (run a temporary container)
docker run --rm -v check-ins_node_modules_dev:/data alpine ls -la /data
```

### Check File Ownership

```bash
# Inside the container
docker-compose -f docker-compose.dev.yml exec app ls -la /app

# You should see:
# drwxr-xr-x  node_modules   (from volume)
# drwxr-xr-x  src            (from host mount)
```

### Verify Hot Reload Is Working

```bash
# Terminal 1: Watch container logs
docker-compose -f docker-compose.dev.yml logs -f app

# Terminal 2: Edit a file
echo "// test change" >> src/app/page.tsx

# Terminal 1 should show:
# Compiled /app/src/app/page.tsx in XXXms
```

## Summary

**Volume layering is the key technology that enables:**

1. ✅ **Hot reload** - Source code changes are instantly visible
2. ✅ **Isolation** - Container dependencies stay separate from host
3. ✅ **Persistence** - Dependencies survive container restarts
4. ✅ **Cross-platform** - Works on macOS, Windows, Linux hosts
5. ✅ **Performance** - Near-native filesystem access speed

**The magic:**
- Base mount (`.:/app`) provides your live source code
- Overlay mounts protect specific directories from being overwritten
- Both work together seamlessly for the perfect dev experience!
