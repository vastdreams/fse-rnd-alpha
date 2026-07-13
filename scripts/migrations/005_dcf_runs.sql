-- Migration: 005_dcf_runs.sql
-- Purpose: W4 DCF workbench — saved, reproducible valuation runs.
-- Every run stores its full assumption set + engine version so any fair value
-- shown in the UI can be recomputed from frozen inputs (kill criterion:
-- "bundle still hand-edited / unreproducible → stop ship").

CREATE TABLE IF NOT EXISTS dcf_runs (
    run_id VARCHAR(80) PRIMARY KEY,
    ticker VARCHAR(12) NOT NULL,
    user_id VARCHAR(80),                         -- NULL = pipeline/base run
    scenario VARCHAR(20) NOT NULL DEFAULT 'base' CHECK (scenario IN ('base','bear','bull','custom')),
    -- Frozen inputs (JSON: revenue, margins, wacc, terminal_g, tgt_margin, conv_k, net_cash, shares …)
    inputs JSONB NOT NULL,
    -- Frozen outputs (fair_px_lo/med/hi, ev components, implied growth …)
    outputs JSONB NOT NULL,
    engine_version VARCHAR(60) NOT NULL,
    universe_version VARCHAR(40),
    snapshot_ids JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_dcf_runs_ticker ON dcf_runs (ticker, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_dcf_runs_user ON dcf_runs (user_id);
