-- Migration: 006_memos.sql
-- Purpose: W4 versioned company memos (thesis). Sentences must cite a claim id
-- or be explicitly labeled Analyst judgment — enforced in the UI/report builder,
-- stored verbatim here with the version chain.

CREATE TABLE IF NOT EXISTS company_memos (
    memo_id VARCHAR(80) PRIMARY KEY,
    ticker VARCHAR(12) NOT NULL,
    user_id VARCHAR(80) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    thesis TEXT NOT NULL,
    risks TEXT,
    citations JSONB NOT NULL DEFAULT '[]',      -- claim ids referenced by the memo
    analyst_judgment_ack BOOLEAN NOT NULL DEFAULT FALSE,
    universe_version VARCHAR(40),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (ticker, user_id, version)
);
CREATE INDEX IF NOT EXISTS ix_company_memos_ticker ON company_memos (ticker, user_id, version DESC);
