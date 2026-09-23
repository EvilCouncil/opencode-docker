#!/usr/bin/env python3
"""Check the build status of opencode-docker.

Verifies:
  1. The latest tag on GHCR
  2. The latest GitHub Actions run for that tag (success/failed/in_progress)
  3. Optionally a specific tag or version

Usage:
  python check_build.py              # check latest tag
  python check_build.py v1.18.25     # check a specific tag
  python check_build.py --version 1.18.25  # check by OPENCODE_VERSION (expands to v1.18.25)
  python check_build.py --all        # show last 5 tags with their statuses
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "EvilCouncil/opencode-docker"
ORG = "evilcouncil"
IMAGE = f"ghcr.io/{ORG}/opencode-docker"
WORKFLOW = "Build and Push Docker Image"

GITHUB_TOKEN = os.environ.get("GH_TOKEN", os.environ.get("GITHUB_TOKEN", ""))


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", os.path.dirname(__file__)] + list(args),
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def gh_api(url: str) -> dict | list | None:
    """GET a GitHub API endpoint, returning parsed JSON or None on failure."""
    req = urllib.request.Request(url)
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.reason}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"  Network error: {e.reason}", file=sys.stderr)
        return None


def ghcr_auth_token() -> str | None:
    """Exchange for an anonymous GHCR pull token."""
    url = f"https://ghcr.io/token?scope=repository:{ORG}/{REPO.split('/')[-1]}:pull"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode())["token"]
    except Exception:
        return None


def ghcr_has_tag(tag: str, token: str | None = None) -> bool:
    """Check if a tag exists on GHCR."""
    if token is None:
        token = ghcr_auth_token()
    if not token:
        print("  [?] Could not obtain GHCR token — skipping image check", file=sys.stderr)
        return False
    url = f"https://ghcr.io/v2/{ORG}/{REPO.split('/')[-1]}/tags/list?n=100"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            tags = json.loads(resp.read().decode())["tags"]
            return tag in tags
    except Exception:
        return False


def get_latest_tag() -> str:
    """Get the newest version tag from git."""
    return run_git("tag", "--sort=-v:refname").split("\n")[0]


def get_version_from_dockerfile() -> str:
    """Read OPENCODE_VERSION from the local Dockerfile."""
    dockerfile = os.path.join(os.path.dirname(__file__), "Dockerfile")
    with open(dockerfile) as f:
        for line in f:
            m = re.search(r"ARG OPENCODE_VERSION=(\S+)", line)
            if m:
                return m.group(1)
    return ""


def fetch_run_details(run_id: int) -> dict | None:
    """Fetch full details for a single workflow run (includes started_at/completed_at)."""
    url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}"
    return gh_api(url)


def check_run(tag: str) -> dict | None:
    """Find the latest workflow_run for a given tag."""
    # Get the commit SHA for this tag
    sha = run_git("rev-list", "-n", "1", tag)
    if not sha:
        return None

    url = (
        f"https://api.github.com/repos/{REPO}/actions/runs"
        f"?head_sha={sha}&per_page=5"
    )
    runs = gh_api(url)
    if not runs or "workflow_runs" not in runs:
        return None

    # Filter to the build workflow
    for run in runs["workflow_runs"]:
        if run.get("name") == WORKFLOW:
            # Fetch full details for started_at/completed_at
            details = fetch_run_details(run["id"])
            return details or run
    return None


def parse_duration(iso: str | None) -> str:
    """Parse an ISO 8601 duration like 'PT2M35S' into '2m35s'."""
    if not iso:
        return "—"
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return iso
    days, hours, minutes, seconds = m.groups()
    parts = []
    if days and int(days):
        parts.append(f"{days}d")
    if hours and int(hours):
        parts.append(f"{hours}h")
    if minutes and int(minutes):
        parts.append(f"{minutes}m")
    if seconds and int(seconds):
        parts.append(f"{seconds}s")
    return "".join(parts) or "0s"


def status_icon(status: str, conclusion: str | None) -> str:
    """Return a unicode icon for the run status."""
    if conclusion == "success":
        return "\U00002705"  # ✅
    if conclusion == "failure":
        return "\U0000274C"  # ❌
    if conclusion == "cancelled":
        return "\U000023F9"  # ⏹
    if conclusion == "skipped":
        return "\U000023F8"  # ⏸
    if status == "in_progress" or status == "queued":
        return "\U0001F504"  # 🔄
    return "  "


def iso_to_seconds(iso: str) -> int:
    """Parse ISO 8601 timestamp to epoch seconds."""
    dt = re.sub(r"Z$", "+00:00", iso)
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(dt)
        return int(dt.timestamp())
    except Exception:
        return 0


def calculate_duration(start_iso: str | None, end_iso: str | None) -> str:
    """Calculate duration between two ISO 8601 timestamps."""
    if not start_iso or not end_iso:
        return "—"
    try:
        from datetime import datetime, timezone
        s = datetime.fromisoformat(re.sub(r"Z$", "+00:00", start_iso))
        e = datetime.fromisoformat(re.sub(r"Z$", "+00:00", end_iso))
        diff = int((e - s).total_seconds())
    except Exception:
        return "—"
    if diff <= 0:
        return "—"
    minutes, seconds = divmod(diff, 60)
    if minutes >= 60:
        hours, minutes = divmod(minutes, 60)
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    return f"{minutes}m {seconds:02d}s"


def check_tag(tag: str) -> None:
    """Check a single tag's build status."""
    version = tag.lstrip("v")
    print(f"Tag: {tag}")
    print(f"  OPENCODE_VERSION: {version}")

    # GHCR check
    token = ghcr_auth_token()
    has_image = ghcr_has_tag(tag, token)
    if has_image:
        print(f"  Image: {IMAGE}:{tag}  \U00002705 present on GHCR")
    else:
        print(f"  Image: {IMAGE}:{tag}  \U0000274C not found on GHCR")

    # CI run check
    run = check_run(tag)
    if run is None:
        print(f"  CI:   \U00002753 no build found (tag may be too new — push triggers CI)")
        return

    icon = status_icon(run["status"], run.get("conclusion"))
    duration = calculate_duration(run.get("created_at"), run.get("updated_at"))
    started = run.get("run_started_at", "")[:19].replace("T", " ")
    html_url = run.get("html_url", "")

    print(f"  CI:   {icon} {run['status']} ({run.get('conclusion', '')})")
    print(f"  Run:  {started} UTC  •  {duration}")
    if html_url:
        print(f"  Link: {html_url}")


def check_all() -> None:
    """Check the last 5 tags."""
    tags = run_git("tag", "--sort=-v:refname").split("\n")[:5]
    for tag in tags:
        if tag:
            check_tag(tag)
            print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Check opencode-docker build status")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("tag", nargs="?", default=None, help="Tag to check (e.g. v1.18.25)")
    group.add_argument("--version", dest="version", help="OPENCODE_VERSION to check (expands to v<version>)")
    group.add_argument("--all", action="store_true", help="Show last 5 tags")
    args = parser.parse_args()

    if args.all:
        check_all()
        return

    tag = args.tag or args.version
    if args.version:
        tag = f"v{args.version}"

    if not tag:
        tag = get_latest_tag()

    # Validate tag format
    if not re.match(r"^v?\d+\.\d+\.\d+\.?\d*$", tag):
        print(f"Error: invalid tag format: {tag}", file=sys.stderr)
        sys.exit(1)

    # Ensure 'v' prefix
    if not tag.startswith("v"):
        tag = f"v{tag}"

    check_tag(tag)


if __name__ == "__main__":
    main()
