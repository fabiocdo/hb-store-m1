from __future__ import annotations

from pathlib import Path
from types import TracebackType
import urllib.request

import pytest

from homebrew_cdn_m1_server.application.gateways import github_assets_gateway as module
from homebrew_cdn_m1_server.application.gateways.github_assets_gateway import (
    GithubAssetsGateway,
)


class _FakeAsset:
    def __init__(self, name: str, url: str) -> None:
        self.name: str = name
        self.browser_download_url: str = url


class _FakeRelease:
    def __init__(self, assets: list[_FakeAsset]) -> None:
        self._assets: list[_FakeAsset] = assets

    def get_assets(self) -> list[_FakeAsset]:
        return self._assets


class _FakeRepo:
    def __init__(self, release: _FakeRelease) -> None:
        self._release: _FakeRelease = release

    def get_releases(self) -> list[_FakeRelease]:
        return [self._release]


class _FakeGithub:
    def __init__(self, repo: _FakeRepo) -> None:
        self._repo: _FakeRepo = repo

    def get_repo(self, _name: str) -> _FakeRepo:
        return self._repo


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload: bytes = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def _patch_fake_github(
    monkeypatch: pytest.MonkeyPatch,
    assets: list[_FakeAsset],
) -> None:
    fake_repo = _FakeRepo(_FakeRelease(assets))

    def _fake_github(timeout: int, retry: int) -> _FakeGithub:
        assert timeout == 10
        assert retry == 0
        return _FakeGithub(fake_repo)

    monkeypatch.setattr(module, "Github", _fake_github)


def _patch_urlopen(monkeypatch: pytest.MonkeyPatch, payload: bytes) -> None:
    def _fake_urlopen(_request: object, timeout: float = 60) -> _FakeResponse:
        assert int(timeout) == 60
        return _FakeResponse(payload)

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)


def test_github_gateway_given_destinations_when_download_then_returns_downloaded_and_missing(
    temp_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_github(
        monkeypatch,
        assets=[
            _FakeAsset("homebrew.elf", "https://example/elf"),
            _FakeAsset("homebrew.elf.sig", "https://example/sig"),
        ],
    )
    _patch_urlopen(monkeypatch, payload=b"sig-bytes")

    existing = temp_workspace / "data" / "share" / "update" / "homebrew.elf"
    existing.parent.mkdir(parents=True, exist_ok=True)
    _ = existing.write_bytes(b"already")

    missing = temp_workspace / "data" / "share" / "update" / "remote.md5"
    to_download = temp_workspace / "data" / "share" / "update" / "homebrew.elf.sig"

    gateway = GithubAssetsGateway()
    downloaded, not_found = gateway.download_latest_release_assets(
        [existing, missing, to_download]
    )

    assert downloaded == [to_download]
    assert not_found == [missing]
    assert to_download.read_bytes() == b"sig-bytes"
    assert to_download.with_suffix(".sig.part").exists() is False


def test_github_gateway_given_no_matching_assets_when_download_then_marks_missing(
    temp_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_github(monkeypatch, assets=[_FakeAsset("other.bin", "https://example/other")])
    _patch_urlopen(monkeypatch, payload=b"unused")

    requested = temp_workspace / "data" / "share" / "update" / "remote.md5"
    gateway = GithubAssetsGateway()

    downloaded, missing = gateway.download_latest_release_assets([requested])

    assert downloaded == []
    assert missing == [requested]
