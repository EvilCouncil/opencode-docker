import json
from unittest.mock import MagicMock, call, patch

import pytest

import update_versions

DOCKERFILE_CONTENT = """\
FROM base AS npm-builder

ARG OPENCODE_VERSION=1.17.4
ARG OPENCHAMBER_VERSION=1.12.4

RUN npm install -g --prefix /npm-global \\
    opencode-ai@${OPENCODE_VERSION} \\
    @openchamber/web@${OPENCHAMBER_VERSION}
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


def mock_latest(monkeypatch, opencode="1.17.4", openchamber="1.12.4"):
    versions = {"opencode-ai": opencode, "@openchamber/web": openchamber}
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
