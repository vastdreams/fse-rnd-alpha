-- Migration: 023_company_report_snapshots.sql
-- Purpose: Immutable two-page company brief snapshots, licensed consensus
-- PIT snapshots, and rendered artifact ledger (PDF / canonical JSON).
--
-- Rules:
-- - Snapshot content is write-once. Only the workflow columns
--   (status, reviewed_by, reviewed_at, published_at) may advance, and only
--   forward: draft -> validated -> reviewed -> published.
-- - Published snapshots can never be deleted or altered; corrections are a
--   new snapshot_id.
-- - Consensus snapshots and artifacts are append-only.

CREATE TABLE IF NOT EXISTS company_report_snapshots (
    snapshot_id      VARCHAR(80) PRIMARY KEY,
    ticker           VARCHAR(12) NOT NULL,
    universe_version VARCHAR(40) NOT NULL,
    template_version VARCHAR(40) NOT NULL,
    engine_version   VARCHAR(60) NOT NULL,
    status           VARCHAR(16) NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft','validated','reviewed','published')),
    content          JSONB NOT NULL,
    content_sha256   CHAR(64) NOT NULL,
    created_by       VARCHAR(80) NOT NULL,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_by      VARCHAR(80),
    reviewed_at      TIMESTAMP,
    published_at     TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_company_report_snapshots_ticker
    ON company_report_snapshots (ticker, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_company_report_snapshots_status
    ON company_report_snapshots (status, ticker);

CREATE TABLE IF NOT EXISTS consensus_snapshots (
    consensus_id   VARCHAR(80) PRIMARY KEY,
    ticker         VARCHAR(12) NOT NULL,
    provider       VARCHAR(40) NOT NULL,
    kind           VARCHAR(40) NOT NULL,   -- analyst_estimates | price_targets
    payload        JSONB NOT NULL,
    payload_sha256 CHAR(64) NOT NULL,
    as_of_date     DATE NOT NULL,
    available_date DATE NOT NULL,
    fetched_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (available_date >= as_of_date)
);
CREATE INDEX IF NOT EXISTS ix_consensus_snapshots_ticker
    ON consensus_snapshots (ticker, kind, as_of_date DESC);

CREATE TABLE IF NOT EXISTS company_report_artifacts (
    artifact_id      VARCHAR(80) PRIMARY KEY,
    snapshot_id      VARCHAR(80) NOT NULL REFERENCES company_report_snapshots(snapshot_id),
    kind             VARCHAR(16) NOT NULL CHECK (kind IN ('pdf','json')),
    storage_key      TEXT NOT NULL,
    sha256           CHAR(64) NOT NULL,
    renderer_version VARCHAR(120),
    n_pages          INTEGER,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_company_report_artifacts_snapshot
    ON company_report_artifacts (snapshot_id, kind, created_at DESC);

-- Workflow integrity: content is frozen at insert; status only moves forward.
CREATE OR REPLACE FUNCTION company_report_snapshot_guard() RETURNS trigger AS $$
DECLARE
    order_old INTEGER;
    order_new INTEGER;
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.status = 'published' THEN
            RAISE EXCEPTION 'published report snapshots are immutable';
        END IF;
        RETURN OLD;
    END IF;
    IF NEW.content IS DISTINCT FROM OLD.content
       OR NEW.content_sha256 IS DISTINCT FROM OLD.content_sha256
       OR NEW.snapshot_id IS DISTINCT FROM OLD.snapshot_id
       OR NEW.ticker IS DISTINCT FROM OLD.ticker
       OR NEW.universe_version IS DISTINCT FROM OLD.universe_version
       OR NEW.template_version IS DISTINCT FROM OLD.template_version
       OR NEW.engine_version IS DISTINCT FROM OLD.engine_version
       OR NEW.created_by IS DISTINCT FROM OLD.created_by
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'report snapshot content is write-once; create a new snapshot';
    END IF;
    order_old := array_position(ARRAY['draft','validated','reviewed','published'], OLD.status);
    order_new := array_position(ARRAY['draft','validated','reviewed','published'], NEW.status);
    IF order_new < order_old THEN
        RAISE EXCEPTION 'report status can only advance (was %, got %)', OLD.status, NEW.status;
    END IF;
    IF NEW.status = 'published' AND NEW.reviewed_by IS NULL THEN
        RAISE EXCEPTION 'cannot publish a report without an independent review';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_company_report_snapshot_guard ON company_report_snapshots;
CREATE TRIGGER trg_company_report_snapshot_guard
    BEFORE UPDATE OR DELETE ON company_report_snapshots
    FOR EACH ROW EXECUTE FUNCTION company_report_snapshot_guard();

-- Consensus and artifacts are strictly append-only.
CREATE OR REPLACE FUNCTION report_append_only_guard() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '% rows are append-only', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_consensus_snapshots_append_only ON consensus_snapshots;
CREATE TRIGGER trg_consensus_snapshots_append_only
    BEFORE UPDATE OR DELETE ON consensus_snapshots
    FOR EACH ROW EXECUTE FUNCTION report_append_only_guard();

DROP TRIGGER IF EXISTS trg_company_report_artifacts_append_only ON company_report_artifacts;
CREATE TRIGGER trg_company_report_artifacts_append_only
    BEFORE UPDATE OR DELETE ON company_report_artifacts
    FOR EACH ROW EXECUTE FUNCTION report_append_only_guard();
