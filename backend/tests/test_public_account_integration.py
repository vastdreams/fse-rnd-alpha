"""Ephemeral-PostgreSQL release checks for public account durability and isolation."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text

from app.contracts.research import MetricValue, MetricVector, ResearchCompleteness
from app.db.session import async_session_maker, engine
from app.main import app
from app.api.routes import auth as auth_routes
from app.services import account_service

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_POSTGRES_INTEGRATION") != "1",
    reason="requires the ephemeral PostgreSQL service used by CI",
)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _empty_release_manifest(universe_version: str) -> dict[str, object]:
    """A valid schema-v2 manifest for readiness tests with no data files."""

    content: dict[str, object] = {
        "schema_version": 2,
        "universe_version": universe_version,
        "required_sources": {},
        "artifacts": {},
        "files": {},
    }
    return {
        **content,
        "manifest_sha256": hashlib.sha256(
            json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


@pytest_asyncio.fixture(autouse=True)
async def _dispose_database_pool_between_tests():
    """The app-level async pool must not leak connections across pytest loops."""

    yield
    await engine.dispose()


async def _register_and_verify(client: httpx.AsyncClient) -> tuple[str, dict, str]:
    email = f"investor-{uuid.uuid4().hex}@example.com"
    password = "correct-horse-battery-staple"
    registered = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Integration Investor"},
    )
    assert registered.status_code == 201, registered.text
    payload = registered.json()
    assert payload["verification_required"] is True
    assert "password_hash" not in payload["user"]
    assert "verification_token_hash" not in payload["user"]

    verified = await client.post(
        "/api/auth/verify-email",
        json={"token": payload["debug_verification_token"]},
    )
    assert verified.status_code == 200, verified.text
    return verified.json()["access_token"], verified.json()["user"], password


@pytest.mark.asyncio
async def test_public_account_survives_new_request_and_password_reset():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        token, user, password = await _register_and_verify(client)
        current = await client.get("/api/auth/me", headers=_headers(token))
        assert current.status_code == 200
        assert current.json()["id"] == user["id"]
        assert current.json()["email_verified"] is True

        reset_request = await client.post("/api/auth/password-reset/request", json={"email": user["email"]})
        assert reset_request.status_code == 200, reset_request.text
        reset_token = reset_request.json()["debug_reset_token"]
        reset = await client.post(
            "/api/auth/password-reset/confirm",
            json={"email": user["email"], "token": reset_token, "password": "new-secure-password"},
        )
        assert reset.status_code == 200, reset.text
        invalidated_session = await client.get("/api/auth/me", headers=_headers(token))
        assert invalidated_session.status_code == 401

        old_login = await client.post(
            "/api/auth/login", json={"email": user["email"], "password": password}
        )
        assert old_login.status_code == 401
        new_login = await client.post(
            "/api/auth/login", json={"email": user["email"], "password": "new-secure-password"}
        )
        assert new_login.status_code == 200, new_login.text


@pytest.mark.asyncio
async def test_duplicate_registration_returns_a_stable_conflict():
    email = f"duplicate-{uuid.uuid4().hex}@example.com"
    payload = {
        "email": email,
        "password": "correct-horse-battery-staple",
        "full_name": "Duplicate Check",
    }
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post("/api/auth/register", json=payload)
        assert first.status_code == 201, first.text
        second = await client.post("/api/auth/register", json=payload)
        assert second.status_code == 409, second.text
        assert second.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_registration_keeps_the_verify_recovery_path_when_email_delivery_fails(monkeypatch):
    async def delivery_failure(_user: dict, _token: str) -> bool:
        return False

    monkeypatch.setattr(auth_routes, "_send_verification_email", delivery_failure)
    email = f"delivery-failure-{uuid.uuid4().hex}@example.com"
    password = "correct-horse-battery-staple"
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        registered = await client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": "Recovery Investor"},
        )
        assert registered.status_code == 201, registered.text
        payload = registered.json()
        assert payload["verification_required"] is True
        assert "delivery is delayed" in payload["message"]

        login = await client.post("/api/auth/login", json={"email": email, "password": password})
        assert login.status_code == 403
        verified = await client.post(
            "/api/auth/verify-email", json={"token": payload["debug_verification_token"]}
        )
        assert verified.status_code == 200, verified.text


@pytest.mark.asyncio
async def test_two_distinct_seed_accounts_are_created_idempotently(monkeypatch):
    primary_email = f"primary-seed-{uuid.uuid4().hex}@example.com"
    secondary_email = f"secondary-seed-{uuid.uuid4().hex}@example.com"
    monkeypatch.setenv("AUTH_SEED_EMAIL", primary_email)
    monkeypatch.setenv("AUTH_SEED_PASSWORD", "primary-bootstrap-password")
    monkeypatch.setenv("AUTH_SECONDARY_SEED_EMAIL", secondary_email)
    monkeypatch.setenv("AUTH_SECONDARY_SEED_PASSWORD", "secondary-bootstrap-password")

    async with async_session_maker() as db:
        await account_service.ensure_seed_account(db)
        await account_service.ensure_seed_account(db)
        await db.commit()
        rows = (
            await db.execute(
                text(
                    """SELECT email, email_verified_at IS NOT NULL AS verified
                         FROM user_accounts
                        WHERE email IN (:primary_email, :secondary_email)
                        ORDER BY email"""
                ),
                {"primary_email": primary_email, "secondary_email": secondary_email},
            )
        ).mappings().all()

    assert [row["email"] for row in rows] == sorted([primary_email, secondary_email])
    assert all(row["verified"] for row in rows)


@pytest.mark.asyncio
async def test_seed_accounts_must_have_distinct_emails(monkeypatch):
    email = f"same-seed-{uuid.uuid4().hex}@example.com"
    monkeypatch.setenv("AUTH_SEED_EMAIL", email)
    monkeypatch.setenv("AUTH_SEED_PASSWORD", "primary-bootstrap-password")
    monkeypatch.setenv("AUTH_SECONDARY_SEED_EMAIL", email)
    monkeypatch.setenv("AUTH_SECONDARY_SEED_PASSWORD", "secondary-bootstrap-password")

    async with async_session_maker() as db:
        with pytest.raises(ValueError, match="must differ"):
            await account_service.ensure_seed_account(db)


@pytest.mark.asyncio
async def test_legacy_email_collision_is_not_mapped_to_a_new_account(monkeypatch):
    legacy_id = f"legacy-{uuid.uuid4().hex}"
    email = f"collision-{uuid.uuid4().hex}@example.com"
    legacy_hash = account_service.auth_users.hash_password("legacy-password")
    existing_id = f"existing-{uuid.uuid4().hex}"

    monkeypatch.setattr(
        account_service.auth_users,
        "list_users",
        lambda: [
            {
                "id": legacy_id,
                "email": email,
                "password_hash": legacy_hash,
                "full_name": "Legacy User",
                "is_active": True,
            }
        ],
    )
    async with async_session_maker() as db:
        await db.execute(
            text(
                """INSERT INTO user_accounts
                   (user_id, email, password_hash, full_name, role, is_active, email_verified_at)
                   VALUES (:user_id, :email, :password_hash, 'Unrelated User', 'user', true, CURRENT_TIMESTAMP)"""
            ),
            {
                "user_id": existing_id,
                "email": email,
                "password_hash": account_service.auth_users.hash_password("different-password"),
            },
        )
        await db.execute(
            text(
                """DELETE FROM legacy_data_migrations
                   WHERE migration_key='auth_users_json_to_user_accounts_v2'"""
            )
        )
        await db.commit()

        migrated = await account_service.migrate_legacy_json_accounts(db)
        await db.commit()
        assert migrated == 0
        mapped = await db.scalar(
            text(
                """SELECT 1 FROM legacy_account_identities
                   WHERE legacy_user_id IN (:legacy_id, :email)"""
            ),
            {"legacy_id": legacy_id, "email": email},
        )
        assert mapped is None
        await db.execute(
            text(
                """DELETE FROM legacy_data_migrations
                   WHERE migration_key='auth_users_json_to_user_accounts_v2'"""
            )
        )
        await db.commit()


async def _seed_vector_with_claim(universe_version: str, ticker: str, claim_id: str) -> None:
    as_of = date(2026, 7, 12)
    build_time = datetime.now(timezone.utc).replace(tzinfo=None)
    vector = MetricVector(
        ticker=ticker,
        universe_version=universe_version,
        computed_at=build_time,
        retention=MetricValue(
            value=1.1,
            as_of_date=as_of,
            available_date=as_of,
            claim_ids=[claim_id],
        ),
        kill_active=False,
        completeness=ResearchCompleteness(
            grade="A",
            filing_fetched=True,
            claims_n=1,
            dcf_reproducible=True,
            overlay_fill_rate=1,
            competitor_map_filled=True,
            stale=False,
        ),
    )
    snapshot_id = f"snapshot-{uuid.uuid4().hex}"
    async with async_session_maker() as db:
        await db.execute(
            text(
                """INSERT INTO universe_builds
                   (universe_version, input_sha256, manifest, engine_version, status, sealed_at, is_active, source_sha)
                   VALUES (:universe_version, :sha, '{}'::jsonb, 'integration-test', 'building', NULL, false, :source_sha)"""
            ),
            {
                "universe_version": universe_version,
                "sha": uuid.uuid4().hex + uuid.uuid4().hex,
                "source_sha": "1" * 40,
            },
        )
        await db.execute(
            text(
                """INSERT INTO source_snapshots
                   (snapshot_id, kind, ticker, as_of_date, available_date, locator, content_sha256)
                   VALUES (:snapshot_id, '10-K', :ticker, :as_of, :available, :locator, :sha)"""
            ),
            {
                "snapshot_id": snapshot_id,
                "ticker": ticker,
                "as_of": as_of,
                "available": as_of,
                "locator": "https://example.test/filing",
                "sha": "a" * 64,
            },
        )
        await db.execute(
            text(
                """INSERT INTO evidence_claims
                   (claim_id, snapshot_id, ticker, field, value_text, excerpt_locator, extractor, extracted_at)
                   VALUES (:claim_id, :snapshot_id, :ticker, 'retention', '110%', 'item-7',
                           'integration-test', :extracted_at)"""
            ),
            {
                "claim_id": claim_id,
                "snapshot_id": snapshot_id,
                "ticker": ticker,
                "extracted_at": build_time,
            },
        )
        await db.execute(
            text(
                """INSERT INTO metric_vectors
                   (ticker, universe_version, computed_at, vector, completeness_grade, kill_active, stale)
                   VALUES (:ticker, :universe_version, :computed_at, CAST(:vector AS jsonb), 'A', false, false)"""
            ),
            {
                "ticker": ticker,
                "universe_version": universe_version,
                "computed_at": build_time,
                "vector": json.dumps(vector.model_dump(mode="json")),
            },
        )
        await db.execute(
            text("SELECT materialize_universe_evidence_refs(:universe_version)"),
            {"universe_version": universe_version},
        )
        await db.execute(
            text(
                """UPDATE universe_builds
                   SET status='sealed', sealed_at=CURRENT_TIMESTAMP
                   WHERE universe_version=:universe_version"""
            ),
            {"universe_version": universe_version},
        )
        await db.commit()


def _research_snapshot(universe_version: str) -> dict:
    script = Path(__file__).parents[2] / "scripts" / "research_snapshot.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--database-url",
            os.environ["DATABASE_URL"],
            "--universe-version",
            universe_version,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


@pytest.mark.asyncio
async def test_sealed_snapshot_ignores_later_unreferenced_claims():
    universe_version = f"univ_snapshot_{uuid.uuid4().hex[:24]}"
    ticker = "SNAP"
    await _seed_vector_with_claim(universe_version, ticker, f"claim-{uuid.uuid4().hex}")

    before = _research_snapshot(universe_version)
    async with async_session_maker() as db:
        snapshot_id = f"unrelated-snapshot-{uuid.uuid4().hex}"
        await db.execute(
            text(
                """INSERT INTO source_snapshots
                   (snapshot_id, kind, ticker, as_of_date, available_date, locator, content_sha256)
                   VALUES (:snapshot_id, '10-K', :ticker, :as_of, :available, :locator, :sha)"""
            ),
            {
                "snapshot_id": snapshot_id,
                "ticker": ticker,
                "as_of": date(2026, 7, 13),
                "available": date(2026, 7, 13),
                "locator": "https://example.test/later-filing",
                "sha": "b" * 64,
            },
        )
        await db.execute(
            text(
                """INSERT INTO evidence_claims
                   (claim_id, snapshot_id, ticker, field, value_text, excerpt_locator, extractor)
                   VALUES (:claim_id, :snapshot_id, :ticker, 'later_metric', 'new', 'item-7', 'test')"""
            ),
            {"claim_id": f"later-claim-{uuid.uuid4().hex}", "snapshot_id": snapshot_id, "ticker": ticker},
        )
        await db.commit()

    after = _research_snapshot(universe_version)
    assert after["snapshot_sha256"] == before["snapshot_sha256"]
    assert after["snapshot"]["tables"] == before["snapshot"]["tables"]


@pytest.mark.asyncio
async def test_books_and_memos_are_isolated_between_users():
    universe_version = f"univ_test_{uuid.uuid4().hex[:24]}"
    ticker = "ACME"
    claim_id = f"claim-{uuid.uuid4().hex}"
    await _seed_vector_with_claim(universe_version, ticker, claim_id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        owner_token, owner, _ = await _register_and_verify(client)
        other_token, _, _ = await _register_and_verify(client)

        created = await client.post(
            "/api/books",
            headers=_headers(owner_token),
            json={"name": "Owner book", "universe_version": universe_version},
        )
        assert created.status_code == 200, created.text
        book_id = created.json()["book_id"]

        other_books = await client.get("/api/books", headers=_headers(other_token))
        assert other_books.status_code == 200
        assert other_books.json()["books"] == []

        other_save = await client.put(
            f"/api/books/{book_id}",
            headers=_headers(other_token),
            json={"holdings": []},
        )
        assert other_save.status_code == 404

        holding = {
            "ticker": ticker,
            "weight_pct": 10,
            "added_at": datetime.now(timezone.utc).isoformat(),
        }
        saved = await client.put(
            f"/api/books/{book_id}",
            headers=_headers(owner_token),
            json={"holdings": [holding]},
        )
        assert saved.status_code == 200, saved.text
        locked = await client.post(
            f"/api/books/{book_id}/lock",
            headers=_headers(owner_token),
            json={"acknowledgements": [ticker]},
        )
        assert locked.status_code == 200, locked.text
        locked_again = await client.post(
            f"/api/books/{book_id}/lock",
            headers=_headers(owner_token),
            json={"acknowledgements": []},
        )
        assert locked_again.status_code == 200
        assert locked_again.json()["acknowledgements"] == [ticker]
        locked_edit = await client.put(
            f"/api/books/{book_id}",
            headers=_headers(owner_token),
            json={"holdings": []},
        )
        assert locked_edit.status_code == 409
        export = await client.get(f"/api/books/{book_id}/audit-pack", headers=_headers(owner_token))
        assert export.status_code == 200, export.text
        assert export.json()["book"]["book_id"] == book_id
        other_export = await client.get(f"/api/books/{book_id}/audit-pack", headers=_headers(other_token))
        assert other_export.status_code == 404
        async with async_session_maker() as db:
            stored_payload = await db.scalar(
                text(
                    """SELECT payload FROM audit_exports
                       WHERE book_id=:book_id AND user_id=:user_id
                       ORDER BY generated_at DESC LIMIT 1"""
                ),
                {"book_id": book_id, "user_id": owner["id"]},
            )
        payload = stored_payload if isinstance(stored_payload, dict) else json.loads(stored_payload)
        assert payload["book"]["book_id"] == book_id

        memo = await client.post(
            f"/api/universe/memo/{ticker}",
            headers=_headers(owner_token),
            json={
                "thesis": "The filing-backed retention claim supports further research.",
                "citations": [claim_id],
                "universe_version": universe_version,
            },
        )
        assert memo.status_code == 200, memo.text
        owner_memos = await client.get(
            f"/api/universe/memo/{ticker}?universe_version={universe_version}",
            headers=_headers(owner_token),
        )
        assert owner_memos.status_code == 200, owner_memos.text
        assert owner_memos.json()["memos"][0]["citation_records"][0]["claim_id"] == claim_id

        other_memos = await client.get(
            f"/api/universe/memo/{ticker}?universe_version={universe_version}",
            headers=_headers(other_token),
        )
        assert other_memos.status_code == 200
        assert other_memos.json()["memos"] == []


@pytest.mark.asyncio
async def test_logout_revokes_the_current_jwt():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        token, _, _ = await _register_and_verify(client)
        logged_out = await client.post("/api/auth/logout", headers=_headers(token))
        assert logged_out.status_code == 200, logged_out.text

        rejected = await client.get("/api/auth/me", headers=_headers(token))
        assert rejected.status_code == 401


@pytest.mark.asyncio
async def test_public_user_cannot_run_operator_only_research_mutations():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        token, _, _ = await _register_and_verify(client)
        headers = _headers(token)

        compute = await client.post("/api/research/classify-cohort", headers=headers)
        assert compute.status_code == 403, compute.text

        ai = await client.post("/api/ai/company/ACME", headers=headers)
        assert ai.status_code == 403, ai.text

        backtests = await client.get("/api/backtests/", headers=headers)
        assert backtests.status_code == 403, backtests.text


@pytest.mark.asyncio
async def test_legacy_portfolio_api_requires_a_durable_authenticated_account():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        anonymous = await client.get("/api/portfolio/methodology")
        assert anonymous.status_code == 401, anonymous.text

        token, _, _ = await _register_and_verify(client)
        authenticated = await client.get(
            "/api/portfolio/methodology",
            headers=_headers(token),
        )
        assert authenticated.status_code == 200, authenticated.text


@pytest.mark.asyncio
async def test_admin_api_uses_a_durable_admin_account_and_revocable_session():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        _, user, password = await _register_and_verify(client)
        async with async_session_maker() as db:
            await db.execute(
                text("UPDATE user_accounts SET role='admin' WHERE user_id=:user_id"),
                {"user_id": user["id"]},
            )
            await db.commit()

        login = await client.post(
            "/api/admin/login",
            json={"email": user["email"], "password": password},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]

        verified = await client.get("/api/admin/verify", headers=_headers(token))
        assert verified.status_code == 200, verified.text
        assert verified.json()["username"] == user["email"]

        logged_out = await client.post("/api/auth/logout", headers=_headers(token))
        assert logged_out.status_code == 200, logged_out.text
        revoked = await client.get("/api/admin/verify", headers=_headers(token))
        assert revoked.status_code == 401, revoked.text


@pytest.mark.asyncio
async def test_sealed_universe_vectors_cannot_be_mutated():
    universe_version = f"univ_sealed_{uuid.uuid4().hex[:24]}"
    ticker = "SEAL"
    claim_id = f"claim-{uuid.uuid4().hex}"
    await _seed_vector_with_claim(universe_version, ticker, claim_id)

    async with async_session_maker() as db:
        with pytest.raises(Exception):
            await db.execute(
                text(
                    """UPDATE metric_vectors SET stale=true
                       WHERE ticker=:ticker AND universe_version=:universe_version"""
                ),
                {"ticker": ticker, "universe_version": universe_version},
            )
            await db.commit()
        await db.rollback()

@pytest.mark.asyncio
async def test_readiness_attests_active_sealed_build_and_mounted_manifest(tmp_path, monkeypatch):
    universe_version = f"univ_ready_{uuid.uuid4().hex[:24]}"
    ticker = "RDY"
    claim_id = f"claim-{uuid.uuid4().hex}"
    manifest = _empty_release_manifest(universe_version)
    manifest_sha = str(manifest["manifest_sha256"])
    await _seed_vector_with_claim(universe_version, ticker, claim_id)

    (tmp_path / "release_manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("RELEASE_SOURCE_SHA", "1" * 40)
    monkeypatch.setenv("RELEASE_REF", f"{'1' * 40}-integration")
    monkeypatch.setenv("RELEASE_BACKEND_IMAGE", "backend@sha256:" + "a" * 64)
    monkeypatch.setenv("RELEASE_FRONTEND_IMAGE", "frontend@sha256:" + "b" * 64)
    async with async_session_maker() as db:
        await db.execute(text("UPDATE universe_builds SET is_active=false WHERE is_active"))
        await db.execute(
            text(
                """UPDATE universe_builds
                   SET data_manifest_sha256=:manifest_sha, is_active=true
                   WHERE universe_version=:universe_version"""
            ),
            {"manifest_sha": manifest_sha, "universe_version": universe_version},
        )
        await db.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        ready = await client.get("/ready")
    assert ready.status_code == 200, ready.text
    payload = ready.json()
    assert payload["ready"] is True
    assert payload["release"]["universe_version"] == universe_version
    assert payload["release"]["data_manifest_sha256"] == manifest_sha
    assert payload["checks"]["runtime_release"] == "ok"
    assert payload["release"]["runtime"]["release_ref"] == f"{'1' * 40}-integration"


@pytest.mark.asyncio
async def test_readiness_rejects_tampered_mounted_release_data(tmp_path, monkeypatch):
    universe_version = f"univ_ready_tamper_{uuid.uuid4().hex[:20]}"
    data_file = tmp_path / "price-cache.json"
    original = b'{"price": 10}\n'
    data_file.write_bytes(original)
    file_inventory = {
        "price-cache.json": {
            "bytes": len(original),
            "sha256": hashlib.sha256(original).hexdigest(),
        }
    }
    content = {
        "schema_version": 2,
        "universe_version": universe_version,
        "required_sources": {},
        "artifacts": {},
        "files": file_inventory,
    }
    manifest = {
        **content,
        "manifest_sha256": hashlib.sha256(
            json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    (tmp_path / "release_manifest.json").write_text(json.dumps(manifest))
    data_file.write_text('{"price": 11}\n')
    await _seed_vector_with_claim(universe_version, "TAMP", f"claim-{uuid.uuid4().hex}")
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))

    async with async_session_maker() as db:
        await db.execute(text("UPDATE universe_builds SET is_active=false WHERE is_active"))
        await db.execute(
            text(
                """UPDATE universe_builds
                   SET data_manifest_sha256=:manifest_sha, is_active=true
                   WHERE universe_version=:universe_version"""
            ),
            {
                "manifest_sha": manifest["manifest_sha256"],
                "universe_version": universe_version,
            },
        )
        await db.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        ready = await client.get("/ready")
    assert ready.status_code == 503, ready.text
    assert ready.json()["checks"]["research_data_manifest"] == (
        "mounted data files do not match the release inventory"
    )


@pytest.mark.asyncio
async def test_readiness_rejects_missing_personal_history_integrity_trigger(tmp_path, monkeypatch):
    universe_version = f"univ_ready_trigger_{uuid.uuid4().hex[:20]}"
    ticker = "TRIG"
    manifest = _empty_release_manifest(universe_version)
    manifest_sha = str(manifest["manifest_sha256"])
    await _seed_vector_with_claim(universe_version, ticker, f"claim-{uuid.uuid4().hex}")
    (tmp_path / "release_manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))

    async with async_session_maker() as db:
        await db.execute(text("UPDATE universe_builds SET is_active=false WHERE is_active"))
        await db.execute(
            text(
                """UPDATE universe_builds
                   SET data_manifest_sha256=:manifest_sha, is_active=true
                   WHERE universe_version=:universe_version"""
            ),
            {"manifest_sha": manifest_sha, "universe_version": universe_version},
        )
        await db.execute(text("ALTER TABLE dcf_runs DISABLE TRIGGER trg_dcf_runs_append_only"))
        await db.commit()

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            ready = await client.get("/ready")
        assert ready.status_code == 503, ready.text
        assert "trg_dcf_runs_append_only" in ready.json()["checks"]["research_integrity_triggers"]
    finally:
        async with async_session_maker() as db:
            await db.execute(text("ALTER TABLE dcf_runs ENABLE TRIGGER trg_dcf_runs_append_only"))
            await db.commit()


@pytest.mark.asyncio
async def test_universe_must_start_building_and_seal_with_vectors():
    universe_version = f"univ_lifecycle_{uuid.uuid4().hex[:24]}"
    source_sha = "2" * 40
    rejected_input_sha = uuid.uuid4().hex + uuid.uuid4().hex
    building_input_sha = uuid.uuid4().hex + uuid.uuid4().hex

    async with async_session_maker() as db:
        with pytest.raises(Exception):
            await db.execute(
                text(
                    """INSERT INTO universe_builds
                       (universe_version, input_sha256, manifest, engine_version, status, sealed_at, is_active, source_sha)
                       VALUES (:universe_version, :input_sha, '{}'::jsonb, 'integration-test',
                               'sealed', CURRENT_TIMESTAMP, false, :source_sha)"""
                ),
                {
                    "universe_version": universe_version,
                    "input_sha": rejected_input_sha,
                    "source_sha": source_sha,
                },
            )
            await db.commit()
        await db.rollback()

        await db.execute(
            text(
                """INSERT INTO universe_builds
                   (universe_version, input_sha256, manifest, engine_version, status, sealed_at, is_active, source_sha)
                   VALUES (:universe_version, :input_sha, '{}'::jsonb, 'integration-test',
                           'building', NULL, false, :source_sha)"""
            ),
            {
                "universe_version": universe_version,
                "input_sha": building_input_sha,
                "source_sha": source_sha,
            },
        )
        await db.commit()

        with pytest.raises(Exception):
            await db.execute(
                text(
                    """UPDATE universe_builds
                       SET status='sealed', sealed_at=CURRENT_TIMESTAMP
                       WHERE universe_version=:universe_version"""
                ),
                {"universe_version": universe_version},
            )
            await db.commit()
        await db.rollback()


@pytest.mark.asyncio
async def test_historical_outputs_require_a_version_and_sealed_builds_reject_late_ranks():
    universe_version = f"univ_outputs_{uuid.uuid4().hex[:24]}"
    ticker = "OUTP"
    claim_id = f"claim-{uuid.uuid4().hex}"
    await _seed_vector_with_claim(universe_version, ticker, claim_id)
    recipe_key = f"T{uuid.uuid4().hex[:8]}"

    async with async_session_maker() as db:
        with pytest.raises(Exception):
            await db.execute(
                text(
                    """INSERT INTO deepseek_audit_runs
                       (run_id, job, ticker, output_kind, output, started_at)
                       VALUES (:run_id, 'gap_audit', :ticker, 'ai_gap', '{}'::jsonb, CURRENT_TIMESTAMP)"""
                ),
                {"run_id": f"unversioned-run-{uuid.uuid4().hex}", "ticker": ticker},
            )
            await db.commit()
        await db.rollback()

        await db.execute(
            text(
                """INSERT INTO rank_recipes
                   (recipe_key, recipe_id, name, formula_human, formula_exact, benchmark_vs)
                   VALUES (:recipe_key, 'R1', 'test', 'test', 'test', 'test')"""
            ),
            {"recipe_key": recipe_key},
        )
        await db.commit()

        with pytest.raises(Exception):
            await db.execute(
                text(
                    """INSERT INTO ranked_rows
                       (ticker, recipe_key, universe_version, rank, score, completeness_grade, freshness_ok, kill_active)
                       VALUES (:ticker, :recipe_key, :universe_version, 1, 1.0, 'A', true, false)"""
                ),
                {
                    "ticker": ticker,
                    "recipe_key": recipe_key,
                    "universe_version": universe_version,
                },
            )
            await db.commit()
        await db.rollback()

        run_id = f"append-only-run-{uuid.uuid4().hex}"
        await db.execute(
            text(
                """INSERT INTO deepseek_audit_runs
                   (run_id, job, ticker, output_kind, output, started_at, universe_version)
                   VALUES (:run_id, 'gap_audit', :ticker, 'ai_gap', '{}'::jsonb,
                           CURRENT_TIMESTAMP, :universe_version)"""
            ),
            {
                "run_id": run_id,
                "ticker": ticker,
                "universe_version": universe_version,
            },
        )
        await db.commit()

        with pytest.raises(Exception):
            await db.execute(
                text(
                    """UPDATE deepseek_audit_runs
                       SET status='rejected' WHERE run_id=:run_id"""
                ),
                {"run_id": run_id},
            )
            await db.commit()
        await db.rollback()

        with pytest.raises(Exception):
            await db.execute(
                text("DELETE FROM deepseek_audit_runs WHERE run_id=:run_id"),
                {"run_id": run_id},
            )
            await db.commit()
        await db.rollback()


@pytest.mark.asyncio
async def test_sealed_universe_evidence_and_sources_cannot_be_mutated():
    universe_version = f"univ_evidence_{uuid.uuid4().hex[:24]}"
    ticker = "EVDC"
    claim_id = f"claim-{uuid.uuid4().hex}"
    await _seed_vector_with_claim(universe_version, ticker, claim_id)

    async with async_session_maker() as db:
        snapshot_id = await db.scalar(
            text("SELECT snapshot_id FROM evidence_claims WHERE claim_id=:claim_id"),
            {"claim_id": claim_id},
        )
        with pytest.raises(Exception):
            await db.execute(
                text(
                    """UPDATE evidence_claims SET value_text='changed'
                       WHERE claim_id=:claim_id"""
                ),
                {"claim_id": claim_id},
            )
            await db.commit()
        await db.rollback()
        with pytest.raises(Exception):
            await db.execute(
                text(
                    """UPDATE source_snapshots SET locator='https://changed.example'
                       WHERE snapshot_id=:snapshot_id"""
                ),
                {"snapshot_id": snapshot_id},
            )
            await db.commit()
        await db.rollback()


@pytest.mark.asyncio
async def test_personal_research_records_require_owner_and_sealed_version():
    universe_version = f"univ_owner_{uuid.uuid4().hex[:24]}"
    ticker = "OWNR"
    claim_id = f"claim-{uuid.uuid4().hex}"
    await _seed_vector_with_claim(universe_version, ticker, claim_id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        token, user, _ = await _register_and_verify(client)
        saved = await client.post(
            f"/api/universe/dcf/{ticker}?universe_version={universe_version}",
            headers=_headers(token),
            json={
                "ticker": ticker,
                "growth": 0.12,
                "revenue_usd": 1_000_000,
                "target_margin": 0.15,
                "save": True,
            },
        )
        assert saved.status_code == 200, saved.text
        insufficient = await client.post(
            f"/api/universe/dcf/{ticker}?universe_version={universe_version}",
            headers=_headers(token),
            json={"ticker": ticker, "growth": 0.12, "save": True},
        )
        assert insufficient.status_code == 422
        assert "DCF needs" in insufficient.json()["detail"]

    async with async_session_maker() as db:
        stored_owner = await db.scalar(
            text(
                """SELECT user_id FROM dcf_runs
                   WHERE ticker=:ticker AND universe_version=:universe_version
                   ORDER BY created_at DESC LIMIT 1"""
            ),
            {"ticker": ticker, "universe_version": universe_version},
        )
        assert stored_owner == user["id"]

        with pytest.raises(Exception):
            await db.execute(
                text(
                    """INSERT INTO dcf_runs
                       (run_id, ticker, scenario, inputs, outputs, engine_version, universe_version)
                       VALUES (:run_id, :ticker, 'base', '{}'::jsonb, '{}'::jsonb, 'test', :universe_version)"""
                ),
                {
                    "run_id": f"orphan-dcf-{uuid.uuid4().hex}",
                    "ticker": ticker,
                    "universe_version": universe_version,
                },
            )
            await db.commit()
        await db.rollback()

        with pytest.raises(Exception):
            await db.execute(
                text(
                    """INSERT INTO saved_books
                       (book_id, user_id, name, universe_version, constraints)
                       VALUES (:book_id, :user_id, 'invalid', NULL, '[]'::jsonb)"""
                ),
                {"book_id": f"invalid-book-{uuid.uuid4().hex}", "user_id": user["id"]},
            )
            await db.commit()
        await db.rollback()


@pytest.mark.asyncio
async def test_personal_history_is_append_only_and_owner_version_pinned():
    universe_version = f"univ_history_{uuid.uuid4().hex[:24]}"
    other_version = f"univ_history_other_{uuid.uuid4().hex[:18]}"
    ticker = "HIST"
    claim_id = f"claim-{uuid.uuid4().hex}"
    await _seed_vector_with_claim(universe_version, ticker, claim_id)
    await _seed_vector_with_claim(other_version, "HST2", f"claim-{uuid.uuid4().hex}")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        owner_token, _, _ = await _register_and_verify(client)
        _, other, _ = await _register_and_verify(client)
        headers = _headers(owner_token)

        created = await client.post(
            "/api/books",
            headers=headers,
            json={"name": "Immutable history", "universe_version": universe_version},
        )
        assert created.status_code == 200, created.text
        book_id = created.json()["book_id"]
        saved = await client.put(
            f"/api/books/{book_id}",
            headers=headers,
            json={
                "holdings": [
                    {
                        "ticker": ticker,
                        "weight_pct": 10,
                        "added_at": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            },
        )
        assert saved.status_code == 200, saved.text
        locked = await client.post(
            f"/api/books/{book_id}/lock",
            headers=headers,
            json={"acknowledgements": [ticker]},
        )
        assert locked.status_code == 200, locked.text
        exported = await client.get(f"/api/books/{book_id}/audit-pack", headers=headers)
        assert exported.status_code == 200, exported.text

        dcf = await client.post(
            f"/api/universe/dcf/{ticker}?universe_version={universe_version}",
            headers=headers,
            json={
                "ticker": ticker,
                "growth": 0.12,
                "revenue_usd": 1_000_000,
                "target_margin": 0.15,
                "save": True,
            },
        )
        assert dcf.status_code == 200, dcf.text
        memo = await client.post(
            f"/api/universe/memo/{ticker}",
            headers=headers,
            json={
                "thesis": "The sealed filing claim supports continued research.",
                "citations": [claim_id],
                "universe_version": universe_version,
            },
        )
        assert memo.status_code == 200, memo.text

        delete = await client.delete(f"/api/books/{book_id}", headers=headers)
        assert delete.status_code == 409

    async def must_reject(db, sql: str, params: dict) -> None:
        with pytest.raises(Exception):
            await db.execute(text(sql), params)
            await db.commit()
        await db.rollback()

    async with async_session_maker() as db:
        await must_reject(
            db,
            "UPDATE saved_books SET user_id=:other WHERE book_id=:book_id",
            {"other": other["id"], "book_id": book_id},
        )
        await must_reject(
            db,
            "UPDATE saved_books SET universe_version=:other_version WHERE book_id=:book_id",
            {"other_version": other_version, "book_id": book_id},
        )
        await must_reject(
            db,
            "UPDATE saved_book_holdings SET weight_pct=20 WHERE book_id=:book_id AND ticker=:ticker",
            {"book_id": book_id, "ticker": ticker},
        )
        await must_reject(
            db,
            "UPDATE dcf_runs SET inputs='{}'::jsonb WHERE run_id=:run_id",
            {"run_id": dcf.json()["run_id"]},
        )
        await must_reject(
            db,
            "DELETE FROM dcf_runs WHERE run_id=:run_id",
            {"run_id": dcf.json()["run_id"]},
        )
        await must_reject(
            db,
            "UPDATE company_memos SET thesis='rewritten' WHERE memo_id=:memo_id",
            {"memo_id": memo.json()["memo_id"]},
        )
        await must_reject(
            db,
            "DELETE FROM company_memos WHERE memo_id=:memo_id",
            {"memo_id": memo.json()["memo_id"]},
        )
        await must_reject(
            db,
            "UPDATE audit_exports SET payload='{}'::jsonb WHERE export_id=:export_id",
            {"export_id": exported.json()["export_id"]},
        )
        await must_reject(
            db,
            "DELETE FROM audit_exports WHERE export_id=:export_id",
            {"export_id": exported.json()["export_id"]},
        )

