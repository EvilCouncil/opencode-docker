import json
from unittest.mock import MagicMock, call, patch

import pytest

import update_versions

DOCKERFILE_CONTENT = """\
FROM base AS npm-builder

ARG OPENCODE_VERSION=1.17.4
ARG OPENCHAMBER_VERSION=1.12.4
ARG PI_CODING_AGENT_VERSION=0.50.0
ARG PI_SUBAGENTS_VERSION=0.20.0
ARG PI_WEBUI_VERSION=0.5.0

RUN npm install -g --prefix /npm-global \\
    opencode-ai@${OPENCODE_VERSION} \\
    @openchamber/web@${OPENCHAMBER_VERSION} \\
    @earendil-works/pi-coding-agent@${PI_CODING_AGENT_VERSION} \\
    pi-subagents@${PI_SUBAGENTS_VERSION} \\
    @firstpick/pi-package-webui@${PI_WEBUI_VERSION}
"""


def _urlopen_mock(version: str) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps({"version": version}).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# get_latest_version
# ---------------------------------------------------------------------------


class TestGetLatestVersion:
    def test_returns_version_from_registry(self):
        with patch("urllib.request.urlopen", return_value=_urlopen_mock("1.18.0")):
            assert update_versions.get_latest_version("opencode-ai") == "1.18.0"

    def test_encodes_slash_in_scoped_package(self):
        captured = []

        def fake_urlopen(url, timeout=None):
            captured.append(url)
            return _urlopen_mock("1.13.0")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            update_versions.get_latest_version("@openchamber/web")

        assert len(captured) == 1
        assert "@openchamber%2Fweb" in captured[0]
        assert "@openchamber/web" not in captured[0]

    def test_uses_latest_dist_tag_endpoint(self):
        captured = []

        def fake_urlopen(url, timeout=None):
            captured.append(url)
            return _urlopen_mock("1.17.4")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            update_versions.get_latest_version("opencode-ai")

        assert captured[0].endswith("/latest")


# ---------------------------------------------------------------------------
# main() helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """Temp directory with Dockerfile and VERSION; module globals patched to match."""
    dockerfile = tmp_path / "Dockerfile"
    version_file = tmp_path / "VERSION"
    dockerfile.write_text(DOCKERFILE_CONTENT)
    version_file.write_text("1.17.4\n")
    monkeypatch.setattr(update_versions, "DOCKERFILE", dockerfile)
    monkeypatch.setattr(update_versions, "VERSION_FILE", version_file)
    return {"dockerfile": dockerfile, "version_file": version_file}


def mock_latest(monkeypatch, opencode="1.17.4", openchamber="1.12.4", pi="0.50.0", subagents="0.20.0", webui="0.5.0"):
    versions = {"opencode-ai": opencode, "@openchamber/web": openchamber, "@earendil-works/pi-coding-agent": pi, "pi-subagents": subagents, "@firstpick/pi-package-webui": webui}
    monkeypatch.setattr(
        update_versions, "get_latest_version", lambda pkg: versions[pkg]
    )


# ---------------------------------------------------------------------------
# main() – no changes needed
# ---------------------------------------------------------------------------


class TestMainUpToDate:
    def test_returns_zero(self, repo, monkeypatch):
        mock_latest(monkeypatch)
        assert update_versions.main() == 0

    def test_version_file_unchanged(self, repo, monkeypatch):
        mock_latest(monkeypatch)
        update_versions.main()
        assert repo["version_file"].read_text() == "1.17.4\n"

    def test_dockerfile_unchanged(self, repo, monkeypatch):
        mock_latest(monkeypatch)
        before = repo["dockerfile"].read_text()
        update_versions.main()
        assert repo["dockerfile"].read_text() == before


# ---------------------------------------------------------------------------
# main() – opencode-ai bumped
# ---------------------------------------------------------------------------


class TestMainOpencodeUpdated:
    def test_version_file_updated(self, repo, monkeypatch):
        mock_latest(monkeypatch, opencode="1.18.0")
        update_versions.main()
        assert repo["version_file"].read_text() == "1.18.0\n"

    def test_dockerfile_arg_updated(self, repo, monkeypatch):
        mock_latest(monkeypatch, opencode="1.18.0")
        update_versions.main()
        assert "ARG OPENCODE_VERSION=1.18.0" in repo["dockerfile"].read_text()

    def test_openchamber_arg_preserved(self, repo, monkeypatch):
        mock_latest(monkeypatch, opencode="1.18.0")
        update_versions.main()
        assert "ARG OPENCHAMBER_VERSION=1.12.4" in repo["dockerfile"].read_text()

    def test_returns_zero(self, repo, monkeypatch):
        mock_latest(monkeypatch, opencode="1.18.0")
        assert update_versions.main() == 0


# ---------------------------------------------------------------------------
# main() – @openchamber/web bumped
# ---------------------------------------------------------------------------


class TestMainOpenchamberUpdated:
    def test_dockerfile_arg_updated(self, repo, monkeypatch):
        mock_latest(monkeypatch, openchamber="1.13.0")
        update_versions.main()
        assert "ARG OPENCHAMBER_VERSION=1.13.0" in repo["dockerfile"].read_text()

    def test_opencode_arg_preserved(self, repo, monkeypatch):
        mock_latest(monkeypatch, openchamber="1.13.0")
        update_versions.main()
        assert "ARG OPENCODE_VERSION=1.17.4" in repo["dockerfile"].read_text()

    def test_version_file_not_written(self, repo, monkeypatch):
        mock_latest(monkeypatch, openchamber="1.13.0")
        update_versions.main()
        assert repo["version_file"].read_text() == "1.17.4\n"

    def test_returns_zero(self, repo, monkeypatch):
        mock_latest(monkeypatch, openchamber="1.13.0")
        assert update_versions.main() == 0


# ---------------------------------------------------------------------------
# main() – both bumped
# ---------------------------------------------------------------------------


class TestMainBothUpdated:
    def test_version_file_updated(self, repo, monkeypatch):
        mock_latest(monkeypatch, opencode="1.18.0", openchamber="1.13.0")
        update_versions.main()
        assert repo["version_file"].read_text() == "1.18.0\n"

    def test_both_dockerfile_args_updated(self, repo, monkeypatch):
        mock_latest(monkeypatch, opencode="1.18.0", openchamber="1.13.0")
        update_versions.main()
        content = repo["dockerfile"].read_text()
        assert "ARG OPENCODE_VERSION=1.18.0" in content
        assert "ARG OPENCHAMBER_VERSION=1.13.0" in content

    def test_returns_zero(self, repo, monkeypatch):
        mock_latest(monkeypatch, opencode="1.18.0", openchamber="1.13.0")
        assert update_versions.main() == 0


# ---------------------------------------------------------------------------
# main() – VERSION file out of sync with Dockerfile (rollback scenario)
# ---------------------------------------------------------------------------


class TestMainVersionFileMismatch:
    """Guards against the bug where VERSION diverges from the Dockerfile ARG.

    If someone rolls back the Dockerfile ARG (e.g. to 1.15.12) without also
    updating VERSION (still 1.17.9), the script must treat the Dockerfile ARG
    as the source of truth and correctly detect that a newer npm version exists
    relative to what the Dockerfile declares.
    """

    def test_dockerfile_arg_is_source_of_truth(self, repo, monkeypatch):
        # Simulate rollback: Dockerfile pinned to 1.15.12 but VERSION still says 1.17.9
        repo["dockerfile"].write_text(
            DOCKERFILE_CONTENT.replace("ARG OPENCODE_VERSION=1.17.4", "ARG OPENCODE_VERSION=1.15.12")
        )
        repo["version_file"].write_text("1.17.9\n")

        # npm latest is 1.17.9 — newer than the Dockerfile's pinned 1.15.12
        mock_latest(monkeypatch, opencode="1.17.9")
        update_versions.main()

        # Dockerfile should be updated to the npm latest
        assert "ARG OPENCODE_VERSION=1.17.9" in repo["dockerfile"].read_text()

    def test_version_file_synced_from_dockerfile(self, repo, monkeypatch):
        # Simulate rollback: Dockerfile pinned to 1.15.12 but VERSION still says 1.17.9
        repo["dockerfile"].write_text(
            DOCKERFILE_CONTENT.replace("ARG OPENCODE_VERSION=1.17.4", "ARG OPENCODE_VERSION=1.15.12")
        )
        repo["version_file"].write_text("1.17.9\n")

        mock_latest(monkeypatch, opencode="1.17.9")
        update_versions.main()

        # VERSION file should now reflect npm latest, not the stale 1.17.9 from before
        assert repo["version_file"].read_text() == "1.17.9\n"

    def test_no_update_when_dockerfile_matches_npm(self, repo, monkeypatch):
        # Dockerfile and npm both at 1.15.12; VERSION file is stale but irrelevant
        repo["dockerfile"].write_text(
            DOCKERFILE_CONTENT.replace("ARG OPENCODE_VERSION=1.17.4", "ARG OPENCODE_VERSION=1.15.12")
        )
        repo["version_file"].write_text("1.17.9\n")

        mock_latest(monkeypatch, opencode="1.15.12")
        result = update_versions.main()

        # Nothing to update — Dockerfile already matches npm
        assert result == 0
        assert "ARG OPENCODE_VERSION=1.15.12" in repo["dockerfile"].read_text()
