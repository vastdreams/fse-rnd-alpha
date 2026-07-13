"""Public account lifecycle: registration, verification, login, and recovery."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.db.session import async_session_maker
from app.services import account_service

router = APIRouter()
security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RegisterResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in: Optional[int] = None
    user: dict
    verification_required: bool
    message: str
    # Test-only escape hatch; production responses never contain raw tokens.
    debug_verification_token: Optional[str] = None


class TokenBody(BaseModel):
    token: str = Field(min_length=16, max_length=512)


class EmailBody(BaseModel):
    email: EmailStr


class ResetPasswordBody(EmailBody):
    token: str = Field(min_length=16, max_length=512)
    password: str = Field(min_length=8, max_length=128)


def _create_token(user: dict, token_version: int) -> tuple[str, int]:
    expires = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    issued_at = datetime.now(timezone.utc).replace(microsecond=0)
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "role": user.get("role", "user"),
        "type": "user",
        "tv": token_version,
        "exp": issued_at + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": issued_at,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    return token, expires


async def ensure_bootstrap_user() -> None:
    """Migrate existing volume accounts and create an explicitly configured seed.

    Migrations run after the first app boot in a fresh release, so a missing
    account table is deliberately deferred rather than allowing startup to
    depend on an image-local auth file.
    """

    async with async_session_maker() as db:
        if not await account_service.accounts_ready(db):
            return
        await account_service.migrate_legacy_json_accounts(db)
        await account_service.ensure_seed_account(db)
        await db.commit()


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if payload.get("type") != "user":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    try:
        user = await account_service.get_account_by_id(db, str(payload.get("sub") or ""))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or missing")
    if settings.AUTH_REQUIRE_EMAIL_VERIFICATION and not user["email_verified"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not verified")
    token_not_before, current_token_version = await account_service.token_state(db, user["id"])
    try:
        token_version = int(payload.get("tv"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token version")
    if token_version != current_token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalidated by a password reset",
        )
    if token_not_before is not None:
        if token_not_before.tzinfo is None:
            token_not_before = token_not_before.replace(tzinfo=timezone.utc)
        raw_issued_at = payload.get("iat")
        try:
            issued_at = datetime.fromtimestamp(float(raw_issued_at), tz=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token issue time")
        if issued_at < token_not_before:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session invalidated by a password reset",
            )
    return user


def _verification_url(token: str) -> str:
    return f"{settings.AUTH_VERIFY_URL}?token={quote(token)}"


def _reset_url(token: str) -> str:
    separator = "&" if "?" in settings.AUTH_RESET_URL else "?"
    return f"{settings.AUTH_RESET_URL}{separator}token={quote(token)}"


async def _send_verification_email(user: dict, token: str) -> bool:
    url = _verification_url(token)
    return await account_service.send_auth_email(
        to=user["email"],
        subject="Verify your Finsoeasy Portfolio account",
        html=(
            "<p>Verify your email to activate your research account.</p>"
            f'<p><a href="{url}">Verify email</a></p>'
        ),
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if settings.AUTH_REQUIRE_EMAIL_VERIFICATION and not settings.DEBUG and not account_service.email_delivery_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account email delivery is not configured",
        )
    try:
        user, verification_token = await account_service.create_account(
            db,
            email=str(body.email),
            password=body.password,
            full_name=body.full_name,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as e:
        detail = str(e)
        response_status = (
            status.HTTP_409_CONFLICT
            if detail == "Email already registered"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=response_status, detail=detail) from e
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    # Persist the account/token before an external email call. A mail-provider
    # timeout must not leave the user believing an account exists when the
    # transaction was rolled back; resend-verification can recover delivery.
    await db.commit()

    if verification_token:
        delivered = await _send_verification_email(user, verification_token)
        return RegisterResponse(
            user=user,
            verification_required=True,
            message=(
                "Check your email to verify your account before signing in."
                if delivered
                else "Account created. Verification delivery is delayed; use resend verification to try again."
            ),
            debug_verification_token=verification_token if settings.DEBUG else None,
        )

    token, expires = _create_token(user, await account_service.token_version(db, user["id"]))
    return RegisterResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires,
        user=user,
        verification_required=False,
        message="Account created.",
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, error = await account_service.authenticate_account(
            db, email=str(body.email), password=body.password
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not user:
        status_code = status.HTTP_403_FORBIDDEN if error == "Verify your email before signing in" else status.HTTP_401_UNAUTHORIZED
        raise HTTPException(status_code=status_code, detail=error or "Invalid email or password")
    await db.commit()
    token, expires = _create_token(user, await account_service.token_version(db, user["id"]))
    return TokenResponse(access_token=token, expires_in=expires, user=user)


@router.post("/verify-email", response_model=TokenResponse)
async def verify_email(body: TokenBody, db: AsyncSession = Depends(get_db)):
    try:
        user = await account_service.verify_account_email(db, body.token)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification link is invalid or expired")
    await db.commit()
    token, expires = _create_token(user, await account_service.token_version(db, user["id"]))
    return TokenResponse(access_token=token, expires_in=expires, user=user)


@router.post("/resend-verification")
async def resend_verification(body: EmailBody, db: AsyncSession = Depends(get_db)):
    if not settings.DEBUG and not account_service.email_delivery_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account email delivery is not configured",
        )
    try:
        user, token = await account_service.issue_verification_token(db, str(body.email))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    await db.commit()
    if user and token and not await _send_verification_email(user, token):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Verification email delivery failed")
    return {
        "ok": True,
        "message": "If the account needs verification, a message has been sent.",
        "debug_verification_token": token if settings.DEBUG else None,
    }


@router.post("/password-reset/request")
async def request_password_reset(body: EmailBody, db: AsyncSession = Depends(get_db)):
    if not settings.DEBUG and not account_service.email_delivery_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account email delivery is not configured",
        )
    try:
        user, token = await account_service.issue_reset_token(db, str(body.email))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    await db.commit()
    if user and token:
        sent = await account_service.send_auth_email(
            to=user["email"],
            subject="Reset your Finsoeasy Portfolio password",
            html=(
                "<p>Use this link to reset your password.</p>"
                f'<p><a href="{_reset_url(token)}">Reset password</a></p>'
            ),
        )
        if not sent:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Password reset email delivery failed")
    return {
        "ok": True,
        "message": "If an active account exists, a password reset link has been sent.",
        "debug_reset_token": token if settings.DEBUG else None,
    }


@router.post("/password-reset/confirm")
async def confirm_password_reset(body: ResetPasswordBody, db: AsyncSession = Depends(get_db)):
    try:
        reset = await account_service.reset_account_password(
            db, email=str(body.email), token=body.token, password=body.password
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not reset:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password reset link is invalid or expired")
    await db.commit()
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    await account_service.invalidate_account_sessions(db, user["id"])
    await db.commit()
    return {"ok": True}


async def require_operator(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in {"operator", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator role required")
    return user
