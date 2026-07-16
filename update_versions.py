#!/usr/bin/env python3
"""Check npm for latest package versions and update Dockerfile and VERSION."""

import json
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).parent
DOCKERFILE = REPO_ROOT / "Dockerfile"
VERSION_FILE = REPO_ROOT / "VERSION"

PINNED_PACKAGES = ["opencode-ai", "@openchamber/web", "@earendil-works/pi-coding-agent", "pi-subagents", "@firstpick/pi-package-webui"]


def get_latest_version(package: str) -> str:
    encoded = package.replace("/", "%2F")
    url = f"https://registry.npmjs.org/{encoded}/latest"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())["version"]


def main() -> int:
    content = DOCKERFILE.read_text()

    opencode_arg = re.search(r"ARG OPENCODE_VERSION=(\S+)", content)
    openchamber_arg = re.search(r"ARG OPENCHAMBER_VERSION=(\S+)", content)
    pi_arg = re.search(r"ARG PI_CODING_AGENT_VERSION=(\S+)", content)
    pi_subagents_arg = re.search(r"ARG PI_SUBAGENTS_VERSION=(\S+)", content)
    pi_webui_arg = re.search(r"ARG PI_WEBUI_VERSION=(\S+)", content)

    current = {
        "opencode-ai": opencode_arg.group(1) if opencode_arg else None,
        "@openchamber/web": openchamber_arg.group(1) if openchamber_arg else None,
        "@earendil-works/pi-coding-agent": pi_arg.group(1) if pi_arg else None,
        "pi-subagents": pi_subagents_arg.group(1) if pi_subagents_arg else None,
        "@firstpick/pi-package-webui": pi_webui_arg.group(1) if pi_webui_arg else None,
    }

    print("Checking npm for latest versions...")
    latest = {pkg: get_latest_version(pkg) for pkg in PINNED_PACKAGES}

    changed = False

    for pkg, new_ver in latest.items():
        old_ver = current[pkg]
        if new_ver != old_ver:
            print(f"  {pkg}: {old_ver} → {new_ver}")
            changed = True
        else:
            print(f"  {pkg}: {old_ver} (up to date)")

    if not changed:
        print("\nAll packages up to date.")
        return 0

    # Update VERSION file
    if latest["opencode-ai"] != current["opencode-ai"]:
        VERSION_FILE.write_text(latest["opencode-ai"] + "\n")

    # Update Dockerfile ARG defaults
    content = re.sub(
        r"ARG OPENCODE_VERSION=\S+",
        f"ARG OPENCODE_VERSION={latest['opencode-ai']}",
        content,
    )
    content = re.sub(
        r"ARG OPENCHAMBER_VERSION=\S+",
        f"ARG OPENCHAMBER_VERSION={latest['@openchamber/web']}",
        content,
    )
    content = re.sub(
        r"ARG PI_CODING_AGENT_VERSION=\S+",
        f"ARG PI_CODING_AGENT_VERSION={latest['@earendil-works/pi-coding-agent']}",
        content,
    )
    content = re.sub(
        r"ARG PI_SUBAGENTS_VERSION=\S+",
        f"ARG PI_SUBAGENTS_VERSION={latest['pi-subagents']}",
        content,
    )
    content = re.sub(
        r"ARG PI_WEBUI_VERSION=\S+",
        f"ARG PI_WEBUI_VERSION={latest['@firstpick/pi-package-webui']}",
        content,
    )
    DOCKERFILE.write_text(content)

    print("\nUpdated VERSION and Dockerfile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
