#!/usr/bin/env python3
"""Fail closed when a restored investor-data tree differs from its manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from create_data_manifest import build_legacy_manifest, build_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()

    expected = json.loads(args.manifest.read_text())
    schema_version = expected.get("schema_version")
    if schema_version not in (1, 2):
        raise SystemExit(f"Unsupported manifest schema: {expected.get('schema_version')!r}")
    if not expected.get("manifest_sha256"):
        raise SystemExit("Manifest has no manifest_sha256")

    builder = build_legacy_manifest if schema_version == 1 else build_manifest
    actual = builder(
        args.data_dir,
        universe_version=expected.get("universe_version"),
        created_at=expected.get("created_at"),
    )
    if actual["manifest_sha256"] != expected["manifest_sha256"]:
        raise SystemExit(
            "Data manifest mismatch: restored files do not match the release artifact "
            f"(expected {expected['manifest_sha256']}, got {actual['manifest_sha256']})."
        )
    print(f"Verified data manifest {actual['manifest_sha256']}")


if __name__ == "__main__":
    main()
