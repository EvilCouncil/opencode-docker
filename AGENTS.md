# Agent Instructions

`opencode-docker` builds a Docker image bundling `opencode-ai` + `@openchamber/web` + `pi-coding-agent` into a coding agent container. Standalone project — publishes to `ghcr.io/evilcouncil/opencode-docker`, not part of the homelab monorepo.

## Key Files

| File | Purpose |
|------|---------|
| `Dockerfile` | 4-stage build: OS deps → Go toolchain → npm install → runtime |
| `VERSION` | Pinned `opencode-ai` version (mirrors `OPENCODE_VERSION` ARG) |
| `update_versions.py` | Checks npm for newer packages, rewrites `Dockerfile` + `VERSION` |
| `check_build.py` | Verify build status (GHCR tag + CI run for any tag) |
| `test_update_versions.py` | Unit tests for `update_versions.py` |
| `.github/workflows/build.yml` | Tag-triggered: builds image, pushes to GHCR, cuts release |
| `.github/workflows/notify-on-failure.yml` | Opens issues on CI failures (deduped by title) |
| `.github/workflows/update-versions.yml` | Weekly cron + manual: opens PR when npm updates exist |
| `Makefile` | Dev tasks (see below) |

## Commands

```bash
make build            # Build the image locally
make run              # Run on :4096 (requires UI_PASSWORD env var)
make shell            # Shell into running container
make test             # Run pytest on update_versions.py
make update-versions  # Check npm for newer packages → rewrite Dockerfile + VERSION
make check-build      # Verify GHCR tag + CI build status (TAG=v1.18.25 for specific tag)
make clean            # Remove local image + Python cache
```

## Version Bumps

Run `make update-versions` to check npm and update pinned versions. Then tag and push to trigger CI:

```bash
git tag v1.18.25 && git push origin v1.18.25
```

- Tags follow `v<OPENCODE_VERSION>.<N>` — bump `N` for image-only changes; start fresh `vX.Y.Z` when `OPENCODE_VERSION` changes
- **Only tag when `Dockerfile` actually changed** — it's the only file contributing to the built image
- CI reads `OPENCODE_VERSION` from the Dockerfile via grep, so don't rename that ARG without updating `.github/workflows/build.yml`

## CI & Releases

- **`build.yml`** triggers on `v*` tags: builds `linux/amd64` image, pushes to GHCR, creates GitHub Release with changelog
- **`update-versions.yml`** runs weekly (Mon 08:00 UTC) and opens PRs via `peter-evans/create-pull-request` when npm has newer versions
- **`notify-on-failure.yml`** watches `build.yml` and `update-versions.yml` via `workflow_run` trigger — use exact workflow `name:` values, not filenames. Adding a new workflow means appending its `name:` to the list or failures won't be caught
- Use `python3 check_build.py` to verify a tag built successfully (GHCR presence + CI status)

## Patterns & Gotchas

- **Base image is `node:22-slim`** — required by `@earendil-works/pi-coding-agent` (needs `node >= 22.19.0`). Do not change to `node:20`.
- **Fail-fast check**: Dockerfile asserts `/npm-global/bin/opencode --version` matches `OPENCODE_VERSION` immediately after install. Keep this if the install method changes. The ARG default must match the version in the install command.
- **MCP servers** (`@modelcontextprotocol/server-filesystem`, `mcp-ripgrep`) are installed as global npm packages in the `npm-builder` stage — add new ones there, not in the runtime stage.
- **`gh` CLI** is pre-installed in the image (via apt in stage 1) — use it for git operations inside the container.
- **`@openchamber/web`** is launched via the `openchamber` binary, not `opencode`. The CMD is `openchamber --lan --port 4096 --ui-password "${UI_PASSWORD:-password}" --no-daemon`.
- **`UI_PASSWORD`** is the only runtime secret — never bake it into the image. Falls back to literal `"password"` if unset (security risk on `--lan`).
- **Only `OPENCODE_VERSION` is passed as a build arg to CI** (`build.yml` reads it from Dockerfile via grep). Other ARGs (`OPENCHAMBER_VERSION`, `PI_CODING_AGENT_VERSION`, etc.) use their Dockerfile defaults at build time.
