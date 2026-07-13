-- Migration: 011_release_integrity.sql
-- Purpose: make immutable research builds, tenant ownership, and historical
--          audit records enforceable by PostgreSQL rather than convention.
--
-- This is deliberately forward-only. Earlier migrations remain byte-for-byte
-- unchanged because schema_migrations records their checksums in deployed
-- environments.

-- ============================================================================
-- IMMUTABLE, ACTIVATABLE UNIVERSE BUILDS
-- ============================================================================

ALTER TABLE universe_builds
    ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'sealed';
ALTER TABLE universe_builds
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE universe_builds
    ADD COLUMN IF NOT EXISTS data_manifest_sha256 CHAR(64);
ALTER TABLE universe_builds
    ADD COLUMN IF NOT EXISTS source_sha VARCHAR(64);
ALTER TABLE universe_builds
    ALTER COLUMN sealed_at DROP NOT NULL;
ALTER TABLE universe_builds
    ALTER COLUMN sealed_at DROP DEFAULT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_universe_builds_status'
          AND conrelid = 'universe_builds'::regclass
    ) THEN
        ALTER TABLE universe_builds
            ADD CONSTRAINT ck_universe_builds_status
            CHECK (status IN ('building', 'sealed', 'failed', 'superseded'));
    END IF;
END $$;

-- Existing recorded builds predate the lifecycle state. Treat them as sealed;
-- they are historical evidence and must never become mutable again.
UPDATE universe_builds
   SET status = 'sealed',
       sealed_at = COALESCE(sealed_at, created_at, CURRENT_TIMESTAMP)
 WHERE status IS NULL OR status NOT IN ('building', 'sealed', 'failed', 'superseded');

-- The original vector tables used VARCHAR(40), while content-addressed build
-- IDs can be longer. Widen every persisted reference before adding FKs.
ALTER TABLE metric_vectors
    ALTER COLUMN universe_version TYPE VARCHAR(80);
ALTER TABLE ranked_rows
    ALTER COLUMN universe_version TYPE VARCHAR(80);
ALTER TABLE gate_evaluations
    ALTER COLUMN universe_version TYPE VARCHAR(80);
ALTER TABLE saved_books
    ALTER COLUMN universe_version TYPE VARCHAR(80);
ALTER TABLE dcf_runs
    ALTER COLUMN universe_version TYPE VARCHAR(80);
ALTER TABLE company_memos
    ALTER COLUMN universe_version TYPE VARCHAR(80);
ALTER TABLE audit_exports
    ALTER COLUMN universe_version TYPE VARCHAR(80);

-- Create immutable legacy build records before enforcing the vector FK. The
-- synthetic digest only identifies an unreproducible legacy snapshot; it never
-- asserts that legacy inputs can be replayed.
INSERT INTO universe_builds (
    universe_version, input_sha256, manifest, engine_version, created_at,
    sealed_at, status, is_active
)
SELECT
    versions.universe_version,
    md5('legacy-universe:' || versions.universe_version)
        || md5('legacy-universe:v2:' || versions.universe_version),
    jsonb_build_object('legacy', true, 'reproducible', false),
    'legacy@unknown',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'sealed',
    false
FROM (
    SELECT DISTINCT universe_version
      FROM metric_vectors
) AS versions
ON CONFLICT (universe_version) DO NOTHING;

-- Preserve an existing activation if there is one; otherwise give legacy
-- installations a deterministic active sealed build.
WITH latest AS (
    SELECT universe_version
      FROM universe_builds
     WHERE status = 'sealed'
     ORDER BY sealed_at DESC NULLS LAST, created_at DESC, universe_version DESC
     LIMIT 1
)
UPDATE universe_builds
   SET is_active = true
 WHERE universe_version = (SELECT universe_version FROM latest)
   AND NOT EXISTS (SELECT 1 FROM universe_builds WHERE is_active);

CREATE UNIQUE INDEX IF NOT EXISTS uq_universe_builds_one_active
    ON universe_builds ((is_active)) WHERE is_active;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_metric_vectors_build'
          AND conrelid = 'metric_vectors'::regclass
    ) THEN
        ALTER TABLE metric_vectors
            ADD CONSTRAINT fk_metric_vectors_build
            FOREIGN KEY (universe_version)
            REFERENCES universe_builds(universe_version);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_gate_evaluations_build'
          AND conrelid = 'gate_evaluations'::regclass
    ) THEN
        ALTER TABLE gate_evaluations
            ADD CONSTRAINT fk_gate_evaluations_build
            FOREIGN KEY (universe_version)
            REFERENCES universe_builds(universe_version)
            NOT VALID;
    END IF;
END $$;

CREATE OR REPLACE FUNCTION guard_universe_build_lifecycle()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.is_active AND NEW.status <> 'sealed' THEN
        RAISE EXCEPTION 'only sealed universe builds may be active';
    END IF;

    IF TG_OP = 'UPDATE' AND OLD.status = 'sealed' AND (
        NEW.universe_version IS DISTINCT FROM OLD.universe_version OR
        NEW.input_sha256 IS DISTINCT FROM OLD.input_sha256 OR
        NEW.manifest IS DISTINCT FROM OLD.manifest OR
        NEW.parent_version IS DISTINCT FROM OLD.parent_version OR
        NEW.engine_version IS DISTINCT FROM OLD.engine_version OR
        NEW.created_at IS DISTINCT FROM OLD.created_at OR
        NEW.sealed_at IS DISTINCT FROM OLD.sealed_at OR
        NEW.status IS DISTINCT FROM OLD.status OR
        (
            NEW.data_manifest_sha256 IS DISTINCT FROM OLD.data_manifest_sha256
            AND NOT (
                OLD.data_manifest_sha256 IS NULL
                AND NEW.data_manifest_sha256 IS NOT NULL
            )
        ) OR
        (
            NEW.source_sha IS DISTINCT FROM OLD.source_sha
            AND NOT (OLD.source_sha IS NULL AND NEW.source_sha IS NOT NULL)
        )
    ) THEN
        RAISE EXCEPTION 'sealed universe build % is immutable', OLD.universe_version;
    END IF;

    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_guard_universe_build_lifecycle ON universe_builds;
CREATE TRIGGER trg_guard_universe_build_lifecycle
BEFORE INSERT OR UPDATE ON universe_builds
FOR EACH ROW EXECUTE FUNCTION guard_universe_build_lifecycle();

CREATE OR REPLACE FUNCTION reject_sealed_universe_content_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    build_version VARCHAR(80);
BEGIN
    build_version := COALESCE(NEW.universe_version, OLD.universe_version);
    IF EXISTS (
        SELECT 1
          FROM universe_builds
         WHERE universe_version = build_version
           AND status = 'sealed'
    ) THEN
        RAISE EXCEPTION 'sealed universe % cannot be changed', build_version;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_metric_vectors_immutable ON metric_vectors;
CREATE TRIGGER trg_metric_vectors_immutable
BEFORE INSERT OR UPDATE OR DELETE ON metric_vectors
FOR EACH ROW EXECUTE FUNCTION reject_sealed_universe_content_mutation();

DROP TRIGGER IF EXISTS trg_gate_evaluations_immutable ON gate_evaluations;
CREATE TRIGGER trg_gate_evaluations_immutable
BEFORE INSERT OR UPDATE OR DELETE ON gate_evaluations
FOR EACH ROW EXECUTE FUNCTION reject_sealed_universe_content_mutation();

-- ============================================================================
-- VERSION-SCOPED RESEARCH / TENANT OWNERSHIP
-- ============================================================================

ALTER TABLE deepseek_audit_runs
    ADD COLUMN IF NOT EXISTS universe_version VARCHAR(80);
ALTER TABLE final_reviews
    ADD COLUMN IF NOT EXISTS universe_version VARCHAR(80);
ALTER TABLE audit_trail_entries
    ADD COLUMN IF NOT EXISTS universe_version VARCHAR(80);

CREATE INDEX IF NOT EXISTS ix_deepseek_runs_version_ticker
    ON deepseek_audit_runs (universe_version, ticker, finished_at DESC);
CREATE INDEX IF NOT EXISTS ix_final_reviews_version_ticker
    ON final_reviews (universe_version, ticker, reviewed_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_trail_version_ticker
    ON audit_trail_entries (universe_version, ticker, generated_at DESC);

ALTER TABLE ranked_rows
    ALTER COLUMN kill_active DROP NOT NULL;

ALTER TABLE dcf_runs
    ADD COLUMN IF NOT EXISTS visibility VARCHAR(16) NOT NULL DEFAULT 'private';
UPDATE dcf_runs
   SET visibility = 'reference'
 WHERE user_id IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_dcf_runs_visibility_owner'
          AND conrelid = 'dcf_runs'::regclass
    ) THEN
        ALTER TABLE dcf_runs
            ADD CONSTRAINT ck_dcf_runs_visibility_owner
            CHECK (
                (visibility = 'private' AND user_id IS NOT NULL)
                OR
                (visibility = 'reference' AND user_id IS NULL)
            ) NOT VALID;
    END IF;
END $$;

ALTER TABLE saved_books
    ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE saved_books
    ADD COLUMN IF NOT EXISTS lock_payload JSONB;
ALTER TABLE audit_exports
    ADD COLUMN IF NOT EXISTS book_revision INTEGER;

CREATE TABLE IF NOT EXISTS legacy_data_migrations (
    migration_key VARCHAR(120) PRIMARY KEY,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details JSONB NOT NULL DEFAULT '{}'
);

-- These FKs validate all new rows but deliberately leave unmapped legacy
-- records quarantined until the explicit legacy-account reconciliation passes.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_saved_books_user') THEN
        ALTER TABLE saved_books
            ADD CONSTRAINT fk_saved_books_user
            FOREIGN KEY (user_id) REFERENCES user_accounts(user_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_dcf_runs_user') THEN
        ALTER TABLE dcf_runs
            ADD CONSTRAINT fk_dcf_runs_user
            FOREIGN KEY (user_id) REFERENCES user_accounts(user_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_company_memos_user') THEN
        ALTER TABLE company_memos
            ADD CONSTRAINT fk_company_memos_user
            FOREIGN KEY (user_id) REFERENCES user_accounts(user_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_audit_exports_user') THEN
        ALTER TABLE audit_exports
            ADD CONSTRAINT fk_audit_exports_user
            FOREIGN KEY (user_id) REFERENCES user_accounts(user_id) NOT VALID;
    END IF;
END $$;

