import io
import requests
import psycopg2
import datetime
from collections import defaultdict
from datetime import timedelta, date
import pytz
from psycopg2 import sql
from psycopg2.extras import execute_values
import logging
# import DatabaseConnection
import httpx
import csv


logger = logging.getLogger(__name__)

class DataCollector():
    """
    This Class connects multiple providers of data into one object
    """
    def __init__(self, db):
        self.db = db
        self.logger = logger


    def theta_option_list_expirations(self, symbol: str, base_url: str = "http://localhost:25503/v3") -> list:
        """
        List all expirations for an option with a given symbol.
        GET /v3/option/list/expirations?symbol=AAPL
        API returns CSV: symbol,expiration with rows like "AAPL","2012-06-01".
        Returns list of expiration integers (YYYYMMDD).
        """
        url = f"{base_url.rstrip('/')}/option/list/expirations"
        resp = httpx.get(url, params={"symbol": symbol}, timeout=30)
        resp.raise_for_status()
        text = resp.text.strip()
        if not text:
            return []
        result = []
        for line in csv.reader(io.StringIO(text)):
            if len(line) < 2:
                continue
            exp_str = line[1].strip('"')
            try:
                result.append(int(datetime.datetime.strptime(exp_str[:10], "%Y-%m-%d").strftime("%Y%m%d")))
            except ValueError:
                continue
        return sorted(set(result))

    def theta_option_list_dates_quote(self, symbol: str, expiration: str, base_url: str = "http://localhost:25503/v3") -> list:
        """
        List all dates that have option quote data for a given symbol and expiration.
        GET /v3/option/list/dates/quote?symbol=AAPL&expiration=20220930
        API returns CSV with header "date" and rows like "2025-06-23". Returns list of integers (YYYYMMDD).
        """
        url = f"{base_url.rstrip('/')}/option/list/dates/quote"
        exp_str = str(expiration)
        if len(exp_str) != 8 or not exp_str.isdigit():
            try:
                exp_str = datetime.datetime.strptime(exp_str[:10], "%Y-%m-%d").strftime("%Y%m%d")
            except ValueError:
                self.logger.warning("Invalid expiration format for list dates: %s", expiration)
                return []
        resp = httpx.get(url, params={"symbol": symbol, "expiration": exp_str}, timeout=30)
        resp.raise_for_status()
        text = resp.text.strip()
        if not text:
            return []
        result = []
        for line in csv.reader(io.StringIO(text)):
            if not line:
                continue
            date_str = line[0].strip('"')
            try:
                result.append(int(datetime.datetime.strptime(date_str[:10], "%Y-%m-%d").strftime("%Y%m%d")))
            except ValueError:
                continue
        return sorted(set(result))

    def theta_option_list_strikes(self, symbol: str, expiration: str, base_url: str = "http://localhost:25503/v3") -> list:
        """
        List all strikes for an option with a given symbol and expiration.
        GET /v3/option/list/strikes?symbol=AAPL&expiration=20220930
        API returns CSV: symbol,strike with rows like "MSFT",240.000. Returns list of strike floats.
        """
        url = f"{base_url.rstrip('/')}/option/list/strikes"
        exp_str = str(expiration)
        if len(exp_str) != 8 or not exp_str.isdigit():
            try:
                exp_str = datetime.datetime.strptime(exp_str[:10], "%Y-%m-%d").strftime("%Y%m%d")
            except ValueError:
                self.logger.warning("Invalid expiration format for list strikes: %s", expiration)
                return []
        resp = httpx.get(url, params={"symbol": symbol, "expiration": exp_str}, timeout=30)
        resp.raise_for_status()
        text = resp.text.strip()
        if not text:
            return []
        result = []
        for line in csv.reader(io.StringIO(text)):
            if len(line) < 2:
                continue
            try:
                result.append(float(line[1].strip('"')))
            except ValueError:
                continue
        return sorted(set(result))

    def theta_option_quotes(
        self, symbol: str, date_yyyymmdd: str, expiration=None, base_url: str = None
    ) -> int:
        """
        Fetch option history quotes for one date (and optionally one expiration) from ThetaData API.
        API returns CSV. expiration: None or "*" or "" = request all (send "*"); or YYYYMMDD (int/str) for a single expiration.
        Ensures each contract exists in options.contracts, inserts quotes into options.quotes.
        Returns count of quote rows inserted.
        """
        base_url = base_url or getattr(self, "_theta_base_url", None) or "http://127.0.0.1:25503/v3"
        base_url = base_url.rstrip("/")
        url = f"{base_url}/option/history/quote"
        if expiration is None or expiration == "" or str(expiration).strip().upper() == "*":
            exp_param = "*"
        else:
            try:
                exp_param = str(int(str(expiration).strip().replace("-", "")))
                if len(exp_param) != 8:
                    exp_param = "*"
            except (ValueError, TypeError):
                exp_param = "*"
        params = {
            "symbol": symbol,
            "expiration": exp_param,
            "date": str(date_yyyymmdd),
            "interval": "1m",
        }
        try:
            resp = httpx.get(url, params=params, timeout=120)
            if resp.status_code == 472:
                self.logger.info("No data for %s on %s (HTTP 472)", symbol, date_yyyymmdd)
                return 0
            resp.raise_for_status()
            text = resp.text.strip()
            if not text:
                self.logger.info("Empty response for %s on %s", symbol, date_yyyymmdd)
                return 0
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            raise
        except Exception as e:
            self.logger.error("Error fetching option history/quote for %s %s: %s", symbol, date_yyyymmdd, e)
            raise

        # Parse CSV (API returns CSV; format=json is deprecated)
        # Header: symbol,expiration,strike,right,timestamp,bid_size,bid_exchange,bid,bid_condition,ask_size,ask_exchange,ask,ask_condition
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return 0
        header = [c.strip().lower() for c in rows[0]]
        col_idx = {}
        for name in ("symbol", "expiration", "strike", "right", "timestamp",
                     "bid_size", "bid_exchange", "bid", "bid_condition",
                     "ask_size", "ask_exchange", "ask", "ask_condition"):
            try:
                col_idx[name] = header.index(name)
            except ValueError:
                col_idx[name] = None
        if col_idx["symbol"] is None or col_idx["timestamp"] is None:
            self.logger.warning("CSV missing required columns (symbol, timestamp): %s", header)
            return 0

        def _get(row, name, default=None):
            i = col_idx.get(name)
            if i is None or i >= len(row):
                return default
            val = row[i].strip().strip('"')
            return val if val else default

        def _num(s, default=None):
            if s is None or s == "":
                return default
            try:
                return float(s)
            except ValueError:
                return default

        def _int(s, default=0):
            if s is None or s == "":
                return default
            try:
                return int(float(s))
            except (ValueError, TypeError):
                return default

        contract_cache = {}
        contract_id_to_exp = {}
        quotes = []
        for row in rows[1:]:
            if len(row) < 5:
                continue
            sym = (_get(row, "symbol") or symbol).strip() or symbol
            exp_val = _get(row, "expiration")
            if not exp_val:
                continue
            try:
                if len(str(exp_val)) == 8 and str(exp_val).isdigit():
                    exp_int = int(exp_val)
                else:
                    exp_int = int(datetime.datetime.strptime(str(exp_val)[:10], "%Y-%m-%d").strftime("%Y%m%d"))
            except (ValueError, TypeError):
                continue
            try:
                strike_float = float(_get(row, "strike") or 0)
            except (TypeError, ValueError):
                continue
            right_raw = (_get(row, "right") or "C").upper()
            side = "put" if right_raw in ("P", "PUT") else "call"
            ts_str = _get(row, "timestamp")
            if not ts_str:
                continue
            try:
                if "T" in str(ts_str):
                    t = datetime.datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
                else:
                    t = datetime.datetime.strptime(str(ts_str)[:19], "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                continue
            if t.tzinfo is not None:
                t = t.replace(tzinfo=None)
            key = (sym, exp_int, strike_float, side)
            if key not in contract_cache:
                contract = {"root": sym, "expiration": exp_int, "strike": strike_float, "right": side}
                cid = self.db.get_or_create_contract(contract)
                if not cid:
                    continue
                contract_cache[key] = cid
                contract_id_to_exp[cid] = exp_int
            contract_id = contract_cache[key]
            bid = _num(_get(row, "bid"))
            ask = _num(_get(row, "ask"))
            bid_size = _int(_get(row, "bid_size"), 0)
            ask_size = _int(_get(row, "ask_size"), 0)
            bid_exchange = _int(_get(row, "bid_exchange")) if _get(row, "bid_exchange") not in (None, "") else None
            ask_exchange = _int(_get(row, "ask_exchange")) if _get(row, "ask_exchange") not in (None, "") else None
            bid_condition = _int(_get(row, "bid_condition")) if _get(row, "bid_condition") not in (None, "") else None
            ask_condition = _int(_get(row, "ask_condition")) if _get(row, "ask_condition") not in (None, "") else None
            quote_row = (
                t,
                contract_id,
                bid,
                bid_size,
                bid_exchange,
                bid_condition,
                ask,
                ask_size,
                ask_exchange,
                ask_condition,
            )
            quotes.append(quote_row)

        if not quotes:
            return 0
        # Debug: print first 5 tuples before inserting
        debug_count = min(5, len(quotes))
        for idx in range(debug_count):
            print("quote tuple[%s]: %s" % (idx, quotes[idx]))
        if len(quotes) > debug_count:
            print("... and %s more quote tuples" % (len(quotes) - debug_count))
        for idx, tup in enumerate(quotes[:5]):
            self.logger.info("quote tuple[%s]: %s", idx, tup)
        if len(quotes) > 5:
            self.logger.info("... and %s more quote tuples", len(quotes) - 5)
        page_size = 10000
        for i in range(0, len(quotes), page_size):
            chunk = quotes[i : i + page_size]
            self.db.insert_option_quotes(chunk)
        # Per-expiration summary: quotes count and contract count for each expiration
        exp_quotes = defaultdict(int)
        exp_contracts = defaultdict(set)
        for row in quotes:
            cid = row[1]
            exp = contract_id_to_exp.get(cid)
            if exp is not None:
                exp_quotes[exp] += 1
                exp_contracts[exp].add(cid)
        for exp in sorted(exp_quotes.keys()):
            self.logger.info(
                "Inserted %s quotes for %s contracts for expiration %s for symbol %s",
                exp_quotes[exp], len(exp_contracts[exp]), exp, symbol,
            )
        return len(quotes)

    def timestamp_to_datetime(self, timestamp):
        etz = pytz.timezone('US/Eastern')
        utc_time = datetime.datetime.fromtimestamp(timestamp, pytz.utc)
        eastern_timestamp = utc_time.astimezone(etz)
        return eastern_timestamp.strftime('%Y-%m-%d %H:%M:%S')


    def theta_stocks_quote(
            self,
            ticker: str,
            date: str,
            end_date: str = None,
            interval: str = "1s",
            start_time: str = "09:30:00",
            end_time: str = "16:00:00",
            venue: str = "nqb",
            format: str = "csv",
            return_tuples: bool = False,
            base_url: str = "http://localhost:25503/v3"
        ) -> list:
        """
        Fetches stock quote data for a given ticker using the Theta Terminal v3 API.
        Returns NBBO quotes as tuples (timestamp, ticker_id, bid, bid_size, bid_exchange, bid_condition, ask, ask_size, ask_exchange, ask_condition).

        Parameters:
            ticker (str): The stock symbol (e.g., 'AAPL').
            date (str): Date in YYYYMMDD format (e.g., '20240102'). Required.
            end_date (str): End date in YYYYMMDD format (optional). If None, only fetches single date.
            interval (str): Time interval - one of: tick, 10ms, 100ms, 500ms, 1s, 5s, 10s, 15s, 30s, 1m, 5m, 10m, 15m, 30m, 1h. Default: "1m"
            start_time (str): Start time in format "HH:MM:SS" (default: "09:30:00").
            end_time (str): End time in format "HH:MM:SS" (default: "16:00:00").
            venue (str): Market feed ('nqb' = Nasdaq Basic, 'utp_cta' = merged UTP & CTA). Default: "nqb"
            format (str): Response format - 'csv', 'json', 'ndjson', or 'html'. Default: "csv"
            return_tuples (bool): (Ignored, always returns tuples).
            base_url (str): Base URL for Theta Terminal API. Default: "http://localhost:25503/v3"

        Returns:
            List of tuples: (timestamp, ticker_id, bid, bid_size, bid_exchange, bid_condition, ask, ask_size, ask_exchange, ask_condition)
        """
        from datetime import datetime, timedelta
        import httpx
        import csv
        import io
        import requests

        url = f"{base_url}/stock/history/quote"

        params = {
            "symbol": ticker,
            "date": date,
            "interval": interval,
            "start_time": start_time,
            "end_time": end_time,
            "venue": venue,
            "format": format
        }

        # Prepare list of dates to fetch
        dates_to_fetch = [date]
        if end_date and end_date != date:
            start_dt = datetime.strptime(date, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")
            dates_to_fetch = []
            current_dt = start_dt
            while current_dt <= end_dt:
                dates_to_fetch.append(current_dt.strftime("%Y%m%d"))
                current_dt += timedelta(days=1)

        ticker_id = self.db.get_or_create_root(ticker)
        all_results = []

        for fetch_date in dates_to_fetch:
            params["date"] = fetch_date

            try:
                if format == "csv":
                    with httpx.stream("GET", url, params=params, timeout=60) as response:
                        response.raise_for_status()
                        first_line = True

                        for line in response.iter_lines():
                            line = line.decode() if hasattr(line, "decode") else line
                            if not line.strip():
                                continue

                            # Skip header row
                            if first_line:
                                first_line = False
                                if 'timestamp' in line.lower() or line.strip().startswith('timestamp'):
                                    continue

                            try:
                                row = next(csv.reader(io.StringIO(line)))
                                if len(row) < 9:
                                    continue

                                timestamp_str = row[0].strip()
                                if timestamp_str.lower() == 'timestamp' or not timestamp_str[0].isdigit():
                                    continue

                                # Parse timestamp with full time (to get ms_of_day)
                                try:
                                    # Try most common ISO formats first
                                    if 'T' in timestamp_str:
                                        if '+' in timestamp_str or timestamp_str.endswith('Z'):
                                            # ISO8601 with timezone
                                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                        else:
                                            try:
                                                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")
                                            except ValueError:
                                                try:
                                                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
                                                except ValueError:
                                                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                    else:
                                        # Try fallback: YYYYMMDD[ HH:MM:SS(.sss)]
                                        try:
                                            timestamp = datetime.strptime(timestamp_str, "%Y%m%d %H:%M:%S.%f")
                                        except ValueError:
                                            try:
                                                timestamp = datetime.strptime(timestamp_str, "%Y%m%d %H:%M:%S")
                                            except ValueError:
                                                timestamp = datetime.strptime(timestamp_str, "%Y%m%d")
                                except ValueError as ve:
                                    self.logger.warning(f"Could not parse timestamp '{timestamp_str}': {ve}")
                                    continue

                                # Store as naive datetime only (no timezone) to avoid alignment errors
                                if timestamp.tzinfo is not None:
                                    timestamp = timestamp.replace(tzinfo=None)

                                # Get ms_of_day
                                ms_of_day = (timestamp.hour * 3600 + timestamp.minute * 60 + timestamp.second) * 1000 + getattr(timestamp, "microsecond", 0) // 1000

                                # Parse other fields per schema
                                bid_size = int(row[1])
                                bid_exchange = int(row[2])
                                bid = float(row[3])
                                bid_condition = int(row[4])
                                ask_size = int(row[5])
                                ask_exchange = int(row[6])
                                ask = float(row[7])
                                ask_condition = int(row[8])

                                # Required tuple: (timestamp, ticker_id, bid, bid_size, bid_exchange, bid_condition, ask, ask_size, ask_exchange, ask_condition)
                                quote_tuple = (
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
                                )
                                all_results.append(quote_tuple)
                            except (ValueError, IndexError) as e:
                                self.logger.warning(f"Could not parse row: {line[:100]} -> {e}")
                                continue
                else:
                    # Use requests for non-CSV formats (not commonly used, fallback logic)
                    response = requests.get(url, params=params, timeout=60)
                    response.raise_for_status()
                    if format == "json":
                        data = response.json()
                        self.logger.warning("JSON format parsing not yet implemented for theta_stocks_quote.")
                    else:
                        rows = response.text.strip().split("\n")
                        for row in rows:
                            if not row.strip():
                                continue
                            # Placeholder for other formats

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 472:
                    self.logger.info(f"No data available for {ticker} on {fetch_date} (HTTP 472)")
                else:
                    self.logger.error(f"HTTP error fetching data for {ticker} on {fetch_date}: {e}")
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error fetching data for {ticker} on {fetch_date}: {e}")
                continue

        if all_results:
            self.logger.info(f"Collected {len(all_results)} stock quote records for {ticker}.")
        else:
            self.logger.warning(f"No valid stock quote records were parsed for {ticker}.")

        return all_results
        return all_results
