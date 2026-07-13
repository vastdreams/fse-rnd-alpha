-- Migration: 007_investor_platform_release.sql
-- Purpose: immutable research builds plus public multi-user investor-platform
--          ownership, primary-book, and lock/audit state.

-- A universe build is immutable once recorded. Metric vectors continue to use
-- (ticker, universe_version) as their storage key; this table records exactly
-- what produced that version.
CREATE TABLE IF NOT EXISTS universe_builds (
    universe_version VARCHAR(80) PRIMARY KEY,
    input_sha256 CHAR(64) NOT NULL UNIQUE,
    manifest JSONB NOT NULL DEFAULT '{}',
    parent_version VARCHAR(80) REFERENCES universe_builds(universe_version),
    engine_version VARCHAR(120) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sealed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_universe_builds_created_at ON universe_builds (created_at DESC);

-- Gate results need the same immutable build linkage as their vector.
ALTER TABLE gate_evaluations
    ADD COLUMN IF NOT EXISTS universe_version VARCHAR(80);
CREATE INDEX IF NOT EXISTS ix_gate_evaluations_version_ticker
    ON gate_evaluations (universe_version, ticker, gate_id);

-- Durable account records replace image-local JSON as the authoritative public
-- account store. Token values are hashes; raw verification/reset tokens never
-- enter the database.
CREATE TABLE IF NOT EXISTS user_accounts (
    user_id VARCHAR(80) PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'user'
        CHECK (role IN ('user', 'operator', 'admin')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified_at TIMESTAMPTZ,
    verification_token_hash CHAR(64),
    verification_expires_at TIMESTAMPTZ,
    reset_token_hash CHAR(64),
    reset_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_user_accounts_email ON user_accounts (email);
CREATE INDEX IF NOT EXISTS ix_user_accounts_role ON user_accounts (role);

-- A user chooses a single server-backed default destination for adds from the
-- Universe and Company pages. Book locks are persisted, never localStorage.
ALTER TABLE saved_books
    ADD COLUMN IF NOT EXISTS is_primary BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE saved_books
    ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ;
ALTER TABLE saved_books
    ADD COLUMN IF NOT EXISTS lock_acknowledgements JSONB NOT NULL DEFAULT '[]';
ALTER TABLE saved_books
    ADD COLUMN IF NOT EXISTS lock_version VARCHAR(80);
CREATE UNIQUE INDEX IF NOT EXISTS uq_saved_books_one_primary_per_user
    ON saved_books (user_id) WHERE is_primary;

CREATE TABLE IF NOT EXISTS audit_exports (
    export_id VARCHAR(80) PRIMARY KEY,
    book_id VARCHAR(80) REFERENCES saved_books(book_id) ON DELETE SET NULL,
    user_id VARCHAR(80) NOT NULL,
    universe_version VARCHAR(80),
    payload_sha256 CHAR(64) NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_audit_exports_user_created
    ON audit_exports (user_id, generated_at DESC);
