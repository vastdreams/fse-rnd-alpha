"""
PATH: backend/app/services/auth_users.py
PURPOSE: Password hashing + durable user store (JSON file, DB optional).
WHY: Auth must work even when Postgres is down (local preview / partial deploy).
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import bcrypt

_LOCK = threading.Lock()
# Prefer Docker volume (/app/data) so accounts survive image rebuilds.
_VOLUME = Path("/app/data/auth_users.json")
_PACKAGE = Path(__file__).resolve().parents[1] / "data" / "auth_users.json"


def store_path() -> Path:
    """Resolve the durable account store at call time.

    Docker volume mounts can appear after Python imports this module. Resolving
    lazily prevents a startup race from silently selecting the image-local
    package path and losing public accounts on the next deploy.
    """

    configured = os.environ.get("AUTH_USERS_PATH", "").strip()
    if configured:
        return Path(configured)
    return _VOLUME if _VOLUME.parent.exists() else _PACKAGE


def hash_password(password: str) -> str:
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def _read() -> dict[str, Any]:
    store = store_path()
    if not store.exists():
        return {"users": []}
    try:
        return json.loads(store.read_text())
    except Exception:
        return {"users": []}


def _write(data: dict[str, Any]) -> None:
    store = store_path()
    store.parent.mkdir(parents=True, exist_ok=True)
    tmp = store.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(store)


def list_users() -> list[dict[str, Any]]:
    with _LOCK:
        return list(_read().get("users") or [])


def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    email_n = email.strip().lower()
    for u in list_users():
        if (u.get("email") or "").lower() == email_n:
            return u
    return None


def get_user_by_id(user_id: str) -> Optional[dict[str, Any]]:
    for u in list_users():
        if str(u.get("id")) == str(user_id):
            return u
    return None


def create_user(email: str, password: str, full_name: Optional[str] = None) -> dict[str, Any]:
    email_n = email.strip().lower()
    if "@" not in email_n or "." not in email_n.split("@")[-1]:
        raise ValueError("Invalid email")
    if get_user_by_email(email_n):
        raise ValueError("Email already registered")
    user = {
        "id": str(uuid.uuid4()),
        "email": email_n,
        "password_hash": hash_password(password),
        "full_name": (full_name or "").strip() or None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
    }
    with _LOCK:
        data = _read()
        data.setdefault("users", []).append(user)
        _write(data)
    return {k: v for k, v in user.items() if k != "password_hash"}


def authenticate(email: str, password: str) -> Optional[dict[str, Any]]:
    user = get_user_by_email(email)
    if not user or not user.get("is_active"):
        return None
    if not verify_password(password, user.get("password_hash") or ""):
        return None
    with _LOCK:
        data = _read()
        for u in data.get("users") or []:
            if u.get("id") == user["id"]:
                u["last_login"] = datetime.now(timezone.utc).isoformat()
                break
        _write(data)
    return {k: v for k, v in user.items() if k != "password_hash"}


def ensure_seed_user(email: str, password: str, full_name: str = "Abhishek Sehgal") -> dict[str, Any]:
    """Idempotent bootstrap account."""
    existing = get_user_by_email(email)
    if existing:
        # If password was rotated, update hash
        if not verify_password(password, existing.get("password_hash") or ""):
            with _LOCK:
                data = _read()
                for u in data.get("users") or []:
                    if (u.get("email") or "").lower() == email.strip().lower():
                        u["password_hash"] = hash_password(password)
                        u["full_name"] = full_name
                        break
                _write(data)
        return {k: v for k, v in (get_user_by_email(email) or {}).items() if k != "password_hash"}
    return create_user(email, password, full_name=full_name)


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "is_active": user.get("is_active", True),
    }
