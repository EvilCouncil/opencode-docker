# Agent Instructions

`opencode-docker` builds a Docker image bundling **OpenCode v2** (`opencode serve`) + `pi-coding-agent` + Go + Terraform + MCP tools into a network-accessible coding server container. Standalone project — publishes to `ghcr.io/evilcouncil/opencode-docker` and serves as the shared coding backend for laptop `opencode attach` clients, `openchamber-docker`, and `hermes-docker` in `EvilCouncil/local_ai_stack`.

## Key Files

| File | Purpose |
|------|---------|
| `Dockerfile` | 4-stage build: OS deps → Go toolchain → npm tools + OpenCode v2 binary → runtime |
| `VERSION` | Pinned OpenCode version (mirrors `OPENCODE_VERSION` ARG) |
| `update_versions.py` | Checks npm (`@opencode/cli`, `pi-*`) for newer packages, rewrites `Dockerfile` + `VERSION` |
| `check_build.py` | Verify build status (GHCR tag + CI run for any tag) |
| `test_update_versions.py` | Unit tests for `update_versions.py` |
| `.github/workflows/build.yml` | Tag-triggered: builds `linux/amd64` image, pushes to GHCR, cuts GitHub Release |
| `.github/workflows/notify-on-failure.yml` | Opens issues on CI failures (deduped by title) |
| `.github/workflows/update-versions.yml` | Weekly cron + manual: opens PR when npm updates exist |
| `Makefile` | Dev tasks (see below) |

## Commands

```bash
make build            # Build the image locally
make run              # Run on :4096 (uses OPENCODE_SERVER_PASSWORD / OPENCODE_PASSWORD / UI_PASSWORD)
make shell            # Shell into running container
make test             # Run pytest on update_versions.py
make update-versions  # Check npm for newer packages → rewrite Dockerfile + VERSION
make check-build      # Verify GHCR tag + CI build status (TAG=v2.3.0 for specific tag)
make clean            # Remove local image + Python cache
```

## Version Bumps & Releases

Run `make update-versions && make test`, commit, then tag and push to trigger CI:

```bash
git tag v2.3.0 && git push origin v2.3.0
```

- Tags follow `v<OPENCODE_VERSION>` (or `v<OPENCODE_VERSION>.<N>` for image-only rebuilds).
- **Only tag when `Dockerfile` actually changed** — it is the only file contributing to the built image.
- CI reads `OPENCODE_VERSION` from `Dockerfile` via `grep -oP`, so do not rename `ARG OPENCODE_VERSION=...` without updating `.github/workflows/build.yml` and `update_versions.py`.
- `notify-on-failure.yml` watches workflow `name:` values (`"Build and Push Docker Image"`, `"Check for opencode updates"`).

## Patterns & Gotchas

- **Base image is `node:22-slim`** — required by `@earendil-works/pi-coding-agent` (`node >= 22.19.0`).
- **Direct OpenCode v2 binary install + fail-fast check**: `update_versions.py` queries `@opencode/cli` on npm for version numbers, while `Dockerfile` downloads `https://opencode.ai/files/bin/${OPENCODE_VERSION}/opencode-linux-x64.tar.gz` directly and asserts `test "$(/npm-global/bin/opencode --version)" = "opencode v${OPENCODE_VERSION}"`.
- **Auth env vars (`OPENCODE_SERVER_PASSWORD`)**: OpenCode v2 `opencode serve` reads `OPENCODE_SERVER_PASSWORD` and `OPENCODE_SERVER_USERNAME` (default `opencode`) for HTTP Basic Auth. If `OPENCODE_SERVER_PASSWORD` is unset, OpenCode v2 generates a random password; therefore `CMD` normalizes `OPENCODE_SERVER_PASSWORD="${OPENCODE_SERVER_PASSWORD:-${OPENCODE_PASSWORD:-${UI_PASSWORD:-password}}}"` and also exports `OPENCODE_PASSWORD` for compatibility.
- **Healthcheck requires Basic Auth**: `/global/health` is gated by Basic Auth when `OPENCODE_SERVER_PASSWORD` is set (`curl -sf -u "$OPENCODE_SERVER_USERNAME:$OPENCODE_SERVER_PASSWORD" http://localhost:4096/global/health`).
- **MCP servers** (`@modelcontextprotocol/server-filesystem`, `mcp-ripgrep`) belong in Stage 3 (`npm-builder`), not Stage 4.
