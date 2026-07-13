#!/usr/bin/env python3
"""Create a content-addressed manifest for deployable investor data artifacts.

The manifest contains paths, counts, byte totals, and SHA-256 values only. It
never serializes source data or credentials. Every regular file that enters
the release tarball is enumerated, so neither an unexpected export nor a
runtime cache mutation can hide outside the checksum.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ARTIFACT_DIRS = (
    "price_history_cache",
    "financials_cache",
    "catalyst_event_cache",
    "filings_cache",
    "company_meta_cache",
    "universe_manifests",
)
EXCLUDED_RELEASE_PATHS = frozenset(
    {
        "release_manifest.json",
        "release_metadata.json",
        "research_snapshot.json",
        "research_records.json",
    }
)
REQUIRED_FILES = (
    "saas_ai_repricing/fundamental_value_run.csv",
    "saas_ai_repricing/first_principles_overlay.csv",
)


def _relative_path(file: Path, data_root: Path) -> str:
    return file.relative_to(data_root).as_posix()


def _release_files(data_root: Path) -> list[Path]:
    files: list[Path] = []
    for candidate in sorted(data_root.rglob("*")):
        relative = _relative_path(candidate, data_root)
        if relative in EXCLUDED_RELEASE_PATHS:
            continue
        if candidate.is_symlink():
            raise ValueError(f"Release data may not contain symlinks: {candidate}")
        if candidate.is_file():
            files.append(candidate)
    return files


def tree_summary(files: list[Path], data_root: Path) -> dict[str, int | str]:
    digest = hashlib.sha256()
    byte_count = 0
    for file in files:
        contents = file.read_bytes()
        byte_count += len(contents)
        digest.update(_relative_path(file, data_root).encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(contents).digest())
    return {"files": len(files), "bytes": byte_count, "sha256": digest.hexdigest()}


def file_inventory(files: list[Path], data_root: Path) -> dict[str, dict[str, int | str]]:
    return {
        _relative_path(file, data_root): {
            "bytes": file.stat().st_size,
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        }
        for file in files
    }


def build_legacy_manifest(
    data_root: Path, *, universe_version: str | None, created_at: str | None
) -> dict:
    """Recreate schema v1 only to restore an already-published legacy artifact."""
    data_root = data_root.resolve()
    required: dict[str, dict[str, int | str]] = {}
    for relative in REQUIRED_FILES:
        file = data_root / relative
        if not file.exists():
            raise ValueError(f"Required source input is missing: {file}")
        required[relative] = {
            "bytes": file.stat().st_size,
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        }

    artifacts: dict[str, dict[str, int | str]] = {}
    for directory in ARTIFACT_DIRS:
        path = data_root / directory
        if not path.exists():
            continue
        legacy_files = [candidate for candidate in sorted(path.rglob("*")) if candidate.is_file()]
        artifacts[directory] = tree_summary(legacy_files, data_root)

    payload = {
        "schema_version": 1,
        "created_at": created_at,
        "universe_version": universe_version,
        "required_sources": required,
        "artifacts": artifacts,
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def build_manifest(
    data_root: Path, *, universe_version: str | None, created_at: str | None = None
) -> dict:
    """Build a stable manifest that can be recreated after a data restore."""

    data_root = data_root.resolve()
    required: dict[str, dict[str, int | str]] = {}
    for relative in REQUIRED_FILES:
        file = data_root / relative
        if not file.exists():
            raise ValueError(f"Required source input is missing: {file}")
        required[relative] = {
            "bytes": file.stat().st_size,
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        }

    files = _release_files(data_root)
    artifacts = {
        directory: tree_summary(
            [
                file
                for file in files
                if _relative_path(file, data_root).startswith(f"{directory}/")
            ],
            data_root,
        )
        for directory in ARTIFACT_DIRS
        if (data_root / directory).exists()
    }
    content = {
        "schema_version": 2,
        "universe_version": universe_version,
        "required_sources": required,
        "artifacts": artifacts,
        "files": file_inventory(files, data_root),
    }
    payload = {
        **content,
        # Release timestamps are useful operational metadata, but excluding
        # them from the digest keeps identical inputs content-addressed.
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA / "release_manifest.json",
        help="Manifest path (default: data/release_manifest.json)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA,
        help="Data root to manifest (default: repository data directory)",
    )
    parser.add_argument("--universe-version", default=None)
    parser.add_argument(
        "--created-at",
        default=None,
        help="ISO timestamp to preserve when reproducing an existing manifest",
    )
    args = parser.parse_args()
    data_root = args.data_dir.resolve()

    try:
        payload = build_manifest(
            data_root,
            universe_version=args.universe_version,
            created_at=args.created_at,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
