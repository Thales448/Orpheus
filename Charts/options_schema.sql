-- Options schema: single source of truth for tickers is public.tickers.
-- options.expirations and options.contracts reference public.tickers(id).
-- options.quotes is a Timescale hypertable (chunked by time, compressed).
--
-- Prerequisites:
--   CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
--   public.tickers must exist (id, ticker). No separate options.tickers table.
--
-- Ensure public.tickers exists (create if your project doesn't have it yet)
-- CREATE SCHEMA IF NOT EXISTS public;
-- CREATE TABLE IF NOT EXISTS public.tickers (
--     id   SERIAL PRIMARY KEY,
--     ticker TEXT NOT NULL UNIQUE
-- );

CREATE SCHEMA IF NOT EXISTS options;

-- Expiration dates per underlying (ticker_id = public.tickers.id)
CREATE TABLE IF NOT EXISTS options.expirations (
    ticker_id   INTEGER NOT NULL REFERENCES public.tickers(id) ON DELETE CASCADE,
    expiration  INTEGER NOT NULL,  -- YYYYMMDD
    PRIMARY KEY (ticker_id, expiration)
);

CREATE INDEX IF NOT EXISTS idx_options_expirations_ticker_id
    ON options.expirations (ticker_id);
CREATE INDEX IF NOT EXISTS idx_options_expirations_expiration
    ON options.expirations (expiration);

-- Option contract metadata (ticker_id = public.tickers.id)
CREATE TABLE IF NOT EXISTS options.contracts (
    id         SERIAL PRIMARY KEY,
    ticker_id  INTEGER NOT NULL REFERENCES public.tickers(id) ON DELETE CASCADE,
    expiration INTEGER NOT NULL,   -- YYYYMMDD
    strike     NUMERIC NOT NULL,
    side       TEXT NOT NULL CHECK (side IN ('call', 'put')),
    UNIQUE (ticker_id, expiration, strike, side)
);

CREATE INDEX IF NOT EXISTS idx_options_contracts_ticker_exp
    ON options.contracts (ticker_id, expiration);
CREATE INDEX IF NOT EXISTS idx_options_contracts_lookup
    ON options.contracts (ticker_id, expiration, strike, side);

-- NBBO quotes per contract (hypertable, chunked and compressed).
-- Greeks columns are nullable; ingest can populate them later.
CREATE TABLE IF NOT EXISTS options.quotes (
    time           TIMESTAMPTZ NOT NULL,
    contract_id    INTEGER NOT NULL REFERENCES options.contracts(id) ON DELETE CASCADE,
    bid            NUMERIC,
    bid_size       INTEGER,
    bid_exchange   SMALLINT,
    bid_condition  SMALLINT,
    ask            NUMERIC,
    ask_size       INTEGER,
    ask_exchange   SMALLINT,
    ask_condition  SMALLINT,
    -- Greeks (nullable; populated when greeks ingest is added)
    delta          NUMERIC,
    gamma          NUMERIC,
    theta          NUMERIC,
    vega           NUMERIC,
    rho            NUMERIC,
    implied_vol    NUMERIC,
    underlying_price    NUMERIC,
    underlying_timestamp TIMESTAMPTZ,
    d1             NUMERIC,
    d2             NUMERIC,
    dual_delta     NUMERIC,
    dual_gamma     NUMERIC,
    charm          NUMERIC,
    color          NUMERIC,
    speed          NUMERIC,
    ultima         NUMERIC,
    vanna          NUMERIC,
    vomma          NUMERIC,
    veta           NUMERIC,
    vera           NUMERIC,
    zomma          NUMERIC,
    epsilon        NUMERIC,
    lambda         NUMERIC,
    iv_error       NUMERIC,
    UNIQUE (time, contract_id)
);

-- Convert to hypertable (chunk by time; requires timescaledb extension)
-- Run: CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
SELECT create_hypertable(
    'options.quotes',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Enable compression: segment by contract_id for efficient per-contract queries
ALTER TABLE options.quotes SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'contract_id',
    timescaledb.compress_orderby = 'time DESC'
);

-- Compress chunks older than 7 days (tune as needed)
SELECT add_compression_policy(
    'options.quotes',
    compress_after => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Optional: retention or other policies
-- SELECT add_retention_policy('options.quotes', INTERVAL '2 years', if_not_exists => TRUE);
