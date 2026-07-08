# Stage 1: base OS packages
FROM node:20-slim AS base

RUN apt-get update && \
    apt-get install -y bash git ripgrep curl python3 python3-pip python3-venv gh && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/* && \
    usermod -l opencode -d /home/opencode -m node && \
    groupmod -n opencode node

# Stage 2: install npm packages into an isolated prefix
FROM base AS npm-builder

ARG OPENCODE_VERSION=1.17.15
ARG OPENCHAMBER_VERSION=1.14.1
ARG OPENCODE_ORCHESTRATOR_VERSION=1.7.6

RUN npm install -g --prefix /npm-global \
    opencode-ai@${OPENCODE_VERSION} \
    pyright \
    @modelcontextprotocol/server-filesystem \
    @openchamber/web@${OPENCHAMBER_VERSION} \
    opencode-orchestrator@${OPENCODE_ORCHESTRATOR_VERSION}

# Stage 3: runtime image
FROM base

COPY --from=npm-builder /npm-global /npm-global
ENV PATH="/npm-global/bin:$PATH"
# UI_PASSWORD must be supplied at runtime via -e UI_PASSWORD=... or docker-compose environment:
RUN mkdir -p /home/opencode/.config/opencode \
             /home/opencode/.config/openchamber \
             /workspace && \
    chown -R opencode:opencode /home/opencode /workspace

USER opencode
WORKDIR /workspace

EXPOSE 4096

CMD exec openchamber --lan --port 4096 --ui-password "${UI_PASSWORD:-password}" --no-daemon
