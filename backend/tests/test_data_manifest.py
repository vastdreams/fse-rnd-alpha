"""Regression tests for immutable data-release manifests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from create_data_manifest import build_manifest  # noqa: E402


def _write_release_fixture(data_root: Path) -> None:
    sources = data_root / "saas_ai_repricing"
    sources.mkdir(parents=True)
    (sources / "fundamental_value_run.csv").write_text("ticker,value\nTEST,1\n")
    (sources / "first_principles_overlay.csv").write_text("ticker,overlay\nTEST,ok\n")
    (data_root / "price_history_cache").mkdir()
    (data_root / "price_history_cache" / "TEST_1095.json").write_text('{"bars":[]}\n')
    (data_root / "exports").mkdir()
    (data_root / "exports" / "research.csv").write_text("ticker,score\nTEST,10\n")


def test_manifest_is_content_addressed_and_covers_every_release_file(tmp_path: Path):
    data_root = tmp_path / "data"
    _write_release_fixture(data_root)

    first = build_manifest(
        data_root,
        universe_version="univ_test",
        created_at="2026-07-13T00:00:00+00:00",
    )
    second = build_manifest(
        data_root,
        universe_version="univ_test",
        created_at="2026-07-14T00:00:00+00:00",
    )

    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert "exports/research.csv" in first["files"]
    assert "price_history_cache/TEST_1095.json" in first["files"]

    (data_root / "exports" / "unexpected-runtime-write.json").write_text("{}\n")
    changed = build_manifest(
        data_root,
        universe_version="univ_test",
        created_at=first["created_at"],
    )
    assert changed["manifest_sha256"] != first["manifest_sha256"]


def test_manifest_rejects_release_symlinks(tmp_path: Path):
    data_root = tmp_path / "data"
    _write_release_fixture(data_root)
    target = data_root / "exports" / "research.csv"
    (data_root / "exports" / "linked.csv").symlink_to(target)

    with pytest.raises(ValueError, match="may not contain symlinks"):
        build_manifest(data_root, universe_version="univ_test")
