import argparse
import requests
import os
import psycopg2
from psycopg2 import sql, errors
from datetime import datetime, timedelta

def get_market_schedule(date, output_format='json', host='localhost', port=25503, verify_ssl=False):
    """
    Retrieves equity market schedule for a given date from Theta Terminal v3 REST API.
    Returns a tuple: (schedule_type, open_time, close_time)
    """
    url = f"http://{host}:{port}/v3/calendar/on_date"
    params = {
        "date": date,
        "format": output_format
    }
    try:
        resp = requests.get(url, params=params, verify=verify_ssl)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            info = data[0]
        else:
            info = data
        schedule_type = info.get("type", "")
        open_time = info.get("open", "")
        close_time = info.get("close", "")
        return schedule_type, open_time, close_time
    except Exception as e:
        print(f"Error retrieving market schedule for {date}: {e}")
        return None, None, None

def daterange(start_date, end_date):
    """Generator that yields all dates from start_date to end_date inclusive (as strings YYYYMMDD)"""
    cur = start_date
    while cur <= end_date:
        yield cur.strftime("%Y%m%d")
        cur += timedelta(days=1)

def ensure_table_exists(conn):
    """
    Ensures the market_schedule table exists in the public schema with correct constraints.
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.market_timings (
                id SERIAL PRIMARY KEY,
                date INTEGER UNIQUE,
                open INTEGER,
                close INTEGER
            )
        """)
        conn.commit()

def insert_row(conn, date, open_time, close_time):
    """
    Inserts a row into the market_timings table.
    open_time and close_time can be None, which will be converted to 0.
    """
    try:
        int_date = int(date)
        # Convert None to 0, otherwise convert to int
        int_open = 0 if open_time is None else int(open_time)
        int_close = 0 if close_time is None else int(close_time)
    except Exception as e:
        print(f"Skipping insert for {date} due to bad int conversion: {e}")
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.market_timings (date, open, close)
                VALUES (%s, %s, %s)
                ON CONFLICT (date) DO NOTHING
                """,
                (int_date, int_open, int_close)
            )
        conn.commit()
        print(f"Inserted: (date={int_date}, open={int_open}, close={int_close})")
    except Exception as e:
        print(f"Error inserting row for {date}: {e}")
        conn.rollback()

def main():
    parser = argparse.ArgumentParser(
        description="Fetch market open & close times for a given date or date range and insert into Postgres."
    )
    parser.add_argument("date", nargs='?', help="Date in YYYYMMDD format (e.g., 20251225), or --from/--to range.")
    parser.add_argument("--from", dest="from_date", help="First date in date range (YYYYMMDD)")
    parser.add_argument("--to", dest="to_date", help="Last date in date range (YYYYMMDD). If --from given, --to is required.")
    parser.add_argument("--host", default="localhost", help="Theta Terminal host (default: localhost)")
    parser.add_argument("--port", default=25503, type=int, help="Theta Terminal port (default: 25503)")
    parser.add_argument("--format", choices=["json", "csv", "ndjson", "html"], default="json", help="Result format (default: json)")
    parser.add_argument("--insecure", action="store_true", help="Disable SSL verification (for self-signed certs/local)")
    args = parser.parse_args()

    # Parse date or date range
    if args.from_date and args.to_date:
        try:
            start_dt = datetime.strptime(args.from_date, "%Y%m%d")
            end_dt = datetime.strptime(args.to_date, "%Y%m%d")
            if end_dt < start_dt:
                raise ValueError("--to date must be after --from date")
        except ValueError as e:
            print(f"Invalid range: {e}")
            return
        dates = list(daterange(start_dt, end_dt))
    elif args.date:
        dates = [args.date]
    else:
        print("Please specify a single date or both --from and --to for a date range.")
        return

    # Get Postgres connection params from env
    pg_user = os.getenv("PGUSER")
    pg_password = os.getenv("PGPASSWORD")
    pg_host = os.getenv("PGHOST", "192.168.1.209")
    pg_port = os.getenv("PGPORT", "31379")
    pg_db = os.getenv("PGDATABASE")

    if not all([pg_user, pg_password, pg_db]):
        raise ValueError("Please set environment variables PGUSER, PGPASSWORD, PGDATABASE (and optionally PGHOST, PGPORT)")

    try:
        conn = psycopg2.connect(
            user=pg_user,
            password=pg_password,
            host=pg_host,
            port=pg_port,
            database=pg_db
        )
        ensure_table_exists(conn)
    except Exception as e:
        print(f"Database connection/init error: {e}")
        return

    for date in dates:
        sched_type, open_tm, close_tm = get_market_schedule(
            date,
            output_format=args.format,
            host=args.host,
            port=args.port,
            verify_ssl=not args.insecure
        )
        
        # Convert times to HHMM integer, if they are strings like "09:30"
        # Always process, even if times are None (weekends/holidays)
        def normalize_time(t):
            # Handle lists - extract first element
            if isinstance(t, list):
                if len(t) == 0:
                    return None
                t = t[0]
            
            # Handle None - return None (will be converted to 0 in insert_row)
            if t is None:
                return None
            
            # Accept HH:MM:SS, HH:MM, HHMM or integer
            if isinstance(t, int):
                return t
            elif isinstance(t, str):
                # Remove all colons and take first 4 characters (HHMM format)
                cleaned = t.replace(":", "")
                # Take only HHMM (first 4 digits)
                cleaned = cleaned[:4]
                if len(cleaned) == 0:
                    return None
                return int(cleaned)
            else:
                return None

        norm_open = normalize_time(open_tm)
        norm_close = normalize_time(close_tm)
        
        # Always insert, even if times are None (will be stored as 0)
        insert_row(conn, date, norm_open, norm_close)

    if conn:
        conn.close()

if __name__ == "__main__":
    main()
