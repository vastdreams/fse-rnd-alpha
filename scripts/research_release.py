#!/usr/bin/env python3
"""Export and atomically import the research records for an immutable release.

The cache/data tarball is not a database backup. This tool carries only the
versioned public research graph needed by a sealed universe (and its ancestor
chain), never accounts, sessions, books, or other tenant records. Importing
replays that graph through the normal building -> sealed lifecycle, then
checks the same deterministic snapshot that was staged with the release.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import asyncpg

from research_snapshot import SNAPSHOT_SQL, _canonical_json, build_document


RELEASE_SCHEMA_VERSION = 1
SOURCE_SHA_RE = re.compile(r"[0-9a-f]{40}")
MANIFEST_SHA_RE = re.compile(r"[0-9a-f]{64}")


def _canonical_hash(document: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(document)).hexdigest()


def _decode_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        decoded = json.loads(value)
        if isinstance(decoded, dict):
            return decoded
    raise RuntimeError("Database returned an invalid JSON release row")


def _decode_json_value(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _jsonb(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value is not None else None


async def _json_rows(
    connection: asyncpg.Connection, query: str, *args: Any
) -> list[dict[str, Any]]:
    rows = await connection.fetch(query, *args)
    return [_decode_json(row["payload"]) for row in rows]


async def _export_document(database_url: str, universe_version: str) -> dict[str, Any]:
    connection = await asyncpg.connect(database_url)
    try:
        builds = await _json_rows(
            connection,
            """
            WITH RECURSIVE lineage(universe_version, depth) AS (
                SELECT universe_version, 0
                  FROM universe_builds
                 WHERE universe_version = $1
                UNION ALL
                SELECT build.parent_version, lineage.depth + 1
                  FROM lineage
                  JOIN universe_builds AS build
                    ON build.universe_version = lineage.universe_version
                 WHERE build.parent_version IS NOT NULL
            )
            SELECT to_jsonb(build) AS payload
              FROM lineage
              JOIN universe_builds AS build USING (universe_version)
             ORDER BY lineage.depth DESC, build.universe_version
            """,
            universe_version,
        )
        if not builds:
            raise RuntimeError(f"Unknown universe version: {universe_version}")
        if any(build.get("status") != "sealed" for build in builds):
            raise RuntimeError("Every release universe and ancestor must be sealed")
        if any(not SOURCE_SHA_RE.fullmatch(str(build.get("source_sha") or "")) for build in builds):
            raise RuntimeError("Every release universe and ancestor must have a committed source SHA")

        candidate = next(
            (build for build in builds if build["universe_version"] == universe_version),
            None,
        )
        if candidate is None:
            raise RuntimeError("Release lineage did not include its requested universe")
        if not MANIFEST_SHA_RE.fullmatch(str(candidate.get("data_manifest_sha256") or "")):
            raise RuntimeError(
                "The sealed release universe must be bound to a data manifest before export"
            )

        versions = [str(build["universe_version"]) for build in builds]
        tables = {
            "metric_vectors": await _json_rows(
                connection,
                """
                SELECT to_jsonb(vector_row) AS payload
                  FROM metric_vectors AS vector_row
                 WHERE universe_version = ANY($1::varchar[])
                 ORDER BY universe_version, ticker
                """,
                versions,
            ),
            "gate_evaluations": await _json_rows(
                connection,
                """
                SELECT to_jsonb(gate_row) - 'id' AS payload
                  FROM gate_evaluations AS gate_row
                 WHERE universe_version = ANY($1::varchar[])
                 ORDER BY universe_version, ticker, gate_id, evaluated_at, id
                """,
                versions,
            ),
            "ranked_rows": await _json_rows(
                connection,
                """
                SELECT to_jsonb(rank_row) AS payload
                  FROM ranked_rows AS rank_row
                 WHERE universe_version = ANY($1::varchar[])
                 ORDER BY universe_version, recipe_key, ticker
                """,
                versions,
            ),
            "universe_evidence_refs": await _json_rows(
                connection,
                """
                SELECT to_jsonb(ref_row) AS payload
                  FROM universe_evidence_refs AS ref_row
                 WHERE universe_version = ANY($1::varchar[])
                 ORDER BY universe_version, claim_id
                """,
                versions,
            ),
            "deepseek_audit_runs": await _json_rows(
                connection,
                """
                SELECT to_jsonb(run_row) AS payload
                  FROM deepseek_audit_runs AS run_row
                 WHERE universe_version = ANY($1::varchar[])
                 ORDER BY universe_version, run_id
                """,
                versions,
            ),
            "final_reviews": await _json_rows(
                connection,
                """
                SELECT to_jsonb(review_row) AS payload
                  FROM final_reviews AS review_row
                 WHERE universe_version = ANY($1::varchar[])
                 ORDER BY universe_version, review_id
                """,
                versions,
            ),
            "audit_trail_entries": await _json_rows(
                connection,
                """
                SELECT to_jsonb(audit_row) - 'id' AS payload
                  FROM audit_trail_entries AS audit_row
                 WHERE universe_version = ANY($1::varchar[])
                 ORDER BY universe_version, ticker, axis, generated_at, id
                """,
                versions,
            ),
        }
        tables["evidence_claims"] = await _json_rows(
            connection,
            """
            SELECT DISTINCT ON (claim.claim_id) to_jsonb(claim) AS payload
              FROM evidence_claims AS claim
              JOIN universe_evidence_refs AS ref
                ON ref.claim_id = claim.claim_id
             WHERE ref.universe_version = ANY($1::varchar[])
             ORDER BY claim.claim_id
            """,
            versions,
        )
        tables["source_snapshots"] = await _json_rows(
            connection,
            """
            SELECT DISTINCT ON (snapshot.snapshot_id) to_jsonb(snapshot) AS payload
              FROM source_snapshots AS snapshot
              JOIN evidence_claims AS claim
                ON claim.snapshot_id = snapshot.snapshot_id
              JOIN universe_evidence_refs AS ref
                ON ref.claim_id = claim.claim_id
             WHERE ref.universe_version = ANY($1::varchar[])
             ORDER BY snapshot.snapshot_id
            """,
            versions,
        )
        tables["rank_recipes"] = await _json_rows(
            connection,
            """
            SELECT to_jsonb(recipe) AS payload
              FROM rank_recipes AS recipe
              JOIN (
                  SELECT DISTINCT recipe_key
                    FROM ranked_rows
                   WHERE universe_version = ANY($1::varchar[])
              ) AS used_recipe
                ON used_recipe.recipe_key = recipe.recipe_key
             ORDER BY recipe.recipe_key
            """,
            versions,
        )
    finally:
        await connection.close()

    snapshot_document = build_document(database_url, universe_version)
    document: dict[str, Any] = {
        "schema_version": RELEASE_SCHEMA_VERSION,
        "universe_version": universe_version,
        "source_sha": candidate["source_sha"],
        "data_manifest_sha256": candidate["data_manifest_sha256"],
        "database_snapshot_sha256": snapshot_document["snapshot_sha256"],
        "builds": builds,
        "tables": tables,
    }
    document["payload_sha256"] = _canonical_hash(document)
    return document


def _require_document(
    document: Any,
    *,
    expected_source_sha: str | None = None,
    expected_manifest_sha: str | None = None,
) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise RuntimeError("Research release must be a JSON object")
    recorded_hash = document.get("payload_sha256")
    material = {key: value for key, value in document.items() if key != "payload_sha256"}
    if not isinstance(recorded_hash, str) or recorded_hash != _canonical_hash(material):
        raise RuntimeError("Research release payload checksum does not match its contents")
    if document.get("schema_version") != RELEASE_SCHEMA_VERSION:
        raise RuntimeError(
            f"Unsupported research release schema: {document.get('schema_version')!r}"
        )
    universe_version = document.get("universe_version")
    source_sha = document.get("source_sha")
    manifest_sha = document.get("data_manifest_sha256")
    snapshot_sha = document.get("database_snapshot_sha256")
    if not isinstance(universe_version, str) or not universe_version:
        raise RuntimeError("Research release has no universe version")
    if not isinstance(source_sha, str) or not SOURCE_SHA_RE.fullmatch(source_sha):
        raise RuntimeError("Research release has no valid source SHA")
    if not isinstance(manifest_sha, str) or not MANIFEST_SHA_RE.fullmatch(manifest_sha):
        raise RuntimeError("Research release has no valid data manifest SHA")
    if not isinstance(snapshot_sha, str) or not MANIFEST_SHA_RE.fullmatch(snapshot_sha):
        raise RuntimeError("Research release has no valid database snapshot SHA")
    if expected_source_sha is not None and source_sha != expected_source_sha:
        raise RuntimeError(
            f"Research release source SHA {source_sha} does not match {expected_source_sha}"
        )
    if expected_manifest_sha is not None and manifest_sha != expected_manifest_sha:
        raise RuntimeError(
            "Research release data manifest SHA does not match the restored data artifact"
        )
    if not isinstance(document.get("builds"), list) or not document["builds"]:
        raise RuntimeError("Research release has no universe build lineage")
    if not isinstance(document.get("tables"), dict):
        raise RuntimeError("Research release has no table payload")
    return document


def _build_signature(build: dict[str, Any]) -> dict[str, Any]:
    return {
        key: build.get(key)
        for key in (
            "universe_version",
            "input_sha256",
            "manifest",
            "parent_version",
            "engine_version",
            "source_sha",
            "data_manifest_sha256",
        )
    }


def _recipe_signature(recipe: dict[str, Any]) -> dict[str, Any]:
    return {
        key: recipe.get(key)
        for key in (
            "recipe_key",
            "recipe_id",
            "name",
            "formula_human",
            "formula_exact",
            "hard_filters",
            "axes",
            "benchmark_vs",
            "code_hash",
            "custom",
        )
    }


async def _insert_sources_and_claims(
    connection: asyncpg.Connection, tables: dict[str, Any]
) -> None:
    snapshots = tables.get("source_snapshots", [])
    claims = tables.get("evidence_claims", [])
    if snapshots:
        await connection.executemany(
            """
            INSERT INTO source_snapshots
                (snapshot_id, kind, ticker, as_of_date, available_date, fetched_at,
                 locator, content_sha256, notes)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            ON CONFLICT (snapshot_id) DO NOTHING
            """,
            [
                (
                    row["snapshot_id"],
                    row["kind"],
                    row["ticker"],
                    _date(row["as_of_date"]),
                    _date(row["available_date"]),
                    _timestamp(row["fetched_at"]),
                    row["locator"],
                    row["content_sha256"],
                    row.get("notes"),
                )
                for row in snapshots
            ],
        )
    if claims:
        await connection.executemany(
            """
            INSERT INTO evidence_claims
                (claim_id, snapshot_id, ticker, field, value_text, value_numeric,
                 operator, unit, excerpt_locator, extractor, extracted_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            ON CONFLICT (claim_id) DO NOTHING
            """,
            [
                (
                    row["claim_id"],
                    row["snapshot_id"],
                    row["ticker"],
                    row["field"],
                    row["value_text"],
                    row.get("value_numeric"),
                    row.get("operator"),
                    row.get("unit"),
                    row["excerpt_locator"],
                    row["extractor"],
                    _timestamp(row["extracted_at"]),
                )
                for row in claims
            ],
        )


async def _insert_rank_recipes(
    connection: asyncpg.Connection, recipes: list[dict[str, Any]]
) -> None:
    for recipe in recipes:
        existing = await connection.fetchval(
            "SELECT to_jsonb(recipe) FROM rank_recipes AS recipe WHERE recipe_key=$1",
            recipe["recipe_key"],
        )
        if existing is not None:
            if _recipe_signature(_decode_json(existing)) != _recipe_signature(recipe):
                raise RuntimeError(
                    f"Target rank recipe {recipe['recipe_key']} does not match the release"
                )
            continue
        await connection.execute(
            """
            INSERT INTO rank_recipes
                (recipe_key, recipe_id, name, formula_human, formula_exact, hard_filters,
                 axes, benchmark_vs, code_hash, custom, created_at)
            VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7::jsonb,$8,$9,$10,$11)
            """,
            recipe["recipe_key"],
            recipe["recipe_id"],
            recipe["name"],
            recipe["formula_human"],
            recipe["formula_exact"],
            _jsonb(recipe.get("hard_filters", [])),
            _jsonb(recipe.get("axes", [])),
            recipe["benchmark_vs"],
            recipe.get("code_hash"),
            bool(recipe.get("custom", False)),
            _timestamp(recipe["created_at"]),
        )


async def _insert_build_content(
    connection: asyncpg.Connection,
    tables: dict[str, Any],
    new_versions: set[str],
) -> None:
    vectors = [
        row for row in tables.get("metric_vectors", []) if row["universe_version"] in new_versions
    ]
    if vectors:
        await connection.executemany(
            """
            INSERT INTO metric_vectors
                (ticker, universe_version, computed_at, vector, completeness_grade,
                 route, kill_active, stale)
            VALUES ($1,$2,$3,$4::jsonb,$5,$6,$7,$8)
            """,
            [
                (
                    row["ticker"],
                    row["universe_version"],
                    _timestamp(row["computed_at"]),
                    _jsonb(row["vector"]),
                    row["completeness_grade"],
                    row.get("route"),
                    row.get("kill_active"),
                    bool(row.get("stale", False)),
                )
                for row in vectors
            ],
        )

    gates = [
        row for row in tables.get("gate_evaluations", []) if row["universe_version"] in new_versions
    ]
    if gates:
        await connection.executemany(
            """
            INSERT INTO gate_evaluations
                (ticker, gate_id, passed, threshold, observed, source_field, claim_ids,
                 evaluated_at, universe_version)
            VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8,$9)
            """,
            [
                (
                    row["ticker"],
                    row["gate_id"],
                    bool(row["passed"]),
                    row["threshold"],
                    row.get("observed"),
                    row["source_field"],
                    _jsonb(row.get("claim_ids", [])),
                    _timestamp(row["evaluated_at"]),
                    row["universe_version"],
                )
                for row in gates
            ],
        )

    ranks = [
        row for row in tables.get("ranked_rows", []) if row["universe_version"] in new_versions
    ]
    if ranks:
        await connection.executemany(
            """
            INSERT INTO ranked_rows
                (ticker, recipe_key, universe_version, rank, score, contributions,
                 completeness_grade, freshness_ok, kill_active, final_review_id, computed_at)
            VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9,$10,$11)
            """,
            [
                (
                    row["ticker"],
                    row["recipe_key"],
                    row["universe_version"],
                    row["rank"],
                    row["score"],
                    _jsonb(row.get("contributions", {})),
                    row["completeness_grade"],
                    bool(row["freshness_ok"]),
                    bool(row["kill_active"]),
                    row.get("final_review_id"),
                    _timestamp(row["computed_at"]),
                )
                for row in ranks
            ],
        )

    refs = [
        row
        for row in tables.get("universe_evidence_refs", [])
        if row["universe_version"] in new_versions
    ]
    if refs:
        await connection.executemany(
            """
            INSERT INTO universe_evidence_refs (universe_version, claim_id)
            VALUES ($1,$2)
            """,
            [(row["universe_version"], row["claim_id"]) for row in refs],
        )


async def _insert_historical_outputs(
    connection: asyncpg.Connection,
    tables: dict[str, Any],
    new_versions: set[str],
) -> None:
    runs = [
        row
        for row in tables.get("deepseek_audit_runs", [])
        if row["universe_version"] in new_versions
    ]
    if runs:
        await connection.executemany(
            """
            INSERT INTO deepseek_audit_runs
                (run_id, job, ticker, output_kind, output, model, started_at,
                 finished_at, status, severity, universe_version)
            VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7,$8,$9,$10,$11)
            ON CONFLICT (run_id) DO NOTHING
            """,
            [
                (
                    row["run_id"],
                    row["job"],
                    row.get("ticker"),
                    row["output_kind"],
                    _jsonb(row["output"]),
                    row["model"],
                    _timestamp(row["started_at"]),
                    _timestamp(row.get("finished_at")),
                    row["status"],
                    row.get("severity"),
                    row["universe_version"],
                )
                for row in runs
            ],
        )

    reviews = [
        row
        for row in tables.get("final_reviews", [])
        if row["universe_version"] in new_versions
    ]
    if reviews:
        await connection.executemany(
            """
            INSERT INTO final_reviews
                (review_id, ticker, recipe_id, trigger, checklist, passed, notes,
                 reviewed_at, reviewer, universe_version)
            VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7,$8,$9,$10)
            ON CONFLICT (review_id) DO NOTHING
            """,
            [
                (
                    row["review_id"],
                    row.get("ticker"),
                    row.get("recipe_id"),
                    row["trigger"],
                    _jsonb(row["checklist"]),
                    bool(row["passed"]),
                    row.get("notes"),
                    _timestamp(row["reviewed_at"]),
                    row["reviewer"],
                    row["universe_version"],
                )
                for row in reviews
            ],
        )

    audit_entries = [
        row
        for row in tables.get("audit_trail_entries", [])
        if row["universe_version"] in new_versions
    ]
    if audit_entries:
        await connection.executemany(
            """
            INSERT INTO audit_trail_entries
                (ticker, axis, metric, snapshot_ids, literature, deepseek_run_id,
                 final_review_id, generated_at, universe_version)
            VALUES ($1,$2,$3::jsonb,$4::jsonb,$5::jsonb,$6,$7,$8,$9)
            """,
            [
                (
                    row["ticker"],
                    row["axis"],
                    _jsonb(row["metric"]),
                    _jsonb(row.get("snapshot_ids", [])),
                    _jsonb(row.get("literature", [])),
                    row.get("deepseek_run_id"),
                    row.get("final_review_id"),
                    _timestamp(row["generated_at"]),
                    row["universe_version"],
                )
                for row in audit_entries
            ],
        )


async def _snapshot_document_for_connection(
    connection: asyncpg.Connection, universe_version: str
) -> dict[str, Any]:
    raw = await connection.fetchval(
        SNAPSHOT_SQL.replace(":'universe_version'", "$1"),
        universe_version,
    )
    snapshot = _decode_json(raw)
    document: dict[str, Any] = {
        "schema_version": 1,
        "universe_version": universe_version,
        "snapshot": snapshot,
    }
    document["snapshot_sha256"] = _canonical_hash(document)
    return document


async def _import_document(
    database_url: str,
    document: dict[str, Any],
    *,
    expected_source_sha: str | None,
    expected_manifest_sha: str | None,
) -> None:
    document = _require_document(
        document,
        expected_source_sha=expected_source_sha,
        expected_manifest_sha=expected_manifest_sha,
    )
    universe_version = str(document["universe_version"])
    tables = document["tables"]
    builds = document["builds"]
    if not all(isinstance(build, dict) for build in builds):
        raise RuntimeError("Research release contains an invalid build lineage")
    versions = [str(build.get("universe_version") or "") for build in builds]
    if len(set(versions)) != len(versions) or not all(versions):
        raise RuntimeError("Research release contains duplicate or empty universe versions")
    if universe_version != versions[-1]:
        raise RuntimeError("Research release build lineage must end at the requested universe")
    for index, build in enumerate(builds):
        if build.get("status") != "sealed":
            raise RuntimeError("Research release contains an unsealed build")
        if not SOURCE_SHA_RE.fullmatch(str(build.get("source_sha") or "")):
            raise RuntimeError("Research release contains a build without a committed source SHA")
        expected_parent = versions[index - 1] if index else None
        if build.get("parent_version") != expected_parent:
            raise RuntimeError("Research release build lineage is not parent-first and contiguous")
    if builds[-1].get("data_manifest_sha256") != document["data_manifest_sha256"]:
        raise RuntimeError("Research release candidate build is not bound to its declared data manifest")

    connection = await asyncpg.connect(database_url)
    try:
        async with connection.transaction():
            existing_rows = await connection.fetch(
                """
                SELECT universe_version, input_sha256, manifest, parent_version, engine_version,
                       source_sha, data_manifest_sha256, status
                  FROM universe_builds
                 WHERE universe_version = ANY($1::varchar[])
                """,
                versions,
            )
            existing = {
                str(row["universe_version"]): {
                    "universe_version": row["universe_version"],
                    "input_sha256": row["input_sha256"],
                    "manifest": _decode_json_value(row["manifest"]),
                    "parent_version": row["parent_version"],
                    "engine_version": row["engine_version"],
                    "source_sha": row["source_sha"],
                    "data_manifest_sha256": row["data_manifest_sha256"],
                    "status": row["status"],
                }
                for row in existing_rows
            }
            new_versions: set[str] = set()
            for build in builds:
                version = build["universe_version"]
                if version in existing:
                    if (
                        existing[version].get("status") != "sealed"
                        or _build_signature(existing[version]) != _build_signature(build)
                    ):
                        raise RuntimeError(
                            f"Target universe {version} does not match the immutable release lineage"
                        )
                    continue
                new_versions.add(version)
                await connection.execute(
                    """
                    INSERT INTO universe_builds
                        (universe_version, input_sha256, manifest, parent_version, engine_version,
                         created_at, sealed_at, status, is_active, data_manifest_sha256, source_sha)
                    VALUES ($1,$2,$3::jsonb,$4,$5,$6,NULL,'building',false,$7,$8)
                    """,
                    build["universe_version"],
                    build["input_sha256"],
                    _jsonb(build["manifest"]),
                    build.get("parent_version"),
                    build["engine_version"],
                    _timestamp(build["created_at"]),
                    build.get("data_manifest_sha256"),
                    build["source_sha"],
                )

            await _insert_sources_and_claims(connection, tables)
            await _insert_rank_recipes(connection, list(tables.get("rank_recipes", [])))
            await _insert_build_content(connection, tables, new_versions)

            for build in builds:
                if build["universe_version"] not in new_versions:
                    continue
                await connection.execute(
                    """
                    UPDATE universe_builds
                       SET status='sealed', sealed_at=$2
                     WHERE universe_version=$1 AND status='building'
                    """,
                    build["universe_version"],
                    _timestamp(build["sealed_at"]),
                )

            await _insert_historical_outputs(connection, tables, new_versions)
            actual_snapshot = await _snapshot_document_for_connection(
                connection, universe_version
            )
            if actual_snapshot["snapshot_sha256"] != document["database_snapshot_sha256"]:
                raise RuntimeError(
                    "Imported research records do not match the staged database snapshot"
                )

            await connection.execute(
                "UPDATE universe_builds SET is_active=false WHERE is_active"
            )
            await connection.execute(
                """
                UPDATE universe_builds
                   SET is_active=true
                 WHERE universe_version=$1
                   AND status='sealed'
                   AND data_manifest_sha256=$2
                """,
                universe_version,
                document["data_manifest_sha256"],
            )
            active = await connection.fetchval(
                "SELECT is_active FROM universe_builds WHERE universe_version=$1",
                universe_version,
            )
            if active is not True:
                raise RuntimeError("Could not activate the imported immutable universe")
    finally:
        await connection.close()


def _database_url(value: str | None) -> str:
    database_url = value or os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("--database-url or DATABASE_URL is required")
    return database_url.replace("postgresql+asyncpg://", "postgresql://")


def _load_document(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read research release {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise SystemExit("Research release must contain a JSON object")
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export or import an immutable versioned research release"
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    export = subcommands.add_parser("export")
    export.add_argument("--database-url")
    export.add_argument("--universe-version", required=True)
    export.add_argument("--output", type=Path, required=True)

    imported = subcommands.add_parser("import")
    imported.add_argument("--database-url")
    imported.add_argument("--input", type=Path, required=True)
    imported.add_argument("--expected-source-sha")
    imported.add_argument("--expected-data-manifest-sha256")

    args = parser.parse_args()
    database_url = _database_url(args.database_url)
    if args.command == "export":
        document = asyncio.run(_export_document(database_url, args.universe_version))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
        print(
            json.dumps(
                {
                    "universe_version": document["universe_version"],
                    "source_sha": document["source_sha"],
                    "data_manifest_sha256": document["data_manifest_sha256"],
                    "database_snapshot_sha256": document["database_snapshot_sha256"],
                    "payload_sha256": document["payload_sha256"],
                },
                sort_keys=True,
            )
        )
        return

    if args.expected_source_sha and not SOURCE_SHA_RE.fullmatch(args.expected_source_sha):
        raise SystemExit("--expected-source-sha must be a full 40-character SHA")
    if args.expected_data_manifest_sha256 and not MANIFEST_SHA_RE.fullmatch(
        args.expected_data_manifest_sha256
    ):
        raise SystemExit(
            "--expected-data-manifest-sha256 must be a 64-character SHA-256 digest"
        )
    document = _load_document(args.input)
    asyncio.run(
        _import_document(
            database_url,
            document,
            expected_source_sha=args.expected_source_sha,
            expected_manifest_sha=args.expected_data_manifest_sha256,
        )
    )
    print(f"Imported and activated research universe {document.get('universe_version')}")


if __name__ == "__main__":
    main()
