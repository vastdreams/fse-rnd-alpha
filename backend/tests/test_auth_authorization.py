"""Unit-level guards for durable public-account authorization."""

import asyncio

import jwt
import pytest
from fastapi import HTTPException

from app.api.routes.admin import get_current_admin
from app.api.routes.auth import ALGORITHM, _create_token, require_operator
from app.core.config import settings
from app.services.account_service import public_account


def test_public_account_never_exposes_credential_or_token_fields():
    account = public_account(
        {
            "user_id": "user-1",
            "email": "investor@example.com",
            "full_name": "Investor",
            "role": "user",
            "is_active": True,
            "email_verified_at": object(),
            "password_hash": "must-not-leak",
            "reset_token_hash": "must-not-leak",
            "verification_token_hash": "must-not-leak",
        }
    )

    assert account == {
        "id": "user-1",
        "email": "investor@example.com",
        "full_name": "Investor",
        "role": "user",
        "is_active": True,
        "email_verified": True,
    }


def test_hs256_access_token_round_trips_without_ecdsa_dependency():
    token, expires_in = _create_token(
        {"id": "user-1", "email": "investor@example.com", "role": "user"},
        token_version=3,
    )

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert expires_in > 0
    assert payload["sub"] == "user-1"
    assert payload["tv"] == 3


def test_operator_guard_rejects_public_user():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_operator({"id": "user-1", "role": "user"}))

    assert exc.value.status_code == 403


def test_operator_guard_accepts_operator_and_admin():
    operator = {"id": "operator-1", "role": "operator"}
    admin = {"id": "admin-1", "role": "admin"}

    assert asyncio.run(require_operator(operator)) is operator
    assert asyncio.run(require_operator(admin)) is admin


def test_admin_guard_requires_durable_admin_role():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            get_current_admin(
                {
                    "id": "user-1",
                    "email": "investor@example.com",
                    "role": "user",
                }
            )
        )

    assert exc.value.status_code == 403
    admin = asyncio.run(
        get_current_admin(
            {
                "id": "admin-1",
                "email": "admin@example.com",
                "role": "admin",
            }
        )
    )
    assert admin.username == "admin@example.com"
