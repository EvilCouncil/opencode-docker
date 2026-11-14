# 🐳 opencode-docker

A container image bundling [`opencode-ai`](https://www.npmjs.com/package/opencode-ai) — a local AI coding agent with a headless server, ready to run anywhere Docker runs.

📦 **Image:** `ghcr.io/evilcouncil/opencode-docker`

## ✨ What's inside

- 🟢 Node 22 (slim base)
- 🤖 `opencode-ai` — the agent CLI (server mode on port 4096)
- 🔍 `pyright` — Python type checking for MCP/tooling support
- 📁 `@modelcontextprotocol/server-filesystem` — filesystem MCP server
- 🔎 `mcp-ripgrep` — ripgrep MCP server
- 🛠️ Dev tools: `bash`, `git`, `ripgrep`, `curl`, `python3`

The image runs as a non-root `opencode` user and exposes a `/workspace` directory as the working directory.

## 🚀 Quick start

```bash
docker run -d \
  --name opencode \
  -p 4096:4096 \
  -e UI_PASSWORD=your-secret-password \
  -v $(pwd)/workspace:/workspace \
  ghcr.io/evilcouncil/opencode-docker:latest
```

Then connect via the opencode client:

```bash
opencode --server http://localhost:4096
```

### 🔐 Setting the UI password

The `--ui-password` flag is populated from the `UI_PASSWORD` environment variable at container start:

```bash
-e UI_PASSWORD=your-secret-password
```

> ⚠️ **Heads up:** if `UI_PASSWORD` isn't set, the container falls back to the literal string `password`. Always set it explicitly.

## 🐙 Using with Docker Compose

```yaml
services:
  opencode:
    image: ghcr.io/evilcouncil/opencode-docker:latest
    container_name: opencode
    ports:
      - "4096:4096"
    environment:
      - UI_PASSWORD=your-secret-password
    volumes:
      - ./workspace:/workspace
    restart: unless-stopped
```

## 🏷️ Image tags

| Tag | Description |
|-----|-------------|
| `latest` | 🌟 Most recent stable release |
| `vX.Y.Z` | 📌 Pinned release version (e.g. `v1.0.0`) |

Pre-release tags (e.g. `v1.0.0-rc1`) are published under their own version tag but never update `latest`.

## 🔧 Building locally

```bash
git clone https://github.com/EvilCouncil/opencode-docker.git
cd opencode-docker
docker build -t opencode-docker:local .
```

## 🤖 CI/CD

Pushing a `v*` git tag triggers a [GitHub Actions workflow](.github/workflows/build.yml) that builds the image for `linux/amd64` and publishes it to GHCR:

```bash
git tag v1.1.0
git push origin v1.1.0
```

## 📄 License

See the upstream [`opencode-ai`](https://www.npmjs.com/package/opencode-ai) package for its license.
