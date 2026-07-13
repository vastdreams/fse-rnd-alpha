"""End-to-end checks for portable immutable research-record releases."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from research_release import _export_document, _import_document  # noqa: E402
from research_snapshot import build_document  # noqa: E402


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_POSTGRES_INTEGRATION") != "1",
    reason="requires the ephemeral PostgreSQL service used by CI",
)


def _database_url_for(database_name: str) -> str:
    source_url = os.environ["DATABASE_URL"].replace(
        "postgresql+asyncpg://", "postgresql://"
    )
    parts = urlsplit(source_url)
    return urlunsplit(
        (parts.scheme, parts.netloc, f"/{database_name}", parts.query, parts.fragment)
    )


async def _seed_sealed_release(database_url: str) -> tuple[str, str, str]:
    connection = await asyncpg.connect(database_url)
    universe_version = f"portable_{uuid.uuid4().hex[:24]}"
    source_sha = "a" * 40
    manifest_sha = "b" * 64
    claim_id = f"claim-{uuid.uuid4().hex}"
    snapshot_id = f"snapshot-{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        async with connection.transaction():
            await connection.execute(
                """
                INSERT INTO universe_builds
                    (universe_version, input_sha256, manifest, engine_version,
                     created_at, status, sealed_at, is_active, source_sha,
                     data_manifest_sha256)
                VALUES ($1,$2,$3::jsonb,'portable-release-test',$4,
                        'building',NULL,false,$5,$6)
                """,
                universe_version,
                uuid.uuid4().hex + uuid.uuid4().hex,
                json.dumps({"fixture": "portable-release"}),
                now,
                source_sha,
                manifest_sha,
            )
            await connection.execute(
                """
                INSERT INTO source_snapshots
                    (snapshot_id, kind, ticker, as_of_date, available_date,
                     fetched_at, locator, content_sha256)
                VALUES ($1,'10-K','PORT',$2,$2,$3,
                        'https://example.test/portable',$4)
                """,
                snapshot_id,
                date(2026, 7, 1),
                now,
                "c" * 64,
            )
            await connection.execute(
                """
                INSERT INTO evidence_claims
                    (claim_id, snapshot_id, ticker, field, value_text,
                     excerpt_locator, extractor, extracted_at)
                VALUES ($1,$2,'PORT','fixture_metric','1','item-7',
                        'portable-release-test',$3)
                """,
                claim_id,
                snapshot_id,
                now,
            )
            vector = {
                "ticker": "PORT",
                "universe_version": universe_version,
                "fixture_metric": {"claim_ids": [claim_id]},
            }
            await connection.execute(
                """
                INSERT INTO metric_vectors
                    (ticker, universe_version, computed_at, vector,
                     completeness_grade, kill_active, stale)
                VALUES ('PORT',$1,$2,$3::jsonb,'Incomplete',false,false)
                """,
                universe_version,
                now,
                json.dumps(vector),
            )
            await connection.fetchval(
                "SELECT materialize_universe_evidence_refs($1)", universe_version
            )
            await connection.execute(
                """
                UPDATE universe_builds
                   SET status='sealed', sealed_at=$2
                 WHERE universe_version=$1
                """,
                universe_version,
                now,
            )
            audit_run_id = f"run-{uuid.uuid4().hex}"
            review_id = f"review-{uuid.uuid4().hex}"
            await connection.execute(
                """
                INSERT INTO deepseek_audit_runs
                    (run_id, job, ticker, output_kind, output, model, started_at,
                     finished_at, status, severity, universe_version)
                VALUES ($1,'gap_audit','PORT','ai_gap',$2::jsonb,
                        'portable-release-test',$3,$3,'confirmed','low',$4)
                """,
                audit_run_id,
                json.dumps({"findings": []}),
                now,
                universe_version,
            )
            await connection.execute(
                """
                INSERT INTO final_reviews
                    (review_id, ticker, recipe_id, trigger, checklist, passed,
                     notes, reviewed_at, reviewer, universe_version)
                VALUES ($1,'PORT',NULL,'top_k',$2::jsonb,true,
                        'portable fixture',$3,'portable-release-test',$4)
                """,
                review_id,
                json.dumps({"checks": ["fixture"]}),
                now,
                universe_version,
            )
            await connection.execute(
                """
                INSERT INTO audit_trail_entries
                    (ticker, axis, metric, snapshot_ids, literature,
                     deepseek_run_id, final_review_id, generated_at, universe_version)
                VALUES ('PORT','fixture_metric',$1::jsonb,$2::jsonb,$3::jsonb,
                        $4,$5,$6,$7)
                """,
                json.dumps({"claim_ids": [claim_id]}),
                json.dumps([snapshot_id]),
                json.dumps([]),
                audit_run_id,
                review_id,
                now,
                universe_version,
            )
    finally:
        await connection.close()
    return universe_version, source_sha, manifest_sha


async def _create_empty_schema_database(
    source_url: str, target_name: str
) -> str:
    admin = await asyncpg.connect(source_url)
    try:
        await admin.execute(f'CREATE DATABASE "{target_name}"')
    finally:
        await admin.close()

    target_url = _database_url_for(target_name)
    dump = subprocess.run(
        ["pg_dump", "--schema-only", source_url],
        check=True,
        capture_output=True,
    )
    # Debian's current pg_dump can emit a PostgreSQL 18-only session setting
    # while this release gate deliberately exercises the PostgreSQL 15 target.
    # It is not schema content, so strip only that forward-incompatible prelude
    # before loading the fixture into the supported server version.
    schema_dump = dump.stdout.replace(b"SET transaction_timeout = 0;\n", b"")
    restored = subprocess.run(
        ["psql", target_url, "-v", "ON_ERROR_STOP=1"],
        input=schema_dump,
        capture_output=True,
    )
    if restored.returncode:
        detail = restored.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"Could not restore schema-only fixture database: {detail}")
    return target_url


async def _drop_database(source_url: str, target_name: str) -> None:
    admin = await asyncpg.connect(source_url)
    try:
        await admin.execute(f'DROP DATABASE IF EXISTS "{target_name}"')
    finally:
        await admin.close()


@pytest.mark.asyncio
async def test_research_release_import_rebuilds_and_attests_sealed_universe():
    source_url = os.environ["DATABASE_URL"].replace(
        "postgresql+asyncpg://", "postgresql://"
    )
    universe_version, source_sha, manifest_sha = await _seed_sealed_release(source_url)
    document = await _export_document(source_url, universe_version)
    target_name = f"research_import_{uuid.uuid4().hex[:16]}"

    try:
        target_url = await _create_empty_schema_database(source_url, target_name)
        await _import_document(
            target_url,
            document,
            expected_source_sha=source_sha,
            expected_manifest_sha=manifest_sha,
        )
        imported = build_document(target_url, universe_version)
        assert imported["snapshot_sha256"] == document["database_snapshot_sha256"]

        target = await asyncpg.connect(target_url)
        try:
            active = await target.fetchrow(
                """
                SELECT status, is_active, data_manifest_sha256
                  FROM universe_builds
                 WHERE universe_version=$1
                """,
                universe_version,
            )
            output_counts = await target.fetchrow(
                """
                SELECT
                    (SELECT count(*) FROM deepseek_audit_runs
                      WHERE universe_version=$1) AS audit_runs,
                    (SELECT count(*) FROM final_reviews
                      WHERE universe_version=$1) AS final_reviews,
                    (SELECT count(*) FROM audit_trail_entries
                      WHERE universe_version=$1) AS audit_entries
                """,
                universe_version,
            )
        finally:
            await target.close()
        assert dict(active) == {
            "status": "sealed",
            "is_active": True,
            "data_manifest_sha256": manifest_sha,
        }
        assert dict(output_counts) == {
            "audit_runs": 1,
            "final_reviews": 1,
            "audit_entries": 1,
        }
    finally:
        await _drop_database(source_url, target_name)
