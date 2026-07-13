#!/usr/bin/env python3
"""Create a deterministic, checksummed summary of one sealed research build.

The output deliberately contains only stable database metadata and table
fingerprints. It is small enough to travel with a staged data artifact while
still proving that the artifact was produced from the exact sealed research
records it names. Full database backups remain the rollback mechanism.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


SNAPSHOT_SQL = r"""
SELECT jsonb_build_object(
    'universe_build',
    (
        SELECT to_jsonb(build_row)
          FROM (
              SELECT universe_version, input_sha256, manifest, parent_version,
                     engine_version, created_at, sealed_at, status,
                     data_manifest_sha256, source_sha
                FROM universe_builds
               WHERE universe_version = :'universe_version'
          ) AS build_row
    ),
    'tables',
    jsonb_build_object(
        'metric_vectors',
        jsonb_build_object(
            'rows', (
                SELECT count(*)
                  FROM metric_vectors
                 WHERE universe_version = :'universe_version'
            ),
            'content_md5', (
                SELECT md5(
                    COALESCE(
                        jsonb_agg(to_jsonb(vector_row) ORDER BY vector_row.ticker)::text,
                        '[]'
                    )
                )
                  FROM (
                      SELECT *
                        FROM metric_vectors
                       WHERE universe_version = :'universe_version'
                  ) AS vector_row
            )
        ),
        'ranked_rows',
        jsonb_build_object(
            'rows', (
                SELECT count(*)
                  FROM ranked_rows
                 WHERE universe_version = :'universe_version'
            ),
            'content_md5', (
                SELECT md5(
                    COALESCE(
                        jsonb_agg(
                            to_jsonb(rank_row)
                            ORDER BY rank_row.recipe_key, rank_row.ticker
                        )::text,
                        '[]'
                    )
                )
                  FROM (
                      SELECT *
                        FROM ranked_rows
                       WHERE universe_version = :'universe_version'
                  ) AS rank_row
            )
        ),
        'rank_recipes',
        jsonb_build_object(
            'rows', (
                SELECT count(*)
                  FROM rank_recipes AS recipe
                  JOIN (
                      SELECT DISTINCT recipe_key
                        FROM ranked_rows
                       WHERE universe_version = :'universe_version'
                  ) AS used_recipe
                    ON used_recipe.recipe_key = recipe.recipe_key
            ),
            'content_md5', (
                SELECT md5(
                    COALESCE(
                        jsonb_agg(to_jsonb(recipe_row) ORDER BY recipe_row.recipe_key)::text,
                        '[]'
                    )
                )
                  FROM (
                      SELECT recipe.*
                        FROM rank_recipes AS recipe
                        JOIN (
                            SELECT DISTINCT recipe_key
                              FROM ranked_rows
                             WHERE universe_version = :'universe_version'
                        ) AS used_recipe
                          ON used_recipe.recipe_key = recipe.recipe_key
                  ) AS recipe_row
            )
        ),
        'gate_evaluations',
        jsonb_build_object(
            'rows', (
                SELECT count(*)
                  FROM gate_evaluations
                 WHERE universe_version = :'universe_version'
            ),
            'content_md5', (
                SELECT md5(
                    COALESCE(
                        jsonb_agg(
                            to_jsonb(gate_row) - 'id'
                            ORDER BY gate_row.ticker, gate_row.gate_id,
                                     gate_row.evaluated_at, gate_row.id
                        )::text,
                        '[]'
                    )
                )
                  FROM (
                      SELECT *
                        FROM gate_evaluations
                       WHERE universe_version = :'universe_version'
                  ) AS gate_row
            )
        ),
        'deepseek_audit_runs',
        jsonb_build_object(
            'rows', (
                SELECT count(*)
                  FROM deepseek_audit_runs
                 WHERE universe_version = :'universe_version'
            ),
            'content_md5', (
                SELECT md5(
                    COALESCE(
                        jsonb_agg(to_jsonb(run_row) ORDER BY run_row.run_id)::text,
                        '[]'
                    )
                )
                  FROM (
                      SELECT *
                        FROM deepseek_audit_runs
                       WHERE universe_version = :'universe_version'
                  ) AS run_row
            )
        ),
        'final_reviews',
        jsonb_build_object(
            'rows', (
                SELECT count(*)
                  FROM final_reviews
                 WHERE universe_version = :'universe_version'
            ),
            'content_md5', (
                SELECT md5(
                    COALESCE(
                        jsonb_agg(to_jsonb(review_row) ORDER BY review_row.review_id)::text,
                        '[]'
                    )
                )
                  FROM (
                      SELECT *
                        FROM final_reviews
                       WHERE universe_version = :'universe_version'
                  ) AS review_row
            )
        ),
        'audit_trail_entries',
        jsonb_build_object(
            'rows', (
                SELECT count(*)
                  FROM audit_trail_entries
                 WHERE universe_version = :'universe_version'
            ),
            'content_md5', (
                SELECT md5(
                    COALESCE(
                        jsonb_agg(
                            to_jsonb(audit_row) - 'id'
                            ORDER BY audit_row.ticker, audit_row.axis,
                                     audit_row.generated_at, audit_row.id
                        )::text,
                        '[]'
                    )
                )
                  FROM (
                      SELECT *
                        FROM audit_trail_entries
                       WHERE universe_version = :'universe_version'
                  ) AS audit_row
            )
        ),
        'universe_evidence_refs',
        jsonb_build_object(
            'rows', (
                SELECT count(*)
                  FROM universe_evidence_refs
                 WHERE universe_version = :'universe_version'
            ),
            'content_md5', (
                SELECT md5(
                    COALESCE(
                        jsonb_agg(to_jsonb(ref_row) ORDER BY ref_row.claim_id)::text,
                        '[]'
                    )
                )
                  FROM (
                      SELECT *
                        FROM universe_evidence_refs
                       WHERE universe_version = :'universe_version'
                  ) AS ref_row
            )
        ),
        'evidence_claims',
        jsonb_build_object(
            'rows', (
                SELECT count(*)
                  FROM evidence_claims AS claim
                  JOIN universe_evidence_refs AS ref
                    ON ref.claim_id = claim.claim_id
                 WHERE ref.universe_version = :'universe_version'
            ),
            'content_md5', (
                SELECT md5(
                    COALESCE(
                        jsonb_agg(to_jsonb(claim_row) ORDER BY claim_row.claim_id)::text,
                        '[]'
                    )
                )
                  FROM (
                      SELECT claim.*
                        FROM evidence_claims AS claim
                        JOIN universe_evidence_refs AS ref
                          ON ref.claim_id = claim.claim_id
                       WHERE ref.universe_version = :'universe_version'
                  ) AS claim_row
            )
        ),
        'source_snapshots',
        jsonb_build_object(
            'rows', (
                SELECT count(*)
                  FROM (
                      SELECT DISTINCT snapshot.snapshot_id
                        FROM source_snapshots AS snapshot
                        JOIN evidence_claims AS claim
                          ON claim.snapshot_id = snapshot.snapshot_id
                        JOIN universe_evidence_refs AS ref
                          ON ref.claim_id = claim.claim_id
                       WHERE ref.universe_version = :'universe_version'
                  ) AS snapshot_ids
            ),
            'content_md5', (
                SELECT md5(
                    COALESCE(
                        jsonb_agg(
                            to_jsonb(snapshot_row)
                            ORDER BY snapshot_row.snapshot_id
                        )::text,
                        '[]'
                    )
                )
                  FROM (
                      SELECT DISTINCT snapshot.*
                        FROM source_snapshots AS snapshot
                        JOIN evidence_claims AS claim
                          ON claim.snapshot_id = snapshot.snapshot_id
                        JOIN universe_evidence_refs AS ref
                          ON ref.claim_id = claim.claim_id
                       WHERE ref.universe_version = :'universe_version'
                  ) AS snapshot_row
            )
        )
    )
)::text;
"""


def _canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def collect_snapshot(database_url: str, universe_version: str) -> dict[str, Any]:
    """Return the stable database fingerprint for ``universe_version``."""
    if shutil.which("psql") is None:
        return _collect_snapshot_with_asyncpg(database_url, universe_version)

    # The app's async SQLAlchemy URL is not understood by psql. Preserve the
    # caller's URL for async paths and adapt only this CLI invocation.
    psql_database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    completed = subprocess.run(
        [
            "psql",
            psql_database_url,
            "-X",
            "-A",
            "-t",
            "-v",
            "ON_ERROR_STOP=1",
            "-v",
            f"universe_version={universe_version}",
        ],
        check=False,
        capture_output=True,
        text=True,
        input=SNAPSHOT_SQL,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Could not fingerprint research snapshot: {detail}")

    raw = completed.stdout.strip()
    if not raw:
        raise RuntimeError("Database returned no research snapshot fingerprint")
    try:
        snapshot = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Database returned invalid research snapshot JSON: {raw}") from exc

    build = snapshot.get("universe_build")
    if not isinstance(build, dict):
        raise RuntimeError(f"Unknown universe version: {universe_version}")
    if build.get("status") != "sealed":
        raise RuntimeError(f"Universe version is not sealed: {universe_version}")
    if build.get("universe_version") != universe_version:
        raise RuntimeError("Database returned a mismatched universe version")
    return snapshot


async def _asyncpg_snapshot(database_url: str, universe_version: str) -> str:
    try:
        import asyncpg
    except ImportError as exc:  # pragma: no cover - depends on execution image
        raise RuntimeError("psql or asyncpg is required to fingerprint research data") from exc

    connection = await asyncpg.connect(database_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        # psql's :'variable' quoting is not available through asyncpg. The
        # universe value is parameterized instead, never interpolated.
        value = await connection.fetchval(
            SNAPSHOT_SQL.replace(":'universe_version'", "$1"),
            universe_version,
        )
    finally:
        await connection.close()
    return value if isinstance(value, str) else json.dumps(value)


def _collect_snapshot_with_asyncpg(database_url: str, universe_version: str) -> dict[str, Any]:
    raw = asyncio.run(_asyncpg_snapshot(database_url, universe_version))
    try:
        snapshot = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Database returned invalid research snapshot JSON: {raw}") from exc

    build = snapshot.get("universe_build")
    if not isinstance(build, dict):
        raise RuntimeError(f"Unknown universe version: {universe_version}")
    if build.get("status") != "sealed":
        raise RuntimeError(f"Universe version is not sealed: {universe_version}")
    if build.get("universe_version") != universe_version:
        raise RuntimeError("Database returned a mismatched universe version")
    return snapshot


def build_document(database_url: str, universe_version: str) -> dict[str, Any]:
    """Wrap a stable fingerprint in a SHA-256-addressed release document."""
    snapshot = collect_snapshot(database_url, universe_version)
    document: dict[str, Any] = {
        "schema_version": 1,
        "universe_version": universe_version,
        "snapshot": snapshot,
    }
    document["snapshot_sha256"] = hashlib.sha256(_canonical_json(document)).hexdigest()
    return document


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a checksummed immutable-research database snapshot"
    )
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--universe-version", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("--database-url or DATABASE_URL is required")

    document = build_document(args.database_url, args.universe_version)
    rendered = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
