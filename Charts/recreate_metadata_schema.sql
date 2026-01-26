-- Recreate metadata schema and quote_dates_summary table
-- Based on ingest-hisotrical-stock.py usage

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS metadata;

-- Create the quote_dates_summary table
CREATE TABLE IF NOT EXISTS metadata.quote_dates_summary (
    ticker_id INTEGER NOT NULL,
    date DATE NOT NULL,
    record_count INTEGER NOT NULL,
    PRIMARY KEY (ticker_id, date)
);

-- Add index for faster lookups (optional but recommended)
CREATE INDEX IF NOT EXISTS idx_quote_dates_summary_ticker_date 
    ON metadata.quote_dates_summary(ticker_id, date);

CREATE INDEX IF NOT EXISTS idx_quote_dates_summary_date 
    ON metadata.quote_dates_summary(date);

-- Add comment for documentation
COMMENT ON TABLE metadata.quote_dates_summary IS 
    'Summary of quote data availability by ticker and date. Tracks record counts for fast lookups.';

COMMENT ON COLUMN metadata.quote_dates_summary.ticker_id IS 
    'Foreign key reference to ticker ID (from main database)';

COMMENT ON COLUMN metadata.quote_dates_summary.date IS 
    'Date of the quote data (YYYY-MM-DD format)';

COMMENT ON COLUMN metadata.quote_dates_summary.record_count IS 
    'Number of quote records available for this ticker/date combination';
