-- Migration: 008_auth_session_invalidation.sql
-- Purpose: invalidate all existing JWTs after a public-account password reset.
--
-- JWTs are stateless, so reset flows need a durable not-before timestamp rather
-- than trusting clients to discard old tokens.

ALTER TABLE user_accounts
    ADD COLUMN IF NOT EXISTS token_not_before TIMESTAMPTZ;
