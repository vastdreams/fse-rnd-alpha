-- PATH: deploy/init.sql
-- PURPOSE: Initialize PostgreSQL database schema

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) UNIQUE NOT NULL,
    cik VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    country VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_companies_ticker ON companies(ticker);
CREATE INDEX IF NOT EXISTS ix_companies_cik ON companies(cik);

-- Company Year Core table
CREATE TABLE IF NOT EXISTS company_year_core (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    ticker VARCHAR(10) NOT NULL,
    cik VARCHAR(20) NOT NULL,
    fiscal_year INTEGER NOT NULL,
    filing_date DATE,
    sec_accession_id VARCHAR(50),
    sector VARCHAR(100),
    industry VARCHAR(100),
    country VARCHAR(50),
    report_path VARCHAR(500),
    report_hash VARCHAR(64),
    data_version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (company_id, fiscal_year)
);

CREATE INDEX IF NOT EXISTS ix_company_year_ticker ON company_year_core(ticker);
CREATE INDEX IF NOT EXISTS ix_company_year_fiscal_year ON company_year_core(fiscal_year);
CREATE INDEX IF NOT EXISTS ix_company_year_ticker_year ON company_year_core(ticker, fiscal_year);

-- Financials Core table
CREATE TABLE IF NOT EXISTS financials_core (
    id SERIAL PRIMARY KEY,
    company_year_id INTEGER UNIQUE NOT NULL REFERENCES company_year_core(id),
    revenue DOUBLE PRECISION,
    cost_of_revenue DOUBLE PRECISION,
    gross_profit DOUBLE PRECISION,
    rd_expense DOUBLE PRECISION,
    sga_expense DOUBLE PRECISION,
    operating_income DOUBLE PRECISION,
    ebit DOUBLE PRECISION,
    interest_expense DOUBLE PRECISION,
    pretax_income DOUBLE PRECISION,
    income_tax DOUBLE PRECISION,
    net_income DOUBLE PRECISION,
    eps_basic DOUBLE PRECISION,
    eps_diluted DOUBLE PRECISION,
    total_assets DOUBLE PRECISION,
    cash_and_equivalents DOUBLE PRECISION,
    short_term_investments DOUBLE PRECISION,
    accounts_receivable DOUBLE PRECISION,
    inventory DOUBLE PRECISION,
    ppe_net DOUBLE PRECISION,
    goodwill DOUBLE PRECISION,
    intangible_assets DOUBLE PRECISION,
    total_liabilities DOUBLE PRECISION,
    short_term_debt DOUBLE PRECISION,
    long_term_debt DOUBLE PRECISION,
    total_equity DOUBLE PRECISION,
    retained_earnings DOUBLE PRECISION,
    cash_from_operations DOUBLE PRECISION,
    cash_from_investing DOUBLE PRECISION,
    cash_from_financing DOUBLE PRECISION,
    capex DOUBLE PRECISION,
    depreciation_amortization DOUBLE PRECISION,
    dividends_paid DOUBLE PRECISION,
    share_repurchases DOUBLE PRECISION,
    source VARCHAR(50),
    quality_flag VARCHAR(20),
    currency VARCHAR(10) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Financials Ratios table
CREATE TABLE IF NOT EXISTS financials_ratios (
    id SERIAL PRIMARY KEY,
    company_year_id INTEGER UNIQUE NOT NULL REFERENCES company_year_core(id),
    gross_margin DOUBLE PRECISION,
    operating_margin DOUBLE PRECISION,
    net_margin DOUBLE PRECISION,
    roe DOUBLE PRECISION,
    roa DOUBLE PRECISION,
    roic DOUBLE PRECISION,
    rd_intensity DOUBLE PRECISION,
    rd_to_gross_profit DOUBLE PRECISION,
    rd_per_employee DOUBLE PRECISION,
    rd_growth_yoy DOUBLE PRECISION,
    debt_to_equity DOUBLE PRECISION,
    debt_to_assets DOUBLE PRECISION,
    interest_coverage DOUBLE PRECISION,
    current_ratio DOUBLE PRECISION,
    quick_ratio DOUBLE PRECISION,
    working_capital DOUBLE PRECISION,
    cfo_to_net_income DOUBLE PRECISION,
    fcf DOUBLE PRECISION,
    fcf_margin DOUBLE PRECISION,
    dividend_coverage DOUBLE PRECISION,
    cash_conversion DOUBLE PRECISION,
    revenue_growth_yoy DOUBLE PRECISION,
    eps_growth_yoy DOUBLE PRECISION,
    fcf_growth_yoy DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Text Factor R&D table
CREATE TABLE IF NOT EXISTS text_factor_rd (
    id SERIAL PRIMARY KEY,
    company_year_id INTEGER UNIQUE NOT NULL REFERENCES company_year_core(id),
    rd_mentions_count INTEGER,
    research_mentions_count INTEGER,
    development_mentions_count INTEGER,
    innovation_mentions_count INTEGER,
    rd_section_length_words INTEGER,
    rd_tone_score DOUBLE PRECISION,
    rd_sentiment_breakdown JSONB,
    rd_reporting_style VARCHAR(50),
    rd_sections_found JSONB,
    rd_primary_section VARCHAR(100),
    rd_focus_tags JSONB,
    rd_technology_areas JSONB,
    rd_geographic_mentions JSONB,
    rd_numbers_mentioned JSONB,
    rd_percentages_mentioned JSONB,
    rd_trends_mentioned JSONB,
    rd_key_paragraphs JSONB,
    rd_strategic_priorities JSONB,
    rd_competitive_mentions JSONB,
    extraction_version VARCHAR(20),
    extraction_timestamp TIMESTAMP,
    extraction_confidence DOUBLE PRECISION,
    verification_status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Annual Reports table
CREATE TABLE IF NOT EXISTS annual_reports (
    id SERIAL PRIMARY KEY,
    company_year_id INTEGER UNIQUE NOT NULL REFERENCES company_year_core(id),
    cik VARCHAR(20) NOT NULL,
    fiscal_year INTEGER NOT NULL,
    filing_date DATE,
    accession_id VARCHAR(50),
    form_type VARCHAR(20) DEFAULT '10-K',
    file_path VARCHAR(500),
    file_hash VARCHAR(64),
    file_size_bytes INTEGER,
    file_format VARCHAR(20),
    extraction_status VARCHAR(20) DEFAULT 'pending',
    document_count INTEGER,
    has_xbrl BOOLEAN,
    xbrl_url VARCHAR(500),
    sections_found JSONB,
    total_pages INTEGER,
    word_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Prices table
CREATE TABLE IF NOT EXISTS prices (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    adjusted_close DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (ticker, date)
);

CREATE INDEX IF NOT EXISTS ix_prices_ticker ON prices(ticker);
CREATE INDEX IF NOT EXISTS ix_prices_date ON prices(date);

-- Unified filings view
CREATE OR REPLACE VIEW unified_filings AS
SELECT
    cy.id AS company_year_id,
    c.id AS company_id,
    ar.id AS annual_report_id,
    c.ticker,
    c.name,
    c.cik,
    cy.fiscal_year,
    cy.filing_date,
    cy.sec_accession_id,
    cy.report_path,
    ar.file_format,
    ar.file_size_bytes,
    ar.extraction_status,
    ar.form_type,
    cy.created_at,
    cy.updated_at
FROM company_year_core cy
JOIN companies c ON cy.company_id = c.id
LEFT JOIN annual_reports ar ON ar.company_year_id = cy.id;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE OR REPLACE TRIGGER update_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_company_year_core_updated_at
    BEFORE UPDATE ON company_year_core
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_financials_core_updated_at
    BEFORE UPDATE ON financials_core
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_financials_ratios_updated_at
    BEFORE UPDATE ON financials_ratios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_text_factor_rd_updated_at
    BEFORE UPDATE ON text_factor_rd
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_annual_reports_updated_at
    BEFORE UPDATE ON annual_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (adjust as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

