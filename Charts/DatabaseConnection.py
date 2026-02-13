import psycopg2
from psycopg2 import sql, extras
import datetime
import os
import logging
from typing import Union, Optional
from datetime import datetime
from datetime import timedelta
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd

load_dotenv()
logger = logging.getLogger(__name__)

class DatabaseConnection():
    """
    This Class provides all the functions and connections to the rquant DataBase
    """
    def __init__(self):
        self.logger = logger
        try:
            self.connection = psycopg2.connect(
                dbname=os.environ["DB_NAME"],
                user=os.environ["DB_USER"],
                password=os.environ["DB_PASSWORD"],
                host=os.environ["DB_HOST"],
                port=os.environ["DB_PORT"]
            )
        except Exception as e:
            print("Initial DB connection failed with env vars, loading .env...")
            load_dotenv(dotenv_path=Path(__file__).parent / '.env')
            try:
                self.connection = psycopg2.connect(
                    dbname=os.getenv("DB_NAME"),
                    user=os.getenv("DB_USER"),
                    password=os.getenv("DB_PASSWORD"),
                    host=os.getenv("DB_HOST"),
                    port=os.getenv("DB_PORT")
                )
            except Exception as e2:
                print("Failed to connect using .env as well:", e2)
                raise e2  # or handle as needed
    
    def close(self):
        try:
            if hasattr(self, 'connection') and self.connection:
                self.connection.close()
                self.logger.info("Database connection closed.")
        except psycopg2.Error as e:
            self.logger.error(f"Error closing the database connection {e}")
        except Exception as e:
            self.logger.error(f"Error closing the database connection {e}")
     
    def insert_option_ohlc(self, data, theta=False):
        if theta:
            insert_query = """
            INSERT INTO options.ohlc (
                time, contract_id,
                ms_of_day, open, high, low, close,
                volume, count, date
            ) VALUES %s
            ON CONFLICT (contract_id, time)
            DO NOTHING
        """
        else:
            insert_query = """
                INSERT INTO options.realtime (
                    underlying, symbol, description, strike, bid, ask, volume, option_type,
                    expiry_date, last_volume, delta, gamma, theta, vega, rho, mid_iv, time
                ) VALUES %s
                ON CONFLICT (symbol) 
                DO UPDATE SET
                    underlying = EXCLUDED.underlying,
                    description = EXCLUDED.description,
                    strike = EXCLUDED.strike,
                    bid = EXCLUDED.bid,
                    ask = EXCLUDED.ask,
                    volume = EXCLUDED.volume,
                    option_type = EXCLUDED.option_type,
                    expiry_date = EXCLUDED.expiry_date,
                    last_volume = EXCLUDED.last_volume,
                    delta = EXCLUDED.delta,
                    gamma = EXCLUDED.gamma,
                    theta = EXCLUDED.theta,
                    vega = EXCLUDED.vega,
                    rho = EXCLUDED.rho,
                    mid_iv = EXCLUDED.mid_iv,
                    time = EXCLUDED.time;
            """
        try:
            with self.connection.cursor() as cursor:
                extras.execute_values(cursor, insert_query, data)
                self.connection.commit()
                
                #self.logger.info("Data insert into options_minute_ohlc successful.")
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Error inserting option data: {e}")
            raise e

    def insert_option_quotes(self, quotes):
        """
        Inserts a batch of option quote tuples into options.quotes.
        Each quote is a tuple: (contract_id, time, bid, bid_size, bid_ex, bid_cond, ask, ask_size, ask_ex, ask_cond)
        """
        if not quotes:
            return

        insert_query = """
        INSERT INTO options.quotes (
            time, contract_id,
            bid, bid_size, bid_exchange, bid_condition,
            ask, ask_size, ask_exchange, ask_condition
        ) VALUES %s
        ON CONFLICT (time, contract_id) DO NOTHING
        """

        try:
            with self.connection.cursor() as cursor:
                extras.execute_values(cursor, insert_query, quotes, page_size=500)
                self.connection.commit()
                self.logger.info(f"✅ Inserted {len(quotes)} quote rows into options.quotes")
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"❌ Error inserting option quotes: {e}")

    def insert_expiration_dates(self, sid, expirations):
        insert_query = """
        INSERT INTO options.expirations (ticker_id, expiration)
        VALUES %s
        ON CONFLICT (ticker_id, expiration) DO NOTHING
        """
        try:
            # Create list of (sid, expiration_date) tuples
            data = [(sid, date) for date in expirations]

            with self.connection.cursor() as cursor:
                extras.execute_values(cursor, insert_query, data)
                self.connection.commit()
                self.logger.info(f"Inserted {len(data)} expiration dates for ticker ID {sid}")
        
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Error inserting expiration dates for ticker ID {sid}: {e}")
  
    def insert_stocks_quote(self, records):
        """
        Inserts a list of quote tuples into the stocks.quote table.
        Each tuple should have the form:
        (timestamp, ticker_id, bid, bid_size, bid_exchange, bid_condition,
         ask, ask_size, ask_exchange, ask_condition)
        Example:
            (datetime.datetime(2025, 1, 3, 9, 30), 29, 587.49, 4, 64, 0, 587.53, 5, 7, 0)
        """

        if not records:
            self.logger.warning("No SEC quote records to insert.")
            return

        insert_quote_query = """
            INSERT INTO stocks.quote (
                timestamp,
                ticker_id,
                bid,
                bid_size,
                bid_exchange,
                bid_condition,
                ask,
                ask_size,
                ask_exchange,
                ask_condition
            ) VALUES %s
            ON CONFLICT DO NOTHING;
        """

        try:
            from psycopg2.extras import execute_values

            with self.connection.cursor() as cursor:
                execute_values(cursor, insert_quote_query, records)
                self.connection.commit()
                self.logger.info(f"Inserted {len(records)} SEC quotes into stocks.quotes.")

        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Error inserting SEC quotes: {e}")
            raise e
        
    def insert_stock_candles(self, data):
        insert_query = """
            INSERT INTO stocks.candles (ticker_id, time, open, high, low, close, volume)
            VALUES %s
            ON CONFLICT (ticker_id, time) DO NOTHING;
        """
        try:
            with self.connection.cursor() as cursor:
                extras.execute_values(cursor, insert_query, data)
                self.connection.commit()
                self.logger.info(f"Inserted {len(data)} stock candle rows into stocks.candles")
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Error inserting stock candle data: {e}")
            raise e
 
    def insert_new_command(self, query_string):
        """
        Pass a SQL query to the db1 database and return the appropriate result.
        - For SELECT queries: Return the fetched result.
        - For INSERT/UPDATE/DELETE/ALTER: Return a confirmation message with the number of affected rows.
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query_string)
                self.connection.commit()
                
                # Check if the query is a SELECT statement
                if cursor.description:  # `cursor.description` is None for non-SELECT statements
                    result = cursor.fetchall()  # Fetch all results for SELECT queries
                    self.logger.info(f"Query executed successfully. Returning fetched data.")
                    return result
                else:
                    # Return a confirmation message for other SQL commands
                    rows_affected = cursor.rowcount
                    self.logger.info(f"Command executed successfully. {rows_affected} rows affected.")
                    return f"Command executed successfully. {rows_affected} rows affected."
        
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Error executing SQL command: {e}")
            raise e
        except Exception as ex:
            self.connection.rollback()
            self.logger.error(f"Unexpected error: {ex}")
            raise ex

    def get_or_create_root(self, root):
        with self.connection.cursor() as cursor:
            if type(root) == int:
                cursor.execute("""
                SELECT ticker FROM public.tickers
                WHERE id=%s
                """, (root,))
                result = cursor.fetchone()
                if result:
                    return result[0]

            cursor.execute("""
                SELECT id FROM public.tickers
                WHERE ticker=%s
           """, (root,))

            result = cursor.fetchone()
            if result:
                return result[0]
            
            cursor.execute("""
            INSERT INTO public.tickers (ticker)
            VALUES (%s)
            RETURNING id
            """, (root,))
            
            self.connection.commit()
            return cursor.fetchone()[0]

    def get_or_create_options_ticker(self, ticker: str):
        """
        Return public.tickers id for the given ticker (single source of truth).
        Same as get_or_create_root: ensures ticker exists in public.tickers and returns id.
        """
        return self.get_or_create_root(ticker)

    def get_or_create_contract(self, contract):
        with self.connection.cursor() as cursor:
            try:
                # If contract is an ID
                if isinstance(contract, int):
                    cursor.execute("SELECT id FROM options.contracts WHERE id = %s", (contract,))
                    result = cursor.fetchone()
                    if result:
                        return result[0]
                    self.logger.warning(f"Contract ID {contract} not found.")
                    return None

                root = contract['root']
                expiration = contract['expiration']  
                strike = contract['strike']
                side = contract['right']

                # Get ticker_id from public.tickers (single source of truth)
                cursor.execute("SELECT id FROM public.tickers WHERE ticker = %s", (contract['root'],))
                result = cursor.fetchone()
                if not result:
                    self.logger.error(f"Ticker '{contract['root']}' not found in public.tickers.")
                    return None
                ticker_id = result[0]

                # Try insert
                cursor.execute("""
                    INSERT INTO options.contracts (ticker_id, expiration, strike, side)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (ticker_id, expiration, strike, side) DO NOTHING
                    RETURNING id
                """, (ticker_id, expiration, strike, side))
                result = cursor.fetchone()
                if result:
                    self.connection.commit()
                    return result[0]
                
                # If already exists, select it
                cursor.execute("""
                    SELECT id FROM options.contracts
                    WHERE ticker_id = %s AND expiration = %s AND strike = %s AND side = %s
                """, (ticker_id, expiration, strike, side))
                result = cursor.fetchone()
                return result[0] if result else None

            except Exception as e:
                self.logger.error(f"❌ Failed to get or create contract: {e}")
                self.logger.error(f"🧾 Contract input: {contract}")
                return None
    
    def get_expirations(self, ticker: str, since_time: int = None) -> list:
        """
        Returns a list of expiration dates (as integers YYYYMMDD) for a given ticker,
        only if at least one contract exists for that expiration.
        If since_time is provided, only expirations >= since_time are returned.
        """
        try:
            with self.connection.cursor() as cursor:
                if since_time:
                    cursor.execute("""
                        SELECT DISTINCT e.expiration
                        FROM options.expirations e
                        JOIN public.tickers t ON t.id = e.ticker_id
                        WHERE t.ticker = %s
                        AND e.expiration >= %s
                        AND EXISTS (
                            SELECT 1 FROM options.contracts c
                            WHERE c.ticker_id = t.id AND c.expiration = e.expiration
                        )
                        ORDER BY e.expiration ASC;
                    """, (ticker, since_time))
                else:
                    cursor.execute("""
                        SELECT DISTINCT e.expiration
                        FROM options.expirations e
                        JOIN public.tickers t ON t.id = e.ticker_id
                        WHERE t.ticker = %s
                        AND EXISTS (
                            SELECT 1 FROM options.contracts c
                            WHERE c.ticker_id = t.id AND c.expiration = e.expiration
                        )
                        ORDER BY e.expiration ASC;
                    """, (ticker,))

                rows = cursor.fetchall()
                return [row[0] for row in rows]

        except Exception as e:
            self.logger.error(f"❌ Failed to get expirations for {ticker}: {e}")
            return []

    def get_stock_quotes(self, ticker: str, date: str = None, interval: str = "1s", start_time: str = None, end_time: str = None):
        """
        Retrieve stock quotes for a specified ticker and time range.

        Parameters:
            ticker (str): The ticker symbol or identifier.
            date (str, optional): Single day in 'YYYY-MM-DD' format (only if start_time/end_time not given).
            interval (str): Time interval for quotes. Supported values:
                - "1s": Raw quotes (default)
                - "1m", "5m", "10m", "15m", "30m": Minute intervals
                - "1h": Hourly intervals
                - "1d": Daily intervals
            start_time (str, optional): Start datetime 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'.
            end_time (str, optional): End datetime 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'.

        Returns:
            List[Tuple]: Each tuple structure exactly as in insert_stocks_quote():
                (timestamp, ticker_id, bid, bid_size, bid_exchange, bid_condition,
                 ask, ask_size, ask_exchange, ask_condition)
        """
        # Determine ticker_id (from public.tickers)
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT id FROM public.tickers WHERE ticker = %s", (ticker,))
                res = cursor.fetchone()
                if not res:
                    self.logger.error(f"Ticker '{ticker}' not found in database.")
                    return []
                ticker_id = res[0]
        except Exception as e:
            self.logger.error(f"Error fetching ticker_id for {ticker}: {e}")
            raise e

        time_condition = ""
        params = [ticker_id]
        if date and not (start_time or end_time):
            time_condition = "AND DATE(timestamp) = %s"
            params.append(date)
        elif start_time and end_time:
            time_condition = "AND timestamp BETWEEN %s AND %s"
            params.extend([start_time, end_time])
        elif start_time and not end_time:
            time_condition = "AND timestamp >= %s"
            params.append(start_time)
        elif end_time and not start_time:
            time_condition = "AND timestamp <= %s"
            params.append(end_time)
        # else: use all times for that ticker

        # Build query based on interval using TimescaleDB-optimized functions
        if interval == "1s":
            # Raw quotes - no aggregation
            select_fields = """
                timestamp, ticker_id, bid, bid_size, bid_exchange, bid_condition,
                ask, ask_size, ask_exchange, ask_condition
            """
            order_by = "ORDER BY timestamp ASC"
            query = f"""
                SELECT {select_fields}
                FROM stocks.quote
                WHERE ticker_id = %s {time_condition}
                {order_by};
            """
        elif interval.endswith("m"):
            # Minute intervals: 1m, 5m, 10m, 15m, 30m - using TimescaleDB time_bucket() and LAST()
            interval_minutes = int(interval.replace("m", ""))
            if interval_minutes not in [1, 5, 10, 15, 30]:
                self.logger.error(f"Unsupported minute interval: {interval}. Supported: 1m, 5m, 10m, 15m, 30m")
                return []
            
            # Use TimescaleDB time_bucket() and LAST() for optimal performance
            # Parameter order: [interval, ticker_id, ...time_condition_params, interval]
            interval_str = f"{interval_minutes} minutes"
            query_params = [interval_str, ticker_id]
            if date and not (start_time or end_time):
                query_params.append(date)
            elif start_time and end_time:
                query_params.extend([start_time, end_time])
            elif start_time and not end_time:
                query_params.append(start_time)
            elif end_time and not start_time:
                query_params.append(end_time)
            query_params.append(interval_str)  # Second interval for GROUP BY
            
            query = f"""
                SELECT 
                    time_bucket(%s, timestamp) AS timestamp,
                    ticker_id,
                    LAST(bid, timestamp) AS bid,
                    LAST(bid_size, timestamp) AS bid_size,
                    LAST(bid_exchange, timestamp) AS bid_exchange,
                    LAST(bid_condition, timestamp) AS bid_condition,
                    LAST(ask, timestamp) AS ask,
                    LAST(ask_size, timestamp) AS ask_size,
                    LAST(ask_exchange, timestamp) AS ask_exchange,
                    LAST(ask_condition, timestamp) AS ask_condition
                FROM stocks.quote
                WHERE ticker_id = %s {time_condition}
                GROUP BY time_bucket(%s, timestamp), ticker_id
                ORDER BY timestamp ASC;
            """
            params = query_params
        elif interval == "1h":
            # Hourly intervals - using TimescaleDB time_bucket() and LAST()
            query = f"""
                SELECT 
                    time_bucket('1 hour', timestamp) AS timestamp,
                    ticker_id,
                    LAST(bid, timestamp) AS bid,
                    LAST(bid_size, timestamp) AS bid_size,
                    LAST(bid_exchange, timestamp) AS bid_exchange,
                    LAST(bid_condition, timestamp) AS bid_condition,
                    LAST(ask, timestamp) AS ask,
                    LAST(ask_size, timestamp) AS ask_size,
                    LAST(ask_exchange, timestamp) AS ask_exchange,
                    LAST(ask_condition, timestamp) AS ask_condition
                FROM stocks.quote
                WHERE ticker_id = %s {time_condition}
                GROUP BY time_bucket('1 hour', timestamp), ticker_id
                ORDER BY timestamp ASC;
            """
        elif interval == "1d":
            # Daily intervals - using TimescaleDB time_bucket() and LAST()
            query = f"""
                SELECT 
                    time_bucket('1 day', timestamp) AS timestamp,
                    ticker_id,
                    LAST(bid, timestamp) AS bid,
                    LAST(bid_size, timestamp) AS bid_size,
                    LAST(bid_exchange, timestamp) AS bid_exchange,
                    LAST(bid_condition, timestamp) AS bid_condition,
                    LAST(ask, timestamp) AS ask,
                    LAST(ask_size, timestamp) AS ask_size,
                    LAST(ask_exchange, timestamp) AS ask_exchange,
                    LAST(ask_condition, timestamp) AS ask_condition
                FROM stocks.quote
                WHERE ticker_id = %s {time_condition}
                GROUP BY time_bucket('1 day', timestamp), ticker_id
                ORDER BY timestamp ASC;
            """
        else:
            self.logger.error(f"Unsupported interval: {interval}. Supported: 1s, 1m, 5m, 10m, 15m, 30m, 1h, 1d")
            return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                return rows
        except Exception as e:
            self.logger.error(f"Error retrieving stock quote data: {e}")
            raise e


    def get_option_symbol(self, option_symbol: str = None, start_time: str = None, end_time: str = None, resolution: str = "daily"):
        """
        Retrieve historical option data for a specific option contract symbol.

        Parameters:
            option_symbol (str): The specific option contract symbol 
            start_time (str, optional): "YYYY-MM-DD" format.
            end_time (str, optional): "YYYY-MM-DD" format. 
            resolution (str): Data resolution (currently not used).

        Returns:
            List: The rows retrieved from the database.
        """
        self.logger.info(f"Retrieving data for {option_symbol}")
        table = "options.historical"

        where_clauses = []
        if option_symbol:
            where_clauses.append(f"symbol = '{option_symbol}'")
        else:
            self.logger.error("Option Symbol must be passed")
            raise ValueError("Option Symbol must be passed")
        
        if start_time and not end_time:
            end_time = datetime.now().strftime("%Y-%m-%d")
        
        if start_time and end_time:
            where_clauses.append(f"time BETWEEN '{start_time}' AND '{end_time}'")
        
        where_clause = " AND ".join(where_clauses)
        
        query = f"""
            SELECT bid, ask, volume, last_volume, delta, gamma, theta, vega, rho, mid_iv, time
            FROM {table}
            WHERE {where_clause}
            ORDER BY time ASC
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                self.logger.info(f"Retrieved {len(rows)} rows from {table} for {option_symbol}.")
                return rows
        except Exception as e:
            self.logger.error(f"Error retrieving option data: {e}")
            raise e

    def get_option_chain(self, ticker, expiration, start_time=None, end_time=None, interval=None, side=None):
        try:
            with self.connection.cursor() as cursor:
                # Step 1: Get ticker_id
                cursor.execute("SELECT id FROM public.tickers WHERE ticker = %s", (ticker,))
                result = cursor.fetchone()
                if not result:
                    self.logger.error(f"❌ Ticker '{ticker}' not found.")
                    return pd.DataFrame()
                ticker_id = result[0]

                # Step 2: Handle expiration
                all_expirations = False
                if expiration == "all":
                    all_expirations = True
                    if not start_time or not end_time:
                        raise ValueError("start_time and end_time are required when expiration='all'")
                    if isinstance(start_time, str):
                        start_time = datetime.strptime(start_time, "%Y-%m-%d")
                    if isinstance(end_time, str):
                        end_time = datetime.strptime(end_time, "%Y-%m-%d")
                    if (end_time - start_time).days > 2 and interval == 'm1':
                        raise ValueError("Date range cannot exceed 2 days when expiration='all'")
                else:
                    if isinstance(expiration, str):
                        expiration_int = int(datetime.strptime(expiration, "%Y-%m-%d").strftime("%Y%m%d"))
                    elif isinstance(expiration, datetime):
                        expiration_int = int(expiration.strftime("%Y%m%d"))
                    elif isinstance(expiration, int):
                        expiration_int = expiration
                    else:
                        raise ValueError("Invalid expiration format")

                # Step 3: Interval logic
                use_bucket = bool(interval)
                interval_sql = None
                if interval:
                    if interval.startswith("m"):
                        interval_sql = f"{int(interval[1:])} minutes"
                    elif interval.startswith("h"):
                        interval_sql = f"{int(interval[1:])} hours"
                    elif interval == "daily":
                        interval_sql = "1 day"
                    else:
                        raise ValueError(f"Unsupported interval: {interval}")

                # Step 4: Build SQL parts
                select_time = "time_bucket(%s, q.time) AS time" if use_bucket else "q.time AS time"
                group_by = "GROUP BY time_bucket(%s, q.time), c.strike, c.expiration, c.side" if use_bucket else ""
                side_clause = "AND c.side = %s" if side else ""
                time_clause = "AND q.time BETWEEN %s AND %s" if start_time and end_time else ""
                expiration_clause = "" if all_expirations else "AND c.expiration = %s"

                # Step 5: Final query
                query = f"""
                    SELECT {select_time},
                        c.strike, c.expiration, c.side,
                        FIRST(q.bid, q.time) AS bid,
                        FIRST(q.bid_size, q.time) AS bid_size,
                        FIRST(q.bid_exchange, q.time) AS bid_exchange,
                        FIRST(q.bid_condition, q.time) AS bid_condition,
                        FIRST(q.ask, q.time) AS ask,
                        FIRST(q.ask_size, q.time) AS ask_size,
                        FIRST(q.ask_exchange, q.time) AS ask_exchange,
                        FIRST(q.ask_condition, q.time) AS ask_condition
                    FROM options.quotes q
                    JOIN options.contracts c ON q.contract_id = c.id
                    WHERE c.ticker_id = %s
                    {expiration_clause}
                    {side_clause}
                    {time_clause}
                    {group_by}
                    ORDER BY time, c.strike;
                """

                # Step 6: Parameter handling
                params = []
                if use_bucket:
                    params.append(interval_sql)
                params.append(ticker_id)
                if not all_expirations:
                    params.append(expiration_int)
                if side:
                    params.append(side)
                if start_time and end_time:
                    params += [start_time, end_time]
                if use_bucket:
                    params.append(interval_sql)

                # Step 7: Execute and format result
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                columns = [
                    'time', 'strike', 'expiration', 'side',
                    'bid', 'bid_size', 'bid_exchange', 'bid_condition',
                    'ask', 'ask_size', 'ask_exchange', 'ask_condition'
                ]
                df = pd.DataFrame(rows, columns=columns)
                df['expiration'] = df['expiration'].apply(lambda x: datetime.strptime(str(x), "%Y%m%d").date())
                df.set_index(['time', 'strike', 'expiration', 'side'], inplace=True)
                df.sort_index(inplace=True)
                self.logger.info(f"✅ Retrieved {len(df)} quotes for {ticker} expiration {expiration}")
                return df

        except Exception as e:
            self.logger.error(f"❌ Error fetching option chain: {e}")
            return pd.DataFrame()
