-- Migration: add Greeks (and related) columns to options.quotes.
-- Safe to run on existing tables; skips columns that already exist.
-- Ingest script does not populate these yet; they are for future use.

DO $$
DECLARE
  col TEXT;
  cols TEXT[] := ARRAY[
    'delta', 'gamma', 'theta', 'vega', 'rho',
    'implied_vol', 'underlying_price', 'underlying_timestamp',
    'd1', 'd2',
    'dual_delta', 'dual_gamma',
    'charm', 'color', 'speed', 'ultima', 'vanna', 'vomma', 'veta', 'vera', 'zomma',
    'epsilon', 'lambda', 'iv_error'
  ];
  typ TEXT;
BEGIN
  FOREACH col IN ARRAY cols
  LOOP
    IF col = 'underlying_timestamp' THEN
      typ := 'TIMESTAMPTZ';
    ELSE
      typ := 'NUMERIC';
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'options' AND table_name = 'quotes' AND column_name = col
    ) THEN
      EXECUTE format('ALTER TABLE options.quotes ADD COLUMN %I %s', col, typ);
    END IF;
  END LOOP;
END $$;
