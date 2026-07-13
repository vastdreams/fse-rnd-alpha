#!/usr/bin/env python3
"""Atomically promote one sealed research universe to the active release."""

from __future__ import annotations

import argparse
import asyncio
import os
import re

import asyncpg


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha"
    ).replace("postgresql+asyncpg://", "postgresql://")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe-version", required=True)
    parser.add_argument(
        "--data-manifest-sha256",
        required=True,
        help="Content hash of the staged immutable data manifest bound to this build.",
    )
    parser.add_argument(
        "--source-sha",
        default=None,
        help="Deprecated: source SHA is immutable build provenance and cannot be added at activation.",
    )
    args = parser.parse_args()
    if args.source_sha is not None:
        raise SystemExit(
            "--source-sha is not accepted during activation; set RELEASE_SHA before creating the build."
        )
    if not re.fullmatch(r"[0-9a-f]{64}", args.data_manifest_sha256):
        raise SystemExit("--data-manifest-sha256 must be a 64-character SHA-256 digest")

    conn = await asyncpg.connect(database_url())
    try:
        async with conn.transaction():
            # Serialize promotion across release workers. The unique active
            # index remains the final invariant; this lock turns a competing
            # promotion into a clean ordered handoff instead of a retryable
            # unique-index race.
            await conn.execute("SELECT pg_advisory_xact_lock(842183002)")
            build = await conn.fetchrow(
                """SELECT universe_version, status, source_sha, data_manifest_sha256
                   FROM universe_builds
                   WHERE universe_version=$1
                   FOR UPDATE""",
                args.universe_version,
            )
            if build is None:
                raise RuntimeError(f"Unknown universe build: {args.universe_version}")
            if build["status"] != "sealed":
                raise RuntimeError(
                    f"Universe {args.universe_version} is {build['status']}, not sealed"
                )
            if not re.fullmatch(r"[0-9a-f]{40}", build["source_sha"] or ""):
                raise RuntimeError(
                    f"Universe {args.universe_version} has no valid build source SHA and cannot be promoted."
                )
            if (
                build["data_manifest_sha256"] is not None
                and build["data_manifest_sha256"] != args.data_manifest_sha256
            ):
                raise RuntimeError(
                    "The staged manifest does not match the immutable data manifest already "
                    f"bound to universe {args.universe_version}."
                )
            await conn.execute(
                "UPDATE universe_builds SET is_active=false WHERE is_active"
            )
            await conn.execute(
                """UPDATE universe_builds
                   SET is_active=true,
                       data_manifest_sha256=$2
                   WHERE universe_version=$1""",
                args.universe_version,
                args.data_manifest_sha256,
            )
    finally:
        await conn.close()

    print(f"Activated sealed universe {args.universe_version}")


if __name__ == "__main__":
    asyncio.run(main())
