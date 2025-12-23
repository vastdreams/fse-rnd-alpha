-- Migration: 001_add_result_versioning.sql
-- Purpose: Add versioning fields to rolling_window_results, anova_results, factor_premiums
-- Date: December 2025
-- Author: Publication Upgrade
--
-- This migration adds:
-- 1. return_convention: 'july_june' or 'calendar'
-- 2. data_tier: 'tier1' (FMP) or 'tier2' (CRSP/Compustat)
-- 3. computation_run_id: UUID for reproducibility
-- 4. Updated unique constraints to include return_convention

-- ============================================================================
-- ROLLING WINDOW RESULTS
-- ============================================================================

-- Add new columns if they don't exist
ALTER TABLE rolling_window_results 
ADD COLUMN IF NOT EXISTS return_convention VARCHAR(20) DEFAULT 'july_june';

ALTER TABLE rolling_window_results 
ADD COLUMN IF NOT EXISTS data_tier VARCHAR(10) DEFAULT 'tier1';

ALTER TABLE rolling_window_results 
ADD COLUMN IF NOT EXISTS computation_run_id VARCHAR(36);

-- Update existing records to have explicit values
UPDATE rolling_window_results 
SET return_convention = 'july_june', data_tier = 'tier1' 
WHERE return_convention IS NULL OR data_tier IS NULL;

-- Drop old unique constraint and add new one
-- Note: This may fail if constraint doesn't exist - that's OK
ALTER TABLE rolling_window_results 
DROP CONSTRAINT IF EXISTS uq_window_quintile;

ALTER TABLE rolling_window_results 
ADD CONSTRAINT uq_window_quintile_convention 
UNIQUE (window_type, start_year, end_year, quintile, return_convention);

-- Add indexes
CREATE INDEX IF NOT EXISTS ix_rolling_window_convention 
ON rolling_window_results (return_convention);

-- ============================================================================
-- ANOVA RESULTS
-- ============================================================================

ALTER TABLE anova_results 
ADD COLUMN IF NOT EXISTS return_convention VARCHAR(20) DEFAULT 'july_june';

ALTER TABLE anova_results 
ADD COLUMN IF NOT EXISTS data_tier VARCHAR(10) DEFAULT 'tier1';

UPDATE anova_results 
SET return_convention = 'july_june', data_tier = 'tier1' 
WHERE return_convention IS NULL OR data_tier IS NULL;

-- Drop old unique constraint and add new one
ALTER TABLE anova_results 
DROP CONSTRAINT IF EXISTS uq_anova_period;

ALTER TABLE anova_results 
ADD CONSTRAINT uq_anova_period_convention 
UNIQUE (window_type, period, test_type, return_convention);

-- ============================================================================
-- FACTOR PREMIUMS
-- ============================================================================

ALTER TABLE factor_premiums 
ADD COLUMN IF NOT EXISTS return_convention VARCHAR(20) DEFAULT 'july_june';

ALTER TABLE factor_premiums 
ADD COLUMN IF NOT EXISTS data_tier VARCHAR(10) DEFAULT 'tier1';

UPDATE factor_premiums 
SET return_convention = 'july_june', data_tier = 'tier1' 
WHERE return_convention IS NULL OR data_tier IS NULL;

-- Drop old unique constraint and add new one
ALTER TABLE factor_premiums 
DROP CONSTRAINT IF EXISTS uq_factor_year;

ALTER TABLE factor_premiums 
ADD CONSTRAINT uq_factor_year_convention 
UNIQUE (year, return_convention);

-- ============================================================================
-- TIER 2 STUB TABLES (CRSP/Compustat)
-- ============================================================================

-- CRSP Monthly Stock Data
CREATE TABLE IF NOT EXISTS crsp_monthly_stock (
    id SERIAL PRIMARY KEY,
    permno INTEGER NOT NULL,
    date DATE NOT NULL,
    ret NUMERIC,           -- Monthly return
    dlret NUMERIC,         -- Delisting return
    prc NUMERIC,           -- Price (neg = bid/ask avg)
    shrout INTEGER,        -- Shares outstanding (000s)
    cfacpr NUMERIC,        -- Cumulative price adjustment
    cfacshr NUMERIC,       -- Cumulative share adjustment
    ticker VARCHAR(20),
    exchcd INTEGER,        -- Exchange code
    shrcd INTEGER,         -- Share code
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (permno, date)
);

CREATE INDEX IF NOT EXISTS ix_crsp_date ON crsp_monthly_stock (date);
CREATE INDEX IF NOT EXISTS ix_crsp_permno ON crsp_monthly_stock (permno);

-- CRSP-Compustat Link Table
CREATE TABLE IF NOT EXISTS crsp_compustat_link (
    id SERIAL PRIMARY KEY,
    permno INTEGER NOT NULL,
    gvkey VARCHAR(10) NOT NULL,
    linkdt DATE,           -- Link start date
    linkenddt DATE,        -- Link end date
    linktype VARCHAR(5),   -- LU, LC, LS, etc.
    linkprim VARCHAR(1),   -- P, C, J
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_ccm_permno ON crsp_compustat_link (permno);
CREATE INDEX IF NOT EXISTS ix_ccm_gvkey ON crsp_compustat_link (gvkey);

-- Compustat Annual Fundamentals
CREATE TABLE IF NOT EXISTS compustat_annual (
    id SERIAL PRIMARY KEY,
    gvkey VARCHAR(10) NOT NULL,
    datadate DATE NOT NULL,
    fyear INTEGER NOT NULL,
    xrd NUMERIC,           -- R&D Expense
    revt NUMERIC,          -- Revenue
    at NUMERIC,            -- Total Assets
    ceq NUMERIC,           -- Common Equity
    csho NUMERIC,          -- Shares Outstanding
    prcc_f NUMERIC,        -- Fiscal year-end price
    ni NUMERIC,            -- Net Income
    oibdp NUMERIC,         -- Operating Income
    sale NUMERIC,          -- Sales
    sic VARCHAR(4),        -- SIC code
    naics VARCHAR(6),      -- NAICS code
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (gvkey, datadate)
);

CREATE INDEX IF NOT EXISTS ix_compustat_fyear ON compustat_annual (fyear);
CREATE INDEX IF NOT EXISTS ix_compustat_gvkey ON compustat_annual (gvkey);

-- CRSP S&P 500 Historical Constituents
CREATE TABLE IF NOT EXISTS crsp_sp500_constituents (
    id SERIAL PRIMARY KEY,
    permno INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,         -- NULL = still member
    ticker VARCHAR(20),
    comnam VARCHAR(255),   -- Company name
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_crsp_sp500_dates ON crsp_sp500_constituents (start_date, end_date);
CREATE INDEX IF NOT EXISTS ix_crsp_sp500_permno ON crsp_sp500_constituents (permno);

-- ============================================================================
-- VALIDATION
-- ============================================================================

-- Verify columns were added
DO $$
BEGIN
    RAISE NOTICE 'Migration 001_add_result_versioning completed successfully';
    RAISE NOTICE 'Verify with: SELECT return_convention, data_tier, COUNT(*) FROM rolling_window_results GROUP BY 1, 2;';
END $$;

