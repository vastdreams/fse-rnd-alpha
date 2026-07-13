"""Durable public-account service backed by PostgreSQL.

Password hashes and one-way verification/reset token hashes live in the
database. The legacy JSON file is migrated once on startup only so a public
multi-user deployment does not depend on image-local state.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services import auth_users


VALID_ROLES = {"user", "operator", "admin"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _token_hash(token: str) -> str:
    # A database leak must not make reset/verification links usable.
    return hashlib.sha256(f"{settings.SECRET_KEY}:{token}".encode("utf-8")).hexdigest()


def _normal_email(email: str) -> str:
    return email.strip().lower()


def public_account(row: Any) -> dict[str, Any]:
    mapping = dict(row)
    return {
        "id": str(mapping["user_id"]),
        "email": mapping["email"],
        "full_name": mapping.get("full_name"),
        "role": mapping.get("role", "user"),
        "is_active": bool(mapping.get("is_active", True)),
        "email_verified": mapping.get("email_verified_at") is not None,
    }


async def accounts_ready(db: AsyncSession) -> bool:
    return (
        await db.execute(text("SELECT to_regclass('public.user_accounts')"))
    ).scalar_one() is not None


async def _require_accounts_table(db: AsyncSession) -> None:
    if not await accounts_ready(db):
        raise RuntimeError(
            "Account database is not ready; apply migration "
            "007_investor_platform_release.sql."
        )


async def migrate_legacy_json_accounts(db: AsyncSession) -> int:
    """Import legacy accounts without letting an email collision claim history.

    A pre-existing public account with the same email is not proof that it is
    the old JSON account. Only a newly imported account—or an exact durable-ID,
    email, and password-hash match from a partial prior import—may receive a
    legacy identity mapping. Quarantined records without that proof stay
    quarantined for explicit operator reconciliation.
    """

    await _require_accounts_table(db)
    already_imported = await db.scalar(
        text(
            """SELECT 1 FROM legacy_data_migrations
               WHERE migration_key='auth_users_json_to_user_accounts_v2'"""
        )
    )
    if already_imported:
        return 0
    migrated = 0
    for user in auth_users.list_users():
        email = _normal_email(str(user.get("email") or ""))
        password_hash = str(user.get("password_hash") or "")
        if not email or not password_hash:
            continue
        legacy_id = str(user.get("id") or "")
        result = await db.execute(
            text(
                """INSERT INTO user_accounts
                   (user_id, email, password_hash, full_name, role, is_active, email_verified_at)
                   VALUES (:id, :email, :password_hash, :full_name, 'user', :is_active, :verified)
                   ON CONFLICT (email) DO NOTHING
                   RETURNING user_id"""
            ),
            {
                "id": legacy_id or str(uuid.uuid4()),
                "email": email,
                "password_hash": password_hash,
                "full_name": user.get("full_name"),
                "is_active": bool(user.get("is_active", True)),
                # Existing private accounts predate email verification.
                "verified": utc_now(),
            },
        )
        account_id = result.scalar_one_or_none()
        if account_id is not None:
            migrated += 1
        elif legacy_id:
            # A previous partial import may already have created this exact
            # account. Do not accept an email-only match: it could belong to a
            # subsequently registered, unrelated person.
            account_id = await db.scalar(
                text(
                    """SELECT user_id FROM user_accounts
                       WHERE user_id=:legacy_id
                         AND email=:email
                         AND password_hash=:password_hash"""
                ),
                {
                    "legacy_id": legacy_id,
                    "email": email,
                    "password_hash": password_hash,
                },
            )
        if account_id is None:
            continue
        for legacy_identity in {legacy_id, email} - {""}:
            await db.execute(
                text(
                    """INSERT INTO legacy_account_identities
                       (legacy_user_id, account_user_id, legacy_email)
                       VALUES (:legacy_id, :account_id, :email)
                       ON CONFLICT (legacy_user_id) DO NOTHING"""
                ),
                {
                    "legacy_id": legacy_identity,
                    "account_id": str(account_id),
                    "email": email,
                },
            )

    identity_table_exists = await db.scalar(
        text("SELECT to_regclass('public.legacy_account_identities')")
    )
    if identity_table_exists is None:
        # This can happen only during an old-schema recovery. Do not fall back
        # to email matching, which could silently assign another user's data.
        return migrated

    # Earlier investor routes used an email or legacy account ID as the
    # ownership key. Reconcile only rows proven by the durable identity table.
    for table in ("saved_books", "dcf_runs", "company_memos", "audit_exports"):
        table_exists = await db.execute(text("SELECT to_regclass(:table)"), {"table": f"public.{table}"})
        if table_exists.scalar_one() is None:
            continue
        visibility_update = (
            ", visibility='private'"
            if table == "dcf_runs"
            else ""
        )
        await db.execute(
            text(
                f"""UPDATE {table} AS record
                    SET user_id=identity.account_user_id,
                        owner_state='owned'{visibility_update}
                    FROM legacy_account_identities AS identity
                    WHERE record.user_id=identity.legacy_user_id
                      AND record.owner_state='quarantined'
                      AND record.universe_version IS NOT NULL
                      AND EXISTS (
                          SELECT 1
                            FROM universe_builds AS build
                           WHERE build.universe_version=record.universe_version
                             AND build.status='sealed'
                      )"""
            )
        )
    await db.execute(
        text(
            """INSERT INTO legacy_data_migrations (migration_key, details)
               VALUES ('auth_users_json_to_user_accounts_v2', :details)
               ON CONFLICT (migration_key) DO NOTHING"""
        ),
        {"details": json.dumps({"accounts_imported": migrated})},
    )
    return migrated


async def _ensure_seed_account(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    role: str,
    full_name: str,
) -> None:
    """Create one idempotent, verified operational account without rotation."""

    if bool(email) != bool(password):
        raise ValueError("Seed account email and password must be set together")
    if not email:
        return
    await _require_accounts_table(db)
    exists = await db.execute(
        text("SELECT 1 FROM user_accounts WHERE email=:email"), {"email": email}
    )
    if exists.scalar_one_or_none():
        return
    role = role.strip().lower()
    if role not in VALID_ROLES:
        raise ValueError("Seed account role must be user, operator, or admin")
    await db.execute(
        text(
            """INSERT INTO user_accounts
               (user_id, email, password_hash, full_name, role, is_active, email_verified_at)
               VALUES (:id, :email, :password_hash, :full_name, :role, true, :verified)"""
        ),
        {
            "id": str(uuid.uuid4()),
            "email": email,
            "password_hash": auth_users.hash_password(password),
            "full_name": full_name,
            "role": role,
            "verified": utc_now(),
        },
    )


async def ensure_seed_account(db: AsyncSession) -> None:
    """Create optional primary and secondary operational accounts.

    The secondary seed exists solely for a fresh host's two-user release smoke.
    Both accounts are verified and idempotent; existing password hashes are
    never rotated from environment values.
    """

    primary_email = _normal_email(os.environ.get("AUTH_SEED_EMAIL", ""))
    primary_password = os.environ.get("AUTH_SEED_PASSWORD", "")
    secondary_email = _normal_email(os.environ.get("AUTH_SECONDARY_SEED_EMAIL", ""))
    secondary_password = os.environ.get("AUTH_SECONDARY_SEED_PASSWORD", "")
    if primary_email and secondary_email and primary_email == secondary_email:
        raise ValueError("AUTH_SEED_EMAIL and AUTH_SECONDARY_SEED_EMAIL must differ")
    await _ensure_seed_account(
        db,
        email=primary_email,
        password=primary_password,
        role=settings.AUTH_SEED_ROLE,
        full_name="Bootstrap primary account",
    )
    await _ensure_seed_account(
        db,
        email=secondary_email,
        password=secondary_password,
        role=settings.AUTH_SECONDARY_SEED_ROLE,
        full_name="Bootstrap secondary smoke account",
    )


async def create_account(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: Optional[str],
) -> tuple[dict[str, Any], Optional[str]]:
    await _require_accounts_table(db)
    if not settings.AUTH_PUBLIC_REGISTRATION:
        raise PermissionError("Public registration is disabled")
    normalized = _normal_email(email)
    if not normalized or "@" not in normalized:
        raise ValueError("Invalid email")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    existing = await db.execute(
        text("SELECT 1 FROM user_accounts WHERE email=:email"), {"email": normalized}
    )
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    verify_token: Optional[str] = None
    verified_at: Optional[datetime] = None
    token_hash: Optional[str] = None
    token_expires: Optional[datetime] = None
    if settings.AUTH_REQUIRE_EMAIL_VERIFICATION:
        verify_token = secrets.token_urlsafe(32)
        token_hash = _token_hash(verify_token)
        token_expires = utc_now() + timedelta(
            minutes=settings.AUTH_VERIFICATION_TTL_MINUTES
        )
    else:
        verified_at = utc_now()

    try:
        # The preflight query makes the normal duplicate path friendly. The
        # savepoint converts the remaining concurrent unique-key race into the
        # same stable conflict without poisoning the request transaction.
        async with db.begin_nested():
            result = await db.execute(
                text(
                    """INSERT INTO user_accounts
                       (user_id, email, password_hash, full_name, role, is_active,
                        email_verified_at, verification_token_hash, verification_expires_at)
                       VALUES (:id, :email, :password_hash, :full_name, 'user', true,
                        :verified, :token_hash, :token_expires)
                       RETURNING user_id, email, full_name, role, is_active, email_verified_at"""
                ),
                {
                    "id": str(uuid.uuid4()),
                    "email": normalized,
                    "password_hash": auth_users.hash_password(password),
                    "full_name": (full_name or "").strip() or None,
                    "verified": verified_at,
                    "token_hash": token_hash,
                    "token_expires": token_expires,
                },
            )
    except IntegrityError as exc:
        raise ValueError("Email already registered") from exc
    row = result.mappings().one()
    return public_account(row), verify_token


async def authenticate_account(
    db: AsyncSession, *, email: str, password: str
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    await _require_accounts_table(db)
    normalized = _normal_email(email)
    row = (
        await db.execute(
            text(
                """SELECT user_id, email, password_hash, full_name, role, is_active,
                          email_verified_at
                   FROM user_accounts WHERE email=:email"""
            ),
            {"email": normalized},
        )
    ).mappings().first()
    if not row or not row["is_active"]:
        return None, "Invalid email or password"
    if not auth_users.verify_password(password, row["password_hash"]):
        return None, "Invalid email or password"
    if settings.AUTH_REQUIRE_EMAIL_VERIFICATION and row["email_verified_at"] is None:
        return None, "Verify your email before signing in"
    await db.execute(
        text(
            "UPDATE user_accounts SET last_login_at=:now, updated_at=:now "
            "WHERE user_id=:id"
        ),
        {"now": utc_now(), "id": row["user_id"]},
    )
    return public_account(row), None


async def get_account_by_id(db: AsyncSession, user_id: str) -> Optional[dict[str, Any]]:
    await _require_accounts_table(db)
    row = (
        await db.execute(
            text(
                """SELECT user_id, email, full_name, role, is_active, email_verified_at
                   FROM user_accounts WHERE user_id=:id"""
            ),
            {"id": user_id},
        )
    ).mappings().first()
    return public_account(row) if row else None


async def token_state(db: AsyncSession, user_id: str) -> tuple[Optional[datetime], int]:
    """Return private session-revocation state without exposing it in profiles."""

    await _require_accounts_table(db)
    row = (
        await db.execute(
            text(
                """SELECT token_not_before, token_version
                   FROM user_accounts WHERE user_id=:id"""
            ),
            {"id": user_id},
        )
    ).mappings().first()
    if row is None:
        return None, 0
    return (
        row["token_not_before"],
        int(row["token_version"] or 0),
    )


async def token_version(db: AsyncSession, user_id: str) -> int:
    """Compatibility helper for issuance paths."""

    _, version = await token_state(db, user_id)
    return version


async def invalidate_account_sessions(db: AsyncSession, user_id: str) -> None:
    """Revoke every stateless JWT for an account, including a logout session."""

    await _require_accounts_table(db)
    now = utc_now().replace(microsecond=0)
    await db.execute(
        text(
            """UPDATE user_accounts
               SET token_not_before=:now, token_version=token_version + 1,
                   updated_at=:now
               WHERE user_id=:id"""
        ),
        {"now": now, "id": user_id},
    )


async def verify_account_email(db: AsyncSession, token: str) -> Optional[dict[str, Any]]:
    await _require_accounts_table(db)
    row = (
        await db.execute(
            text(
                """UPDATE user_accounts
                   SET email_verified_at=:now, verification_token_hash=NULL,
                       verification_expires_at=NULL, updated_at=:now
                   WHERE verification_token_hash=:token_hash
                     AND verification_expires_at > :now
                   RETURNING user_id, email, full_name, role, is_active, email_verified_at"""
            ),
            {"now": utc_now(), "token_hash": _token_hash(token)},
        )
    ).mappings().first()
    return public_account(row) if row else None


async def issue_verification_token(
    db: AsyncSession, email: str
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    await _require_accounts_table(db)
    row = (
        await db.execute(
            text(
                """SELECT user_id, email, full_name, role, is_active, email_verified_at
                   FROM user_accounts WHERE email=:email"""
            ),
            {"email": _normal_email(email)},
        )
    ).mappings().first()
    if not row or not row["is_active"] or row["email_verified_at"] is not None:
        return None, None
    token = secrets.token_urlsafe(32)
    now = utc_now()
    await db.execute(
        text(
            """UPDATE user_accounts
               SET verification_token_hash=:token_hash,
                   verification_expires_at=:expires, updated_at=:now
               WHERE user_id=:id"""
        ),
        {
            "token_hash": _token_hash(token),
            "expires": now + timedelta(minutes=settings.AUTH_VERIFICATION_TTL_MINUTES),
            "now": now,
            "id": row["user_id"],
        },
    )
    return public_account(row), token


async def issue_reset_token(db: AsyncSession, email: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    await _require_accounts_table(db)
    normalized = _normal_email(email)
    row = (
        await db.execute(
            text(
                """SELECT user_id, email, full_name, role, is_active, email_verified_at
                   FROM user_accounts WHERE email=:email"""
            ),
            {"email": normalized},
        )
    ).mappings().first()
    if not row or not row["is_active"]:
        return None, None
    token = secrets.token_urlsafe(32)
    expires = utc_now() + timedelta(minutes=settings.AUTH_RESET_TTL_MINUTES)
    await db.execute(
        text(
            """UPDATE user_accounts
               SET reset_token_hash=:token_hash, reset_expires_at=:expires,
                   updated_at=:now WHERE user_id=:id"""
        ),
        {
            "token_hash": _token_hash(token),
            "expires": expires,
            "now": utc_now(),
            "id": row["user_id"],
        },
    )
    return public_account(row), token


async def reset_account_password(
    db: AsyncSession, *, email: str, token: str, password: str
) -> bool:
    await _require_accounts_table(db)
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    # JWT `iat` has second precision; normalize the cutoff so a freshly issued
    # token in this same second is valid while every earlier token is revoked.
    now = utc_now().replace(microsecond=0)
    result = await db.execute(
        text(
            """UPDATE user_accounts
               SET password_hash=:password_hash, reset_token_hash=NULL,
                   reset_expires_at=NULL, token_not_before=:now,
                   token_version=token_version + 1, updated_at=:now
               WHERE email=:email AND reset_token_hash=:token_hash
                 AND reset_expires_at > :now"""
        ),
        {
            "password_hash": auth_users.hash_password(password),
            "now": now,
            "email": _normal_email(email),
            "token_hash": _token_hash(token),
        },
    )
    return bool(result.rowcount)


def email_delivery_configured() -> bool:
    return bool(settings.RESEND_API_KEY and settings.AUTH_EMAIL_FROM)


async def send_auth_email(*, to: str, subject: str, html: str) -> bool:
    """Send through Resend. Debug mode deliberately avoids external email."""

    if settings.DEBUG:
        return True
    if not email_delivery_configured():
        return False
    try:
        import resend

        resend.api_key = settings.RESEND_API_KEY
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": settings.AUTH_EMAIL_FROM,
                "to": [to],
                "subject": subject,
                "html": html,
            },
        )
        return True
    except Exception:
        return False
