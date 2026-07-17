# Agent Instructions

This is `opencode-docker`, a standalone repo (nested under `docker/opencode-docker/` in the homelab monorepo, published separately at `github.com/EvilCouncil/opencode-docker`) that builds a Docker image bundling `opencode-ai` + `@openchamber/web` + `pi-coding-agent` into a ready-to-run coding agent container.

## Key Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build: OS deps → Go toolchain → npm packages → runtime image |
| `VERSION` | Current pinned `opencode-ai` version, kept in sync with the Dockerfile |
| `update_versions.py` | Checks npm registry for newer `opencode-ai` / `@openchamber/web` / `@earendil-works/pi-coding-agent` / `pi-subagents` / `@firstpick/pi-package-webui`, rewrites `Dockerfile` + `VERSION` |
| `test_update_versions.py` | Unit tests for `update_versions.py` (pytest) |
| `.github/workflows/build.yml` | Tag-triggered CI: builds image, pushes to GHCR, cuts a GitHub release |
| `Makefile` | Dev task runner — build/run/test/update-versions/clean |

## Commands

Use the `Makefile` for all common dev tasks — run `make help` for the full list:

```bash
make build            # 🔨 build the image locally
make run              # 🚀 run it on :4096
make shell            # 🐚 shell into the running container
make test             # 🧪 run pytest on update_versions.py
make update-versions  # ⬆️  check npm for newer opencode-ai / @openchamber/web / pi-coding-agent / pi-coding-agent
make clean            # 🧹 remove local image + Python cache
```

## Patterns

- **Version pinning**: `opencode-ai` and `@openchamber/web` versions live in `Dockerfile` `ARG` defaults (`OPENCODE_VERSION`, `OPENCHAMBER_VERSION`). Only these two are checked by `update_versions.py` — other npm packages installed in the `npm-builder` stage are unpinned (`latest` at build time). **Base image**: `node:22-slim` is required because `@earendil-works/pi-coding-agent@0.80.7` requires `node >= 22.19.0`. **Base image**: `node:22-slim` is required because `@earendil-works/pi-coding-agent@0.80.7` requires `node >= 22.19.0`. **Base image**: `node:22-slim` is required because `@earendil-works/pi-coding-agent@0.80.7` requires `node >= 22.19.0`.
- **Fail-fast check**: the Dockerfile asserts the installed `opencode --version` matches `OPENCODE_VERSION` right after install — keep this if adding/changing how opencode is installed. **The ARG default must match the pinned version in the install command** — mismatch causes build failure.
- **Releasing**: tags follow `v<OPENCODE_VERSION>.<N>` (e.g. `v1.17.18`, then `v1.17.18.1`, `v1.17.18.2`...) — bump `N` for image-only changes that don't change the pinned opencode version; start a fresh `vX.Y.Z` when `OPENCODE_VERSION` itself changes. **Only cut a new tag/release when `Dockerfile` actually changed** — it's the only file that contributes to the built image, so changes to `README.md`, `AGENTS.md`, `Makefile`, tests, etc. alone don't warrant a version bump. **After any Dockerfile change, push a new tag to trigger CI:** `git tag v1.18.3.1 && git push origin v1.18.3.1`. **Then verify the build completed** — CI is tag-triggered and won't run on `main` pushes alone. CI reads `OPENCODE_VERSION` straight out of the Dockerfile via `grep`, so don't rename that ARG without updating `.github/workflows/build.yml`.
- **CI failure notifications**: `.github/workflows/notify-on-failure.yml` watches `build.yml` and `update-versions.yml` via `workflow_run` and opens a `ci-failure`-labeled GitHub issue when either fails (deduped by issue title, so repeat failures of the same workflow don't create duplicates). GitHub's `workflow_run` trigger requires exact workflow `name:` values, not filenames — whenever a new workflow file is added to this repo, append its `name:` value to the `workflows:` list in `notify-on-failure.yml` or its failures won't be caught.
- **MCP servers bundled in the image**: installed as global npm packages in the `npm-builder` stage (e.g. `@modelcontextprotocol/server-filesystem`, `mcp-ripgrep`). Add new ones there, not in the runtime stage.
- **Secrets**: `UI_PASSWORD` is the only runtime secret, passed via env var at container start — never bake it into the image.

## Tool Usage

Prefer MCP filesystem/ripgrep tools over Bash for file reads/searches. Use Bash for `docker build`, `git`, and running the Python scripts/tests.
