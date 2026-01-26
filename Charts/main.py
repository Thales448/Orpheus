import sys
import logging
import os
import pandas as pd
import psycopg2
import psycopg2.extras
import hashlib
import pickle
from pathlib import Path
from datetime import datetime
from typing import Optional, Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from Charts.DatabaseConnection import DatabaseConnection
from Charts.DataCollector import DataCollector

# Init shared resources
db = DatabaseConnection()
data = DataCollector(db)


class SyntxDB():
    def __init__(self, cache_dir: str = "/home/r/Workspace/.syntxdb_cache", enable_cache: bool = True):
        self.conn = db
        self.datacollector = data

        # Cache settings
        self.enable_cache = enable_cache
        self.cache_dir = Path(cache_dir)
        if self.enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cache enabled at {self.cache_dir}")
        
        # Direct database connection for options
        self.db_conn = psycopg2.connect(
            host="192.168.1.92",
            port=5432,
            database="historical",
            user="postgres",
            password="password",
            cursor_factory=psycopg2.extras.RealDictCursor
        )

    def add_equity(self, symbol: str, resolution: str, start_time: Optional[str] = None, 
                   end_time: Optional[str] = None, use_cache: bool = True) -> pd.DataFrame:
        """
        Get stock/equity data with time aggregation
        
        Args:
            symbol: Stock symbol (e.g., "SPY", "AAPL")
            resolution: Time resolution - "1m", "5m", "15m", "30m", "1h", "1d" (default: "1d")
            start_time: Start date (YYYY-MM-DD format, optional)
            end_time: End date (YYYY-MM-DD format, optional)
            use_cache: Whether to use cache for this query (default: True)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Check cache first
            if use_cache:
                cache_key = self._get_cache_key(symbol, f"equity_{start_time}_{end_time}", resolution, None, None)
                cached_df = self._get_from_cache(cache_key)
                if cached_df is not None:
                    return cached_df
            
            # Map resolution to PostgreSQL interval
            resolution_map = {
                "1m": "1 minute",
                "5m": "5 minutes",
                "15m": "15 minutes",
                "30m": "30 minutes",
                "1h": "1 hour",
                "1d": "1 day"
            }
            
            if resolution not in resolution_map:
                logger.error(f"Invalid resolution: {resolution}. Valid options: {list(resolution_map.keys())}")
                return pd.DataFrame()
            
            interval = resolution_map[resolution]
            
            # Build time filter
            time_clause = ""
            params = [symbol]
            
            if start_time:
                time_clause += " AND c.time >= %s"
                params.append(start_time)
            
            if end_time:
                time_clause += " AND c.time <= %s"
                params.append(end_time + " 23:59:59")  # Include entire day
            
            # Query with time_bucket aggregation
            if resolution == "1d":
                # For daily, aggregate from minute data
                query = f"""
                    SELECT 
                        time_bucket('{interval}', c.time) AS time,
                        FIRST(c.open, c.time) AS open,
                        MAX(c.high) AS high,
                        MIN(c.low) AS low,
                        LAST(c.close, c.time) AS close,
                        SUM(c.volume) AS volume
                    FROM stocks.candles c
                    JOIN public.tickers t ON c.ticker_id = t.id
                    WHERE t.ticker = %s
                      {time_clause}
                    GROUP BY time_bucket('{interval}', c.time)
                    ORDER BY time
                """
            else:
                # For intraday, aggregate from minute data
                query = f"""
                    SELECT 
                        time_bucket('{interval}', c.time) AS time,
                        FIRST(c.open, c.time) AS open,
                        MAX(c.high) AS high,
                        MIN(c.low) AS low,
                        LAST(c.close, c.time) AS close,
                        SUM(c.volume) AS volume
                    FROM stocks.candles c
                    JOIN public.tickers t ON c.ticker_id = t.id
                    WHERE t.ticker = %s
                      {time_clause}
                    GROUP BY time_bucket('{interval}', c.time)
                    ORDER BY time
                """
            
            cursor = self.db_conn.cursor()
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            
            if not rows:
                logger.warning(f"No data found for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(rows)
            df['time'] = pd.to_datetime(df['time'])
            df.set_index('time', inplace=True)
            
            # Convert to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.info(f"Retrieved {len(df)} {resolution} candles for {symbol}")
            
            # Save to cache
            if use_cache:
                self._save_to_cache(cache_key, df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting equity data for {symbol}: {e}")
            return pd.DataFrame()

    def add_crypto(self, coin: str, resolution="daily"):
        data = self.conn.get_crypto_data(coin, resolution)
        return pd.DataFrame(data, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])

    def _get_cache_key(self, symbol, expiration, resolution, min_dte, max_dte):
        """Generate cache key from parameters"""
        key_str = f"{symbol}_{expiration}_{resolution}_{min_dte}_{max_dte}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key):
        """Get data from cache"""
        if not self.enable_cache:
            return None 
        
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    df = pickle.load(f)
                logger.info(f"Cache hit! Loaded from cache")
                return df
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
                return None
        return None
    
    def _save_to_cache(self, cache_key, df):
        """Save data to cache"""
        if not self.enable_cache or df.empty:
            return
        
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(df, f)
            logger.info(f"Saved to cache")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    def clear_cache(self):
        """Clear all cached data"""
        if self.enable_cache and self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            logger.info(f"Cache cleared")
    
    def add_chain(self, symbol: str, expiration: Optional[Union[int, str, tuple]] = None, 
                  resolution: str = "1m", min_dte: Optional[int] = None, max_dte: Optional[int] = None,
                  use_cache: bool = True) -> pd.DataFrame:
        """
        Get options quotes for a symbol with time aggregation
        
        Args:
            symbol: Stock symbol (e.g., "SPY")
            expiration: Optional. Can be:
                - Single expiration: 20250612 (int) or "2025-06-12" (str)
                - Range: (20250601, 20250630) for all expirations in June 2025
                - None: Get all available expirations
            resolution: Time resolution - "1m", "5m", "15m", "1h", "1d" (default: "1m")
            min_dte: Minimum days to expiration (only get quotes >= this many days before expiration)
            max_dte: Maximum days to expiration (only get quotes <= this many days before expiration)
            use_cache: Whether to use cache for this query (default: True)
            
        Returns:
            DataFrame with quotes aggregated to the specified resolution
        """
        try:
            # Check cache first
            if use_cache:
                cache_key = self._get_cache_key(symbol, expiration, resolution, min_dte, max_dte)
                cached_df = self._get_from_cache(cache_key)
                if cached_df is not None:
                    return cached_df
            
            # Handle expiration parameter
            expiration_clause = ""
            params = [symbol]
            
            if expiration is None:
                # Get all expirations
                expiration_clause = ""
                expiration_str = "all expirations"
            elif isinstance(expiration, tuple):
                # Range of expirations
                start_exp, end_exp = expiration
                if isinstance(start_exp, str):
                    start_exp = int(start_exp.replace("-", ""))
                if isinstance(end_exp, str):
                    end_exp = int(end_exp.replace("-", ""))
                
                # Ensure start <= end (auto-fix reversed ranges)
                if start_exp > end_exp:
                    start_exp, end_exp = end_exp, start_exp
                    logger.warning(f"Reversed expiration range to {start_exp}-{end_exp}")
                
                expiration_clause = "AND c.expiration BETWEEN %s AND %s"
                params.extend([start_exp, end_exp])
                expiration_str = f"expirations {start_exp}-{end_exp}"
            else:
                # Single expiration
                if isinstance(expiration, str):
                    expiration = int(expiration.replace("-", ""))
                expiration_clause = "AND c.expiration = %s"
                params.append(expiration)
                expiration_str = f"expiration {expiration}"
            
            # Map resolution to PostgreSQL interval
            resolution_map = {
                "1m": "1 minute",
                "5m": "5 minutes",
                "15m": "15 minutes",
                "30m": "30 minutes",
                "1h": "1 hour",
                "1d": "1 day"
            }
            
            if resolution not in resolution_map:
                logger.error(f"Invalid resolution: {resolution}. Valid options: {list(resolution_map.keys())}")
                return pd.DataFrame()
            
            interval = resolution_map[resolution]
            
            # Build DTE filter clause
            # DTE = days between quote time and expiration date
            # For historical: if expiration is 20250612, and quote is on 2025-06-10, DTE = 2 days
            dte_clause = ""
            if min_dte is not None or max_dte is not None:
                # Convert expiration YYYYMMDD to date, subtract quote time, get days
                if min_dte is not None and max_dte is not None:
                    dte_clause = f"""
                        AND (TO_DATE(c.expiration::text, 'YYYYMMDD') - q.time::date) BETWEEN {min_dte} AND {max_dte}
                    """
                elif min_dte is not None:
                    dte_clause = f"""
                        AND (TO_DATE(c.expiration::text, 'YYYYMMDD') - q.time::date) >= {min_dte}
                    """
                elif max_dte is not None:
                    dte_clause = f"""
                        AND (TO_DATE(c.expiration::text, 'YYYYMMDD') - q.time::date) <= {max_dte}
                    """
            
            # Query with time_bucket aggregation
            if resolution == "1m":
                # No aggregation needed for 1m
                query = f"""
                    SELECT 
                        q.time,
                        c.strike,
                        c.expiration,
                        c.side,
                        q.bid,
                        q.bid_size,
                        q.ask,
                        q.ask_size
                    FROM options.quotes q
                    JOIN options.contracts c ON q.contract_id = c.id
                    JOIN options.tickers t ON c.ticker_id = t.id
                    WHERE t.ticker = %s 
                      {expiration_clause}
                      {dte_clause}
                      AND NOT (q.bid = 0 AND q.ask = 0)
                    ORDER BY q.time, c.expiration, c.strike, c.side
                """
            else:
                # Use time_bucket for aggregation
                query = f"""
                    SELECT 
                        time_bucket('{interval}', q.time) AS time,
                        c.strike,
                        c.expiration,
                        c.side,
                        (ARRAY_AGG(q.bid ORDER BY q.time DESC))[1] AS bid,
                        (ARRAY_AGG(q.bid_size ORDER BY q.time DESC))[1] AS bid_size,
                        (ARRAY_AGG(q.ask ORDER BY q.time DESC))[1] AS ask,
                        (ARRAY_AGG(q.ask_size ORDER BY q.time DESC))[1] AS ask_size
                    FROM options.quotes q
                    JOIN options.contracts c ON q.contract_id = c.id
                    JOIN options.tickers t ON c.ticker_id = t.id
                    WHERE t.ticker = %s 
                      {expiration_clause}
                      {dte_clause}
                      AND NOT (q.bid = 0 AND q.ask = 0)
                    GROUP BY time_bucket('{interval}', q.time), c.strike, c.expiration, c.side
                    ORDER BY time, c.expiration, c.strike, c.side
                """
            
            cursor = self.db_conn.cursor()
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            
            if not rows:
                logger.warning(f"No data found for {symbol} {expiration_str}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(rows)
            df['time'] = pd.to_datetime(df['time'])
            
            logger.info(f"Retrieved {len(df)} {resolution} quotes for {symbol} {expiration_str}")
            
            # Save to cache
            if use_cache:
                self._save_to_cache(cache_key, df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting options chain: {e}")
            return pd.DataFrame()
    
    def get_expirations(self, symbol: str) -> list:
        """
        Get list of available expiration dates for a symbol
        
        Args:
            symbol: Stock symbol (e.g., "SPY")
            
        Returns:
            List of expiration dates (YYYYMMDD format), sorted newest first
        """
        try:
            query = """
                SELECT DISTINCT c.expiration
                FROM options.contracts c
                JOIN options.tickers t ON c.ticker_id = t.id
                WHERE t.ticker = %s
                ORDER BY c.expiration DESC
            """
            
            cursor = self.db_conn.cursor()
            cursor.execute(query, (symbol,))
            rows = cursor.fetchall()
            cursor.close()
            
            expirations = [row['expiration'] for row in rows]
            
            if expirations:
                logger.info(f"Found {len(expirations)} expirations for {symbol}")
            else:
                logger.warning(f"No expirations found for {symbol}")
            
            return expirations
            
        except Exception as e:
            logger.error(f"Error getting expirations: {e}")
            return []
    
    def get_data_availability(self, symbol: str) -> pd.DataFrame:
        """
        Get data availability summary for a symbol
        
        Args:
            symbol: Stock symbol (e.g., "SPY")
            
        Returns:
            DataFrame with expiration dates, date ranges, and quote counts
        """
        try:
            query = """
                SELECT 
                    c.expiration,
                    MIN(q.time::date) as first_date,
                    MAX(q.time::date) as last_date,
                    COUNT(*) as total_quotes,
                    COUNT(DISTINCT c.strike) as num_strikes,
                    COUNT(DISTINCT DATE(q.time)) as num_days
                FROM options.quotes q
                JOIN options.contracts c ON q.contract_id = c.id
                JOIN options.tickers t ON c.ticker_id = t.id
                WHERE t.ticker = %s
                  AND NOT (q.bid = 0 AND q.ask = 0)
                GROUP BY c.expiration
                ORDER BY c.expiration DESC
            """
            
            cursor = self.db_conn.cursor()
            cursor.execute(query, (symbol,))
            rows = cursor.fetchall()
            cursor.close()
            
            if not rows:
                logger.warning(f"No data found for {symbol}")
                return pd.DataFrame()
            
            df = pd.DataFrame(rows)
            df['expiration_date'] = pd.to_datetime(df['expiration'].astype(str), format='%Y%m%d')
            
            # Calculate DTE range (days between first quote and expiration)
            df['dte_range'] = (df['expiration_date'] - pd.to_datetime(df['first_date'])).dt.days
            
            logger.info(f"Found data for {len(df)} expirations for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error getting data availability: {e}")
            return pd.DataFrame()
    
    def close(self):
        """Close database connections"""
        if hasattr(self, 'db_conn') and self.db_conn:
            self.db_conn.close()
    
    
def print_help():
    print("""
Syntx Function Runner Help
          
Available functions:
  populate_options <ticker> <start_date> <end_date> <interval>
    - Populates options data for a specific ticker.

  populate_stocks <ticker>
    - Populates 245 days of minute-resolution stock data.

Options:
  -h, --help
    - Shows this help menu.

""")

def populate_options(ticker, start_date, end_date, interval):
    if not isinstance(ticker, str) or not ticker.isalpha():
        print("Error: 'ticker' must be a valid string (e.g. 'SPY').")
        return
    if not isinstance(interval, str):
        print("Error: 'interval' must be a valid string (e.g. '1m', '5m').")
        return

    try:
        f = DataCollector(db, config)
        f.populate_options(ticker, start_date, end_date, interval)
        print(f"Options collected for {ticker}")
    except Exception as e:
        print(f"Failed to collect options for {ticker}: {e}")

def populate_stocks(ticker):
    if not isinstance(ticker, str) or not ticker.isalpha():
        print("Error: 'ticker' must be a valid string (e.g. 'SPY').")
        return  

    try:
        data.get_stocks_minute(ticker)
        print(f"Collected 245 days of minute stock data for {ticker}")
    except Exception as e:
        print(f"Failed to collect stocks for {ticker}: {e}")


if __name__ == "__main__":
    exec_code = os.environ.get("EXEC_CODE")

    if not exec_code:
        print_help()
        sys.exit(0)

    parts = exec_code.strip().split()
    if len(parts) == 0:
        print_help()
        sys.exit(1)

    func_name = parts[0]

    if func_name in ["-h", "--help"]:
        print_help()
    elif func_name == "populate_options":
        if len(parts) != 5:
            print("Usage: populate_options <ticker> <start_date> <end_date> <interval>")
            sys.exit(1)
        populate_options(parts[1], parts[2], parts[3], parts[4])
    elif func_name == "populate_stocks":
        if len(parts) != 2:
            print("Usage: populate_stocks <ticker>")
            sys.exit(1)
        populate_stocks(parts[1])
    else:
        print(f"Unknown function: {func_name}")
        print_help()
        sys.exit(1)
