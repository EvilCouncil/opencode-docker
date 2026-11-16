# 🐳 opencode-docker

A container image bundling **OpenCode v2** (`opencode serve`) alongside `pi-coding-agent`, Go, Terraform, `gh`, and MCP servers — ready to act as a network-accessible AI coding server for laptop CLI/IDE attachments, **OpenChamber**, and **Hermes Agent** orchestration.

📦 **Image:** `ghcr.io/evilcouncil/opencode-docker`

## ✨ What's inside

- 🟢 Node 22 (`node:22-slim` base)
- 🤖 `opencode` v2 standalone binary — runs `opencode serve --hostname 0.0.0.0 --port 4096`
- 🥧 `@earendil-works/pi-coding-agent`, `pi-subagents`, `@firstpick/pi-package-webui`
- 🔧 Go toolchain (`/usr/local/go`) & HashiCorp Terraform (`/usr/local/bin/terraform`)
- 🔍 `pyright`, `@modelcontextprotocol/server-filesystem`, `mcp-ripgrep`
- 🛠️ Dev tools: `bash`, `git`, `gh`, `ripgrep`, `curl`, `tmux`, `python3` (`pip`, `venv`)

The image runs as a non-root `opencode` user (`1000:1000`) with `/workspace` as its working directory.

## 🚀 Quick start

```bash
docker run -d \
  --name opencode \
  -p 4096:4096 \
  -e OPENCODE_SERVER_PASSWORD=your-secret-password \
  -v $(pwd)/workspace:/workspace \
  ghcr.io/evilcouncil/opencode-docker:latest
```

### 💻 Connecting from your laptop

Attach an interactive TUI session from your laptop:

```bash
opencode attach http://<host>:4096 \
  --username opencode \
  --password your-secret-password
```

Or run a one-shot headless prompt (also used by Hermes orchestration):

```bash
opencode run --attach http://<host>:4096 \
  --username opencode \
  --password your-secret-password \
  "Summarize the repository architecture"
```

### 🔐 Authentication & Healthcheck

`opencode serve` enforces HTTP Basic Authentication via `OPENCODE_SERVER_PASSWORD` (username `OPENCODE_SERVER_USERNAME`, default `opencode`). The container entrypoint also accepts `OPENCODE_PASSWORD` and legacy `UI_PASSWORD` as fallbacks.

> ⚠️ **Heads up:** if none of `OPENCODE_SERVER_PASSWORD`, `OPENCODE_PASSWORD`, or `UI_PASSWORD` is set, the container falls back to the literal string `password`. Always set a strong password when exposing port `4096` on the network.

Health endpoint (requires Basic Auth when password-protected):

```bash
curl -sf -u "opencode:your-secret-password" http://localhost:4096/global/health
```

## 🔧 Building & releasing

```bash
make test             # Run unit tests for update_versions.py
make update-versions  # Bump pinned versions from npm
make build            # Build opencode-docker:local
git tag v2.3.0 && git push origin v2.3.0
```
