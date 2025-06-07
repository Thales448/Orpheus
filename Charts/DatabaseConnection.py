
import psycopg2
from psycopg2 import sql, extras
import datetime
import os
import logging
from typing import Union, Optional
import datetime
from datetime import timedelta
from dotenv import load_dotenv
from pathlib import Path

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
            if self.cursor:
                self.cursor.close()
                self.logger.info('Database cursor closed.')
            if self.connection:
                self.connection.close()
                self.logger.info("Database connection closed.")
        except psycopg2.Error as e:
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
        ON CONFLICT DO NOTHING
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
  
    def insert_stocks_quotes(self, records):
        """
        Inserts a list of NBBO quote records into the stocks.nbbo_quotes table.
        Assumes the records are dictionaries with fields:
        ['symbol', 'timestamp', 'bid_size', 'bid_exchange', 'bid', 'bid_condition',
        'ask_size', 'ask_exchange', 'ask', 'ask_condition', 'date']
        """

        if not records:
            self.logger.warning("No NBBO quote records to insert.")
            return

        insert_ticker_query = """
            INSERT INTO stocks.tickers (symbol)
            VALUES (%s)
            ON CONFLICT (symbol) DO NOTHING;
        """

        insert_quote_query = """
            INSERT INTO stocks.nbbo_quotes (
                time, symbol, bid_size, bid_exchange, bid, bid_condition,
                ask_size, ask_exchange, ask, ask_condition, date
            ) VALUES %s
            ON CONFLICT DO NOTHING;
        """

        try:
            with self.connection.cursor() as cursor:
                # Ensure all ticker symbols are in the tickers table
                symbols = set(record['symbol'] for record in records)
                for symbol in symbols:
                    cursor.execute(insert_ticker_query, (symbol,))
                
                # Format data for bulk insert
                values = [
                    (
                        record['timestamp'],
                        record['symbol'],
                        record['bid_size'],
                        record['bid_exchange'],
                        record['bid'],
                        record['bid_condition'],
                        record['ask_size'],
                        record['ask_exchange'],
                        record['ask'],
                        record['ask_condition'],
                        record['date']
                    )
                    for record in records
                ]

                from psycopg2.extras import execute_values
                execute_values(cursor, insert_quote_query, values)
                self.connection.commit()
                self.logger.info(f"Inserted {len(values)} NBBO quotes into stocks.nbbo_quotes.")

        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Error inserting NBBO quotes: {e}")
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

    def insert_crypto(self, coin = str, data = list):
        """
        inserts crypto data for coin passed takes input as tuple of the form:
        (ts,open, high, low, close, volume)
        """
        insert_query = f"""
            INSERT INTO crypto.{coin} (ts, open_price, high_price, low_price, close_price, volume)
            VALUES %s;
        """
        try:
            with self.connection.cursor() as cursor:
                extras.execute_values(cursor, insert_query, data)
                self.connection.commit()
                self.logger.info(f"Data insert into crypto.{coin} successful.")
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Error inserting crypto.{coin} data: {e}")
            raise e
    
    def insert_crytpo_csv(self, csv_path, coin: str):
        
        with open("/workspace/btcusd_1-min_data.csv", "r") as f:
            csv_reader = csv.reader(f)

        next(csv_reader, None)

        rows_as_tuples = []
        for row in csv_reader:
            if not row[0] or not row[1] or not row[2] or not row[3] or not row[4] or not row[5]:
                continue
            # row[0] => timestamp, row[1] => open, row[2] => high, etc.
            ts      = datetime.datetime.fromtimestamp(int(float(row[0])))
            o_price = float(row[1])
            h_price = float(row[2])
            l_price = float(row[3])
            c_price = float(row[4])
            vol     = float(row[5])
            
            rows_as_tuples.append((ts, open, h_price, l_price, c_price, vol))
        conn.insert_crypto(coin=coin, data=csv_list_of_tuples)
    
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

    def copy_csv(self, table: str, csv_path: str):
        """
        Efficiently loads a CSV file into a PostgreSQL/TimescaleDB hypertable.
        Assumes CSV has header and values matching table columns exactly.
        """
        try:
            with self.connection.cursor() as cursor:
                with open(csv_path, 'r') as f:
                    # Skip header
                    next(f)
                    cursor.copy_expert(
                        sql.SQL("COPY {} FROM STDIN WITH CSV").format(sql.Identifier(*table.split('.'))),
                        f
                    )
                self.connection.commit()
                self.logger.info(f"Copied data from {csv_path} into {table}")
        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Failed to copy CSV into {table}: {e}")
            raise

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

                # Get ticker_id
                cursor.execute("SELECT id FROM options.tickers WHERE ticker = %s", (contract['root'],))
                result = cursor.fetchone()
                if not result:
                    self.logger.error(f"Ticker '{contract['root']}' not found.")
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
        Returns a list of expiration dates (as integers YYYYMMDD) for a given ticker.
        If since_time is provided, only expirations >= since_time are returned.
        """
        try:
            with self.connection.cursor() as cursor:
                if since_time:
                    cursor.execute("""
                        SELECT e.expiration
                        FROM options.expirations e
                        JOIN options.tickers t ON t.id = e.ticker_id
                        WHERE t.ticker = %s AND e.expiration >= %s
                        ORDER BY e.expiration ASC;
                    """, (ticker, since_time))
                else:
                    cursor.execute("""
                        SELECT e.expiration
                        FROM options.expirations e
                        JOIN options.tickers t ON t.id = e.ticker_id
                        WHERE t.ticker = %s
                        ORDER BY e.expiration ASC;
                    """, (ticker,))
                
                rows = cursor.fetchall()
                return [row[0] for row in rows]

        except Exception as e:
            self.logger.error(f"❌ Failed to get expirations for {ticker}: {e}")
            return []

    def get_stock_data(self, ticker: str, resolution: str = "daily", start_time: str = None, end_time: str = None):
            """
            Retrieve stock OHLCV data for a specified ticker and time resolution.
            - Intraday resolutions (minute, 5m, 10m, 15m, 30m, hourly) are from stocks.minute.
            - Daily, weekly, and monthly data are from stocks.daily.
            """
            
            # Set default end_time if only start_time is defined
            if start_time and not end_time:
                end_time = datetime.datetime.now().strftime("%Y-%m-%d")  # Get today's date in the "YYYY-MM-DD" format
            
            # Start building the SQL query
            ticker_id = self.get_or_create_root(ticker)
            where_clause = f"WHERE ticker_id = ticker_id"
            
            # Add date filters if start_time or end_time are provided
            if start_time:
                where_clause += f" AND time >= '{start_time}'"
            if end_time:
                where_clause += f" AND time <= '{end_time}'"

            if resolution == "minute":
                query = f"""
                    SELECT time, open, high, low, close, volume
                    FROM stocks.candles
                    {where_clause}
                    ORDER BY time ASC;
                """
                
            elif resolution in ["5m", "10m", "15m", "30m"]:
                interval = resolution.replace("m", "")
                query = f"""
                    WITH bars AS (
                        SELECT DISTINCT ON (
                            date_trunc('minute', time) - ((EXTRACT(MINUTE FROM time)::int %% {interval}) * INTERVAL '1 minute')
                        )
                        date_trunc('minute', time) - ((EXTRACT(MINUTE FROM time)::int %% {interval}) * INTERVAL '1 minute') AS bar_time,
                        open, high, low, close, volume
                        FROM stocks.candles
                        {where_clause}
                        ORDER BY date_trunc('minute', time) - ((EXTRACT(MINUTE FROM time)::int %% {interval}) * INTERVAL '1 minute'), time
                    )
                    SELECT * FROM bars
                    ORDER BY bar_time;
                """
                
            elif resolution == "hourly":
                query = f"""
                    WITH hourly_bars AS (
                        SELECT DISTINCT ON (date_trunc('hour', time))
                            date_trunc('hour', time) AS hour_time,
                            open, high, low, close, volume
                        FROM stocks.candles
                        {where_clause}
                        ORDER BY date_trunc('hour', time), time
                    )
                    SELECT * FROM hourly_bars
                    ORDER BY hour_time;
                """
                
            elif resolution == "daily":
                query = f"""
                    SELECT time, open, high, low, close, volume
                    FROM stocks.candles
                    {where_clause}
                    ORDER BY time ASC;
                """
                
            elif resolution == "weekly":
                query = f"""
                    WITH weekly_bars AS (
                        SELECT DISTINCT ON (date_trunc('week', time))
                            date_trunc('week', time) AS week_time,
                            open, high, low, close, volume
                        FROM stocks.candles
                        {where_clause}
                        ORDER BY date_trunc('week', time), time
                    )
                    SELECT * FROM weekly_bars
                    ORDER BY week_time;
                """
                
            elif resolution == "monthly":
                query = f"""
                    WITH monthly_bars AS (
                        SELECT DISTINCT ON (date_trunc('month', time))
                            date_trunc('month', time) AS month_time,
                            open, high, low, close, volume
                        FROM stocks.candles
                        {where_clause}
                        ORDER BY date_trunc('month', time), time
                    )
                    SELECT * FROM monthly_bars
                    ORDER BY month_time;
                """
                
            else:
                self.logger.error(f"Invalid resolution: {resolution}")
                return []

            try:
                with self.connection.cursor() as cursor:
                    cursor.execute(query, (ticker,))
                    rows = cursor.fetchall()
                    if len(rows) == 0:
                        self.logger.error(f"No data found for {ticker}  at {resolution} ticks")
                        return []
                    # Augment the log message with the start_time, end_time, and resolution.
                    self.logger.info(f"Retrieved {len(rows)} rows of {ticker} from {start_time} to {end_time} at {resolution} candle sticks")
                    return rows
            except psycopg2.Error as e:
                self.logger.error(f"Error retrieving stock data: {e}")
                raise e
    
    def get_crypto_data(self, coin: str, resolution: str = "daily"):
        """
        Retrieve crypto OHLCV data for a specified coin and time resolution
        from a single table: crypto.{coin}.

        The table crypto.{coin} is assumed to contain minute-level data.
        We aggregate it for hourly, daily, weekly, monthly using date_trunc().
        """

        if resolution == "minute":
            # Pull raw minute data from crypto.{coin}
            self.logger.info(f"Retrieving MINUTE data for coin: {coin}")
            query = f"""
                SELECT ts, open, high, low, close, volume
                FROM crypto.{coin}
                ORDER BY ts ASC;
            """
        
        elif resolution == "5m":
            self.logger.info(f"Retrieving 5-MINUTE data for coin: {coin}")
            query = f"""
                WITH bars AS (
                    SELECT DISTINCT ON (
                        date_trunc('minute', ts)
                        - ((EXTRACT(MINUTE FROM ts)::int %% 5) * INTERVAL '1 minute')
                    )
                    --  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                    --  This entire expression must match what appears in ORDER BY below

                        date_trunc('minute', ts)
                        - ((EXTRACT(MINUTE FROM ts)::int %% 5) * INTERVAL '1 minute')
                        AS bar_time,
                        open,
                        high,
                        low,
                        close,
                        volume
                    FROM crypto.{coin}
                    ORDER BY
                        -- First sort key must be the same expression used in DISTINCT ON
                        date_trunc('minute', ts)
                        - ((EXTRACT(MINUTE FROM ts)::int %% 5) * INTERVAL '1 minute'),
                        ts
                )
                SELECT *
                FROM bars
                ORDER BY bar_time;
                """

        elif resolution == "10m":
            self.logger.info(f"Retrieving 10-MINUTE data for coin: {coin}")
            query = f"""
                WITH bars AS (
                    SELECT DISTINCT ON (
                        date_trunc('minute', ts)
                        - ((EXTRACT(MINUTE FROM ts)::int %% 10) * INTERVAL '1 minute')
                    )
                    date_trunc('minute', ts)
                    - ((EXTRACT(MINUTE FROM ts)::int %% 10) * INTERVAL '1 minute') AS bar_time,
                    open,
                    high,
                    low,
                    close,
                    volume
                    FROM crypto.{coin}
                    ORDER BY
                        date_trunc('minute', ts)
                        - ((EXTRACT(MINUTE FROM ts)::int %% 10) * INTERVAL '1 minute'),
                        ts
                )
                SELECT *
                FROM bars
                ORDER BY bar_time;
            """

        elif resolution == "15m":
            self.logger.info(f"Retrieving 15-MINUTE data for coin: {coin}")
            query = f"""
                WITH bars AS (
                    SELECT DISTINCT ON (
                        date_trunc('minute', ts)
                        - ((EXTRACT(MINUTE FROM ts)::int %% 15) * INTERVAL '1 minute')
                    )
                    date_trunc('minute', ts)
                    - ((EXTRACT(MINUTE FROM ts)::int %% 15) * INTERVAL '1 minute') AS bar_time,
                    open,
                    high,
                    low,
                    close,
                    volume
                    FROM crypto.{coin}
                    ORDER BY
                        date_trunc('minute', ts)
                        - ((EXTRACT(MINUTE FROM ts)::int %% 15) * INTERVAL '1 minute'),
                        ts
                )
                SELECT *
                FROM bars
                ORDER BY bar_time;
            """

        elif resolution == "30m":
            self.logger.info(f"Retrieving 30-MINUTE data for coin: {coin}")
            query = f"""
                WITH bars AS (
                    SELECT DISTINCT ON (
                        date_trunc('minute', ts)
                        - ((EXTRACT(MINUTE FROM ts)::int %% 30) * INTERVAL '1 minute')
                    )
                    date_trunc('minute', ts)
                    - ((EXTRACT(MINUTE FROM ts)::int %% 30) * INTERVAL '1 minute') AS bar_time,
                    open,
                    high,
                    low,
                    close,
                    volume
                    FROM crypto.{coin}
                    ORDER BY
                        date_trunc('minute', ts)
                        - ((EXTRACT(MINUTE FROM ts)::int %% 30) * INTERVAL '1 minute'),
                        ts
                )
                SELECT *
                FROM bars
                ORDER BY bar_time;
            """

        elif resolution == "hourly":
            self.logger.info(f"Retrieving HOURLY data for coin: {coin}")
            query = f"""
                WITH hourly_bars AS (
                    SELECT DISTINCT ON (date_trunc('hour', ts))
                        date_trunc('hour', ts) AS hour_time,
                        open,
                        high,
                        low,
                        close,
                        volume
                    FROM crypto.{coin}
                    ORDER BY date_trunc('hour', ts), ts ASC
                )
                SELECT *
                FROM hourly_bars
                ORDER BY hour_time;
            """

        elif resolution == "daily":
            self.logger.info(f"Retrieving DAILY data for coin: {coin}")
            query = f"""
                WITH daily_bars AS (
                    SELECT DISTINCT ON (date_trunc('day', ts))
                        date_trunc('day', ts) AS day_time,
                        open,
                        high,
                        low,
                        close,
                        volume
                    FROM crypto.{coin}
                    ORDER BY date_trunc('day', ts), ts ASC
                )
                SELECT *
                FROM daily_bars
                ORDER BY day_time;
            """

        elif resolution == "weekly":
            self.logger.info(f"Retrieving WEEKLY data for coin: {coin}")
            query = f"""
                WITH weekly_bars AS (
                    SELECT DISTINCT ON (date_trunc('week', ts))
                        date_trunc('week', ts) AS week_time,
                        open,
                        high,
                        low,
                        close,
                        volume
                    FROM crypto.{coin}
                    ORDER BY date_trunc('week', ts), ts ASC
                )
                SELECT *
                FROM weekly_bars
                ORDER BY week_time;
            """

        elif resolution == "monthly":
            self.logger.info(f"Retrieving MONTHLY data for coin: {coin}")
            query = f"""
                WITH monthly_bars AS (
                    SELECT DISTINCT ON (date_trunc('month', ts))
                        date_trunc('month', ts) AS month_time,
                        open,
                        high,
                        low,
                        close,
                        volume
                    FROM crypto.{coin}
                    ORDER BY date_trunc('month', ts), ts ASC
                )
                SELECT *
                FROM monthly_bars
                ORDER BY month_time;
            """

        else:
            self.logger.error(f"Invalid resolution: {resolution}")
            return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, (coin,))
                rows = cursor.fetchall()
                self.logger.info(
                    f"Retrieved {len(rows)} rows for coin={coin} at resolution='{resolution}'"
                )
                return rows
        except psycopg2.Error as e:
            self.logger.error(f"Error retrieving crypto data: {e}")
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

    def get_option_chain(self,
                        ticker: str = None,
                        start_time: Optional[str] = None,
                        end_time: Optional[str] = None,
                        expiry: Optional[Union[str, int]] = None,
                        put: bool = True,
                        call: bool = True,
                        delta_away_from_atm: float = None,
                        resolution: str = "daily",
                        current: bool = True):
        """
        Retrieve option data from the database.

        Parameters:
            ticker (str): The underlying symbol (e.g., "AAPL"). (Required if option_symbol is not provided.)
            start_time (str, optional): Start date in "YYYY-MM-DD" format.
            end_time (str, optional): End date in "YYYY-MM-DD" format. If not provided and start_time is given, assumes current date.
            expiry (str or int, optional): Either a specific expiry date (as a string in "YYYY-MM-DD") 
                or an integer representing the number of days from the base date (start_time if provided, else current date) to the expiry.
            put (bool): Whether to include put options. Default is True.
            call (bool): Whether to include call options. Default is True.
            delta_away_from_abs_1_ (float, optional): Tolerance from 1 for call delta or -1 for put delta.
            resolution (str): Data resolution; kept for compatibility.
            current (bool): If True, force retrieval from the options.realtime table (returning only current data).
        
        Returns:
            If start_time and/or end_time are provided (i.e. historical filtering is requested):
                pd.DataFrame: A MultiIndex DataFrame with index levels ["Time", "Expiry_date"],
                so you can slice per expiry date.
            Otherwise:
                pd.DataFrame: A DataFrame of option chain data (organized as rows).
        """
        # Log the incoming parameters.
        self.logger.info(f"Retrieving option data for {ticker if ticker else ''}")

        # If start_time is provided without end_time, assume end_time is current date.
        if start_time and not end_time:
            end_time = datetime.datetime.now().strftime("%Y-%m-%d")

        if start_time or end_time:
            use_realtime = False
        else:
            use_realtime = True

        table = "options.realtime" if use_realtime else "options.historical"

        # Build the WHERE clause.
        where_clauses = []
        if ticker:
            where_clauses.append(f"underlying = '{ticker}'")
        else:
            self.logger.error("Either ticker or option_symbol must be provided.")
            raise ValueError("Either ticker or option_symbol must be provided.")

        if expiry is not None:
            if isinstance(expiry, int):
                base_date = start_time if start_time else datetime.now().strftime("%Y-%m-%d")
                base_dt = datetime.strftime(base_date, "%Y-%m-%d")
                computed_expiry = (base_dt + timedelta(days=expiry)).strftime("%Y-%m-%d")
                where_clauses.append(f"expiry_date = '{computed_expiry}'")
            elif isinstance(expiry, str):
                where_clauses.append(f"expiry_date = '{expiry}'")
            else:
                self.logger.error("Expiry must be either a string (YYYY-MM-DD) or an integer (days till expiry).")
                raise ValueError("Expiry must be either a string (YYYY-MM-DD) or an integer (days till expiry).")

        if not put and call:
            where_clauses.append("option_type = 'call'")
        elif not call and put:
            where_clauses.append("option_type = 'put'")
        elif not put and not call:
            self.logger.error("Both put and call cannot be false.")
            raise ValueError("At least one of put or call must be True.")

        if delta_away_from_atm is not None:
            if put and not call:
                where_clauses.append(f"ABS(delta - (-0.5)) <= {delta_away_from_atm}")
            elif call and not put:
                where_clauses.append(f"ABS(delta - 0.5) <= {delta_away_from_atm}")
            elif put and call:
                where_clauses.append(
                    f"((option_type = 'call' AND ABS(delta - 0.5) <= {delta_away_from_atm}) "
                    f"OR (option_type = 'put' AND ABS(delta + 0.5) <= {delta_away_from_atm}))"
                )

        if start_time and end_time:
            where_clauses.append(f"time BETWEEN '{start_time}' AND '{end_time}'")

        where_clause = " AND ".join(where_clauses)

        if current:
            order_by = "ORDER BY time ASC"
        else:
            order_by = "ORDER BY expiry_date ASC, strike ASC"

        query = f"""
            SELECT  symbol, description, strike, bid, ask, volume, last_volume, option_type, expiry_date,
                delta, gamma, theta, vega, rho, mid_iv, time
            FROM {table}
            WHERE {where_clause}
            {order_by};
        """


        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                self.logger.info(f"Retrieved {len(rows)} rows from {table}")
                return rows
        except Exception as e:
            self.logger.error(f"Error retrieving option data: {e}")
            raise e

    def get_option_quotes_by_ticker_expiration(self, ticker, expiration_date, start_time, end_time, interval_ms):
        """
        Fetches quote data for a given ticker and expiration date within a time range, sampled at `interval_ms` resolution.
        
        :param ticker: Ticker symbol (str)
        :param expiration_date: Expiration date (datetime or ISO string)
        :param start_time: Start of the time range (datetime)
        :param end_time: End of the time range (datetime)
        :param interval_ms: Interval in milliseconds between sampled points
        :return: List of (time, contract_id, bid, ask, bid_size, ask_size) tuples
        """
        try:
            with self.connection.cursor() as cursor:
                # Get ticker ID
                cursor.execute("SELECT id FROM options.tickers WHERE ticker = %s", (ticker,))
                result = cursor.fetchone()
                if not result:
                    self.logger.error(f"❌ Ticker '{ticker}' not found.")
                    return []
                ticker_id = result[0]

                # Get contract IDs with matching expiration
                cursor.execute("""
                    SELECT id FROM options.contracts
                    WHERE ticker_id = %s AND expiration = %s
                """, (ticker_id, expiration_date))
                contract_ids = [row[0] for row in cursor.fetchall()]
                if not contract_ids:
                    self.logger.warning(f"⚠️ No contracts found for ticker {ticker} expiring on {expiration_date}")
                    return []

                # Interval control: we reduce result set by bucketing timestamps
                interval = timedelta(milliseconds=interval_ms)

                # Build query using filtered contract_ids
                cursor.execute(f"""
                    SELECT DISTINCT ON (contract_id, time_bucket_gapfill(%s, time)) 
                        time, contract_id, bid, ask, bid_size, ask_size
                    FROM options.quotes
                    WHERE contract_id = ANY(%s)
                    AND time BETWEEN %s AND %s
                    ORDER BY contract_id, time_bucket_gapfill(%s, time), time
                """, (interval, contract_ids, start_time, end_time, interval))

                rows = cursor.fetchall()
                return rows

        except Exception as e:
            self.logger.error(f"❌ Error querying quotes for {ticker} expiring {expiration_date}: {e}")
            return []

    def explore_contracts(self, ticker):
        """
        Diagnoses the contracts and quotes in the DB for a given ticker.
        Allows interactive filtering to refine exploration.
        """
        import pandas as pd

        try:
            with self.connection.cursor() as cursor:
                # Step 1: Get Ticker ID
                cursor.execute("SELECT id FROM options.tickers WHERE ticker = %s", (ticker,))
                result = cursor.fetchone()
                if not result:
                    self.logger.error(f"❌ Ticker '{ticker}' not found.")
                    return []
                ticker_id = result[0]

                # Step 2: Fetch contract metadata
                cursor.execute("""
                    SELECT id, expiration, strike, side
                    FROM options.contracts
                    WHERE ticker_id = %s
                    ORDER BY expiration, strike
                """, (ticker_id,))
                contracts = cursor.fetchall()

                if not contracts:
                    self.logger.warning(f"⚠️ No contracts found for ticker '{ticker}'")
                    return []

                df = pd.DataFrame(contracts, columns=['id', 'expiration', 'strike', 'side'])
                df['expiration'] = pd.to_datetime(df['expiration'])

                # Step 3: Log summary stats
                total = len(df)
                calls = (df['side'] == 'C').sum()
                puts = (df['side'] == 'P').sum()
                self.logger.info(f"🔍 Ticker: {ticker}")
                self.logger.info(f"🧾 Total contracts: {total} | Calls: {calls} | Puts: {puts}")
                self.logger.info(f"📆 Expiration range: {df['expiration'].min().date()} → {df['expiration'].max().date()}")
                self.logger.info(f"💰 Strike range: {df['strike'].min()} → {df['strike'].max()}")

                print("\n🎯 Sample of grouped contracts:\n")
                grouped = df.groupby(['expiration', 'side'])['strike'].apply(list).reset_index()
                print(grouped.to_string(index=False))

                # Step 4: User chooses filter
                print("\n💡 Now define your filter criteria.\n")
                start_exp = pd.to_datetime(input("Start expiration (YYYY-MM-DD): "))
                end_exp = pd.to_datetime(input("End expiration (YYYY-MM-DD): "))
                strike_min = float(input("Min strike: "))
                strike_max = float(input("Max strike: "))
                side = input("Side (C/P/both): ").upper()

                filtered = df[
                    (df['expiration'] >= start_exp) &
                    (df['expiration'] <= end_exp) &
                    (df['strike'] >= strike_min) &
                    (df['strike'] <= strike_max)
                ]

                if side in ['C', 'P']:
                    filtered = filtered[filtered['side'] == side]

                selected_contract_ids = filtered['id'].tolist()

                self.logger.info(f"✅ Filtered contracts: {len(selected_contract_ids)}")

                # Step 5: Get quote stats for those contracts
                cursor.execute(f"""
                    SELECT contract_id, COUNT(*), MIN(time), MAX(time)
                    FROM options.quotes
                    WHERE contract_id = ANY(%s)
                    GROUP BY contract_id
                    ORDER BY COUNT(*) DESC
                """, (selected_contract_ids,))
                quote_stats = cursor.fetchall()
                print("\n📊 Quote stats per contract_id:")
                for cid, count, min_t, max_t in quote_stats:
                    print(f"  🧩 ID {cid}: {count} rows from {min_t} → {max_t}")

                return selected_contract_ids

        except Exception as e:
            self.logger.error(f"❌ Error exploring contracts for {ticker}: {e}")
            return []

        
