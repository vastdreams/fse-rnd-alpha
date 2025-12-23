-- Migration: 003_publication_snapshots.sql
-- Purpose: Add publication_snapshots table for frozen (submission-grade) results
-- Date: December 2025
--
-- Stores a JSON payload containing all tables/metrics used by the on-site Main Paper
-- and supporting Sub-Research pages. This enables reproducible, stable numbers for
-- publication while allowing the live database to keep updating independently.
--
-- ============================================================================
-- PUBLICATION SNAPSHOTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS publication_snapshots (
    id VARCHAR(36) PRIMARY KEY,                 -- UUID
    label VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,

    -- Provenance / reproducibility
    return_convention VARCHAR(20) NOT NULL DEFAULT 'july_june',
    data_tier VARCHAR(10) NOT NULL DEFAULT 'tier1',
    built_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    git_commit VARCHAR(40),
    git_branch VARCHAR(100),
    notes TEXT,

    -- Frozen payload (Postgres JSONB)
    payload JSONB NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_publication_snapshots_active
ON publication_snapshots (is_active);

CREATE INDEX IF NOT EXISTS ix_publication_snapshots_built_at
ON publication_snapshots (built_at);

CREATE INDEX IF NOT EXISTS ix_publication_snapshots_convention
ON publication_snapshots (return_convention);

CREATE INDEX IF NOT EXISTS ix_publication_snapshots_tier
ON publication_snapshots (data_tier);

-- Ensure at most one active snapshot (soft-enforced via partial unique index)
CREATE UNIQUE INDEX IF NOT EXISTS uq_publication_snapshots_one_active
ON publication_snapshots ((is_active))
WHERE is_active = TRUE;

DO $$
BEGIN
    RAISE NOTICE 'Migration 003_publication_snapshots completed successfully';
END $$;


