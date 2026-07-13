-- Migration: 004_research_contracts.sql
-- Purpose: W1 contracts for the investor platform redesign (2026-07-12)
-- Tables: source_snapshots, evidence_claims, metric_vectors, rank_recipes,
--         ranked_rows, gate_evaluations, literature_binds, audit_trail_entries,
--         deepseek_audit_runs, final_reviews, saved_books
--
-- Design rules (mirrors backend/app/contracts/research.py):
--  * PIT: as_of_date + available_date on every value-bearing row;
--    CHECK (available_date >= as_of_date) enforces no-look-ahead at rest.
--  * DeepSeek runs carry output_kind restricted by CHECK — metric_value is
--    structurally impossible.
--  * reviewer_passed lives ONLY on final_reviews; ranked_rows reference it.
--  * saved_books start empty; holdings are a separate table with weights.

-- ============================================================================
-- SOURCES & CLAIMS
-- ============================================================================

CREATE TABLE IF NOT EXISTS source_snapshots (
    snapshot_id VARCHAR(80) PRIMARY KEY,
    kind VARCHAR(30) NOT NULL CHECK (kind IN (
        '10-K','20-F','10-Q','8-K','earnings_release','ir_deck',
        'ir_transcript','sharadar_pull','fmp_quote','alphavantage_pull')),
    ticker VARCHAR(12) NOT NULL,
    as_of_date DATE NOT NULL,
    available_date DATE NOT NULL,
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locator TEXT NOT NULL,
    content_sha256 VARCHAR(64) NOT NULL,
    notes TEXT,
    CONSTRAINT ck_snapshot_pit CHECK (available_date >= as_of_date)
);
CREATE INDEX IF NOT EXISTS ix_source_snapshots_ticker ON source_snapshots (ticker);
CREATE INDEX IF NOT EXISTS ix_source_snapshots_kind ON source_snapshots (kind);

CREATE TABLE IF NOT EXISTS evidence_claims (
    claim_id VARCHAR(80) PRIMARY KEY,
    snapshot_id VARCHAR(80) NOT NULL REFERENCES source_snapshots(snapshot_id),
    ticker VARCHAR(12) NOT NULL,
    field VARCHAR(80) NOT NULL,
    value_text TEXT NOT NULL,
    value_numeric DOUBLE PRECISION,
    operator VARCHAR(2) CHECK (operator IN ('=','>','>=','<','<=','~')),
    unit VARCHAR(20),
    excerpt_locator TEXT NOT NULL,
    extractor VARCHAR(120) NOT NULL,
    extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_evidence_claims_ticker_field ON evidence_claims (ticker, field);
CREATE INDEX IF NOT EXISTS ix_evidence_claims_snapshot ON evidence_claims (snapshot_id);

-- ============================================================================
-- METRIC VECTORS (per ticker per universe build; JSONB for the 8 families)
-- ============================================================================

CREATE TABLE IF NOT EXISTS metric_vectors (
    ticker VARCHAR(12) NOT NULL,
    universe_version VARCHAR(40) NOT NULL,
    computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Full MetricVector JSON (validated by the Pydantic contract before insert)
    vector JSONB NOT NULL,
    -- Denormalized hot columns for filtering/sorting
    completeness_grade VARCHAR(12) NOT NULL CHECK (completeness_grade IN ('A','B','C','Incomplete')),
    route VARCHAR(15) CHECK (route IN ('fcf_positive','pre_fcf','carved_out')),
    kill_active BOOLEAN,
    stale BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (ticker, universe_version)
);
CREATE INDEX IF NOT EXISTS ix_metric_vectors_version ON metric_vectors (universe_version);
CREATE INDEX IF NOT EXISTS ix_metric_vectors_grade ON metric_vectors (completeness_grade);

-- ============================================================================
-- RECIPES & RANKS
-- ============================================================================

CREATE TABLE IF NOT EXISTS rank_recipes (
    recipe_key VARCHAR(60) PRIMARY KEY,          -- 'R1'..'R8' or 'R9:<saved name hash>'
    recipe_id VARCHAR(3) NOT NULL CHECK (recipe_id IN ('R1','R2','R3','R4','R5','R6','R7','R8','R9')),
    name VARCHAR(120) NOT NULL,
    formula_human TEXT NOT NULL,
    formula_exact TEXT NOT NULL,
    hard_filters JSONB NOT NULL DEFAULT '[]',
    axes JSONB NOT NULL DEFAULT '[]',
    benchmark_vs TEXT NOT NULL,
    code_hash VARCHAR(64),
    custom BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ranked_rows (
    ticker VARCHAR(12) NOT NULL,
    recipe_key VARCHAR(60) NOT NULL REFERENCES rank_recipes(recipe_key),
    universe_version VARCHAR(40) NOT NULL,
    rank INTEGER NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    contributions JSONB NOT NULL DEFAULT '{}',
    completeness_grade VARCHAR(12) NOT NULL,
    freshness_ok BOOLEAN NOT NULL,
    kill_active BOOLEAN NOT NULL,
    final_review_id VARCHAR(80),                  -- FK added after final_reviews below
    computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, recipe_key, universe_version)
);
CREATE INDEX IF NOT EXISTS ix_ranked_rows_recipe_version ON ranked_rows (recipe_key, universe_version, rank);

CREATE TABLE IF NOT EXISTS gate_evaluations (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(12) NOT NULL,
    gate_id VARCHAR(60) NOT NULL,
    passed BOOLEAN NOT NULL,
    threshold TEXT NOT NULL,
    observed TEXT,
    source_field VARCHAR(80) NOT NULL,
    claim_ids JSONB NOT NULL DEFAULT '[]',
    evaluated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_gate_evaluations_ticker ON gate_evaluations (ticker, gate_id);

-- ============================================================================
-- AUDIT / LITERATURE / AI / REVIEW
-- ============================================================================

CREATE TABLE IF NOT EXISTS literature_binds (
    id SERIAL PRIMARY KEY,
    axis VARCHAR(80) NOT NULL,
    bib_key VARCHAR(80) NOT NULL,
    citation TEXT NOT NULL,
    paper_section VARCHAR(120),
    url_or_doi TEXT,
    UNIQUE (axis, bib_key)
);

CREATE TABLE IF NOT EXISTS deepseek_audit_runs (
    run_id VARCHAR(80) PRIMARY KEY,
    job VARCHAR(20) NOT NULL CHECK (job IN ('filing_map','gap_audit','peer_propose','runthrough','consistency')),
    ticker VARCHAR(12),
    -- HARD RULE: metric_value is not an allowed kind. DeepSeek maps; engines compute.
    output_kind VARCHAR(20) NOT NULL CHECK (output_kind IN
        ('ai_map','ai_gap','ai_runthrough','ai_peer_propose','ai_consistency')),
    output JSONB NOT NULL,
    model VARCHAR(60) NOT NULL DEFAULT 'deepseek-reasoner',
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    status VARCHAR(12) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','mapped','flagged','confirmed','rejected')),
    severity VARCHAR(8) CHECK (severity IN ('low','medium','high'))
);
CREATE INDEX IF NOT EXISTS ix_deepseek_runs_ticker ON deepseek_audit_runs (ticker, status);

CREATE TABLE IF NOT EXISTS final_reviews (
    review_id VARCHAR(80) PRIMARY KEY,
    ticker VARCHAR(12),
    recipe_id VARCHAR(3),
    trigger VARCHAR(20) NOT NULL CHECK (trigger IN ('top_k','random_sample','kill_flip','high_severity_gap')),
    checklist JSONB NOT NULL,
    passed BOOLEAN NOT NULL,
    notes TEXT,
    reviewed_at TIMESTAMP NOT NULL,
    reviewer VARCHAR(60) NOT NULL DEFAULT 'cursor-agent'
);

ALTER TABLE ranked_rows
    ADD CONSTRAINT fk_ranked_rows_review
    FOREIGN KEY (final_review_id) REFERENCES final_reviews(review_id);

CREATE TABLE IF NOT EXISTS audit_trail_entries (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(12) NOT NULL,
    axis VARCHAR(80) NOT NULL,
    metric JSONB NOT NULL,
    snapshot_ids JSONB NOT NULL DEFAULT '[]',
    literature JSONB NOT NULL DEFAULT '[]',
    deepseek_run_id VARCHAR(80) REFERENCES deepseek_audit_runs(run_id),
    final_review_id VARCHAR(80) REFERENCES final_reviews(review_id),
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_audit_trail_ticker_axis ON audit_trail_entries (ticker, axis);

-- ============================================================================
-- BOOKS (server-persisted, empty start, constraints)
-- ============================================================================

CREATE TABLE IF NOT EXISTS saved_books (
    book_id VARCHAR(80) PRIMARY KEY,
    user_id VARCHAR(80) NOT NULL,
    name VARCHAR(120) NOT NULL,
    recipe_id VARCHAR(3),
    universe_version VARCHAR(40),
    constraints JSONB NOT NULL DEFAULT '[]',
    research_only_ack BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_saved_books_user ON saved_books (user_id);

CREATE TABLE IF NOT EXISTS saved_book_holdings (
    book_id VARCHAR(80) NOT NULL REFERENCES saved_books(book_id) ON DELETE CASCADE,
    ticker VARCHAR(12) NOT NULL,
    weight_pct DOUBLE PRECISION NOT NULL CHECK (weight_pct >= 0 AND weight_pct <= 100),
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    override_reason TEXT,
    PRIMARY KEY (book_id, ticker)
);
