---
name: Bug report
about: Report a problem with Tryggare
title: "[Bug] "
labels: bug
assignees: ""
---

## Describe the bug

A clear and concise description of what the bug is.

## Steps to reproduce

1. Go to '...'
2. Click on '...'
3. See error

## Expected behavior

What you expected to happen.

## Actual behavior

What actually happened. Include any error messages shown in the UI or console.

## Environment

- **OS**: (e.g. Ubuntu 24.04, macOS 15, Windows 11)
- **Browser**: (e.g. Chrome 124, Firefox 126, Safari 17)
- **Deployment type**: Docker Compose / Coolify / Other (please specify)
- **Tryggare version / commit**: (e.g. `main` branch, or the git SHA from the image tag)

## Screenshots

If applicable, add screenshots to help explain the problem.

## Relevant logs

Paste any relevant log output here. For Docker deployments:

```
# Backend logs
docker compose logs web --tail=50

# Or for production
docker compose -f docker-compose.prod.yml logs web --tail=50
```

<details>
<summary>Log output</summary>

```
paste logs here
```

</details>
