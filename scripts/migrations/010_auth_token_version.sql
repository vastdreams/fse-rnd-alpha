-- Migration: 010_auth_token_version.sql
-- Purpose: revoke existing stateless user JWTs exactly when a password reset
--          occurs, including resets issued within the same clock second.

ALTER TABLE user_accounts
    ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;
