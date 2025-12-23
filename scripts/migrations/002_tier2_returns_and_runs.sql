-- Migration: 002_tier2_returns_and_runs.sql
-- Purpose: Extend july_june_returns for Tier-2 storage + add ComputationRun table
-- Date: December 2025
-- Author: Tier-2 WRDS Upgrade
--
-- This migration adds:
-- 1. data_tier, permno, computation_run_id to july_june_returns
-- 2. computation_run_id to anova_results and factor_premiums
-- 3. computation_runs table for run metadata
-- 4. Updated PK/unique constraints for multi-tier storage

-- ============================================================================
-- JULY JUNE RETURNS - Extend for Tier-2
-- ============================================================================

-- Add new columns (safe if they don't exist)
ALTER TABLE july_june_returns 
ADD COLUMN IF NOT EXISTS data_tier VARCHAR(10) DEFAULT 'tier1';

ALTER TABLE july_june_returns 
ADD COLUMN IF NOT EXISTS permno INTEGER;

ALTER TABLE july_june_returns 
ADD COLUMN IF NOT EXISTS computation_run_id VARCHAR(36);

-- Update existing records to have explicit tier
UPDATE july_june_returns 
SET data_tier = 'tier1' 
WHERE data_tier IS NULL;

-- The PK change (adding data_tier) requires recreating the table in Postgres
-- We'll do this carefully to preserve data:

-- Step 1: Create new table with correct PK
CREATE TABLE IF NOT EXISTS july_june_returns_new (
    symbol VARCHAR(20) NOT NULL,
    formation_year INTEGER NOT NULL,
    data_tier VARCHAR(10) NOT NULL DEFAULT 'tier1',
    permno INTEGER,
    july_start_price NUMERIC,
    june_end_price NUMERIC,
    total_return NUMERIC,
    annualized_return NUMERIC,
    volatility NUMERIC,
    trading_days INTEGER,
    computation_run_id VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, formation_year, data_tier)
);

-- Step 2: Copy existing data
INSERT INTO july_june_returns_new 
    (symbol, formation_year, data_tier, permno, july_start_price, june_end_price,
     total_return, annualized_return, volatility, trading_days, computation_run_id, created_at)
SELECT 
    symbol, formation_year, COALESCE(data_tier, 'tier1'), permno, july_start_price, june_end_price,
    total_return, annualized_return, volatility, trading_days, computation_run_id, created_at
FROM july_june_returns
ON CONFLICT (symbol, formation_year, data_tier) DO NOTHING;

-- Step 3: Swap tables (only if new table has data or old table is empty)
DO $$
DECLARE
    old_count INTEGER;
    new_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO old_count FROM july_june_returns;
    SELECT COUNT(*) INTO new_count FROM july_june_returns_new;
    
    IF new_count >= old_count OR old_count = 0 THEN
        DROP TABLE IF EXISTS july_june_returns_backup;
        ALTER TABLE july_june_returns RENAME TO july_june_returns_backup;
        ALTER TABLE july_june_returns_new RENAME TO july_june_returns;
        RAISE NOTICE 'Swapped july_june_returns tables (old: %, new: %)', old_count, new_count;
    ELSE
        DROP TABLE july_june_returns_new;
        RAISE NOTICE 'Kept original july_june_returns (count mismatch: old=%, new=%)', old_count, new_count;
    END IF;
END $$;

-- Add indexes
CREATE INDEX IF NOT EXISTS ix_july_june_tier ON july_june_returns (data_tier);
CREATE INDEX IF NOT EXISTS ix_july_june_permno ON july_june_returns (permno);

-- ============================================================================
-- ANOVA RESULTS - Add computation_run_id
-- ============================================================================

ALTER TABLE anova_results 
ADD COLUMN IF NOT EXISTS computation_run_id VARCHAR(36);

-- ============================================================================
-- FACTOR PREMIUMS - Add computation_run_id
-- ============================================================================

ALTER TABLE factor_premiums 
ADD COLUMN IF NOT EXISTS computation_run_id VARCHAR(36);

-- ============================================================================
-- COMPUTATION RUNS - New table for run metadata
-- ============================================================================

CREATE TABLE IF NOT EXISTS computation_runs (
    id VARCHAR(36) PRIMARY KEY,
    computation_type VARCHAR(50) NOT NULL,
    return_convention VARCHAR(20) NOT NULL,
    data_tier VARCHAR(10) NOT NULL,
    window_types VARCHAR(50),
    start_year INTEGER,
    end_year INTEGER,
    git_commit VARCHAR(40),
    git_branch VARCHAR(100),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',
    records_created INTEGER,
    records_updated INTEGER,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS ix_computation_run_type ON computation_runs (computation_type);
CREATE INDEX IF NOT EXISTS ix_computation_run_tier ON computation_runs (data_tier);
CREATE INDEX IF NOT EXISTS ix_computation_run_status ON computation_runs (status);

-- ============================================================================
-- VALIDATION
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 002_tier2_returns_and_runs completed successfully';
    RAISE NOTICE 'Verify with: SELECT data_tier, COUNT(*) FROM july_june_returns GROUP BY 1;';
    RAISE NOTICE 'Verify runs: SELECT computation_type, data_tier, COUNT(*) FROM computation_runs GROUP BY 1, 2;';
END $$;

