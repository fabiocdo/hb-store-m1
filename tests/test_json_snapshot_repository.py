from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from homebrew_cdn_m1_server.application.repositories.json_snapshot_repository import (
    JsonSnapshotRepository,
)

SNAPSHOT_SCHEMA = Path(__file__).resolve().parents[1] / "init" / "snapshot.schema.json"


def test_json_snapshot_repository_given_snapshot_when_save_then_load_roundtrip(
    temp_workspace: Path,
):
    snapshot_path = temp_workspace / "data" / "internal" / "catalog" / "pkgs-snapshot.json"
    repository = JsonSnapshotRepository(snapshot_path, SNAPSHOT_SCHEMA)

    repository.save(
        {
            "/app/data/share/pkg/game/A.pkg": (100, 200),
            "/app/data/share/pkg/app/B.pkg": (300, 400),
        }
    )

    loaded = repository.load()
    assert loaded == {
        "/app/data/share/pkg/game/A.pkg": (100, 200),
        "/app/data/share/pkg/app/B.pkg": (300, 400),
    }

    raw_obj = cast(object, json.loads(snapshot_path.read_text("utf-8")))
    assert isinstance(raw_obj, dict)
    raw = cast(dict[str, object], raw_obj)
    assert raw == {
        "/app/data/share/pkg/app/B.pkg": [300, 400],
        "/app/data/share/pkg/game/A.pkg": [100, 200],
    }


def test_json_snapshot_repository_given_invalid_snapshot_when_load_then_returns_empty(
    temp_workspace: Path,
):
    snapshot_path = temp_workspace / "data" / "internal" / "catalog" / "pkgs-snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    _ = snapshot_path.write_text(
        '{"bad":[1], "bad2":["oops", 1], "good":[10,20]}',
        encoding="utf-8",
    )

    repository = JsonSnapshotRepository(snapshot_path, SNAPSHOT_SCHEMA)
    assert repository.load() == {}


def test_json_snapshot_repository_given_outdated_schema_when_init_then_raises(
    temp_workspace: Path,
):
    snapshot_path = temp_workspace / "data" / "internal" / "catalog" / "pkgs-snapshot.json"
    bad_schema = temp_workspace / "snapshot.schema.json"
    _ = bad_schema.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="out of sync"):
        _ = JsonSnapshotRepository(snapshot_path, bad_schema)
