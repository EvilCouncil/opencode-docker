# Stage 1: base OS packages
FROM node:22-slim AS base

RUN apt-get update && \
    apt-get install -y bash git ripgrep curl python3 python3-pip python3-venv gh tmux && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/* && \
    usermod -l opencode -d /home/opencode -m node && \
    groupmod -n opencode node

# Stage 2: install the official Go toolchain (apt's golang-go is too old)
FROM base AS go-installer

ARG GO_VERSION=1.26.5
ARG GO_SHA256=5c2c3b16caefa1d968a94c1daca04a7ca301a496d9b086e17ad77bb81393f053

RUN curl -fsSL -o /tmp/go.tar.gz "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" && \
    echo "${GO_SHA256}  /tmp/go.tar.gz" | sha256sum -c - && \
    tar -C /usr/local -xzf /tmp/go.tar.gz && \
    rm /tmp/go.tar.gz

# Stage 3: install npm packages into an isolated prefix
FROM base AS npm-builder

ARG OPENCODE_VERSION=1.18.3
ARG OPENCHAMBER_VERSION=1.16.1
ARG PI_CODING_AGENT_VERSION=0.80.7
ARG PI_SUBAGENTS_VERSION=0.34.0
ARG PI_WEBUI_VERSION=0.6.7

RUN npm install -g --prefix /npm-global \
    opencode-ai@${OPENCODE_VERSION} \
    pyright \
    @modelcontextprotocol/server-filesystem \
    mcp-ripgrep \
    @openchamber/web@${OPENCHAMBER_VERSION} \
    @earendil-works/pi-coding-agent@${PI_CODING_AGENT_VERSION} \
    pi-subagents@${PI_SUBAGENTS_VERSION} \
    @firstpick/pi-package-webui@${PI_WEBUI_VERSION}

# Fail fast if a wrong opencode version ends up installed
RUN test "$(/npm-global/bin/opencode --version)" = "${OPENCODE_VERSION}"

# Stage 4: runtime image
FROM base

COPY --from=npm-builder /npm-global /npm-global
COPY --from=go-installer /usr/local/go /usr/local/go
ENV PATH="/usr/local/go/bin:/npm-global/bin:$PATH"
# UI_PASSWORD must be supplied at runtime via -e UI_PASSWORD=... or docker-compose environment:
RUN mkdir -p /home/opencode/.config/opencode \
             /home/opencode/.config/openchamber \
             /workspace && \
    chown -R opencode:opencode /home/opencode /workspace

USER opencode
WORKDIR /workspace

EXPOSE 4096

CMD exec openchamber --lan --port 4096 --ui-password "${UI_PASSWORD:-password}" --no-daemon
