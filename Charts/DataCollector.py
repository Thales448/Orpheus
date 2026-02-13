import requests
import psycopg2
import datetime
from datetime import timedelta, date
import pytz
from psycopg2 import sql
from psycopg2.extras import execute_values
import logging
import DatabaseConnection
import httpx
import csv
HEADERS ='hello'


logger = logging.getLogger(__name__)

class DataCollector():
    """
    This Class connects multiple providers of data into one object
    """
    def __init__(self, db):
        self.db = db
        self.logger = logger
    def collect_expiration_dates(self, paramaters):
        """
        Collect expiration dates for options.
        
        Parameters needed:
        - "symbol": string - The underlying symbol
        
        Returns:
        - List of expiration dates or None if error
        """
        url = 'http://127.0.0.1:25510/v3/list/expirations'
        
        try:
            while url is not None:
                response = httpx.get(url, params=paramaters, timeout=60)
                response.raise_for_status() 

                if 'Next-Page' in response.headers and response.headers['Next-Page'] != "null":
                    url = response.headers['Next-Page']
                    paramaters = None
                else:
                    url = None
            
            return response.json()['response']
        except Exception as e:
            self.logger.error(f"Error collecting expiration dates: {e}")
            return None

    def theta_option_list_expirations(self, symbol: str, base_url: str = "http://localhost:25503/v3") -> list:
        """
        List all expirations for an option with a given symbol.
        GET /v3/option/list/expirations?symbol=AAPL
        Returns list of expiration integers (YYYYMMDD) or empty list on error.
        Handles JSON or plain/text (one expiration per line) responses.
        """
        url = f"{base_url.rstrip('/')}/option/list/expirations"
        resp = None
        try:
            resp = httpx.get(url, params={"symbol": symbol}, timeout=30)
            resp.raise_for_status()
            text = resp.text.strip()
            if not text:
                self.logger.warning(f"Option list/expirations for {symbol}: empty response body")
                return []
            content_type = (resp.headers.get("content-type") or "").lower()
            if "json" in content_type:
                try:
                    data = resp.json()
                except Exception:
                    data = None
                if data is not None:
                    out = data.get("response") or data.get("expirations") or data
                    if isinstance(out, list):
                        return [int(x) for x in out if str(x).isdigit()]
                    return []
            # Plain text / CSV: one expiration per line (or fallback if JSON failed)
            expirations = []
            for line in text.splitlines():
                line = line.strip()
                if line.isdigit() and len(line) == 8:
                    expirations.append(int(line))
                else:
                    for part in line.replace(",", " ").split():
                        if part.isdigit() and len(part) == 8:
                            expirations.append(int(part))
            return sorted(expirations) if expirations else []
        except Exception as e:
            self.logger.error(f"Error listing option expirations for {symbol}: {e}")
            if resp is not None and getattr(resp, "text", None):
                self.logger.debug(f"Response body (first 200 chars): {resp.text[:200]!r}")
            return []

    def theta_option_list_dates_quote(self, symbol: str, expiration: str, base_url: str = "http://localhost:25503/v3") -> list:
        """
        List all dates that have option quote data for a given symbol and expiration.
        GET /v3/option/list/dates/quote?symbol=AAPL&expiration=20220930
        Returns list of date strings (YYYYMMDD) or empty list on error.
        """
        url = f"{base_url.rstrip('/')}/option/list/dates/quote"
        exp_str = str(expiration)
        if len(exp_str) == 8 and exp_str.isdigit():
            pass
        else:
            try:
                from datetime import datetime
                exp_str = datetime.strptime(exp_str, "%Y-%m-%d").strftime("%Y%m%d")
            except ValueError:
                self.logger.warning(f"Invalid expiration format for list dates: {expiration}")
                return []
        try:
            resp = httpx.get(url, params={"symbol": symbol, "expiration": exp_str}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response") or []
        except Exception as e:
            self.logger.debug(f"Error listing quote dates for {symbol} exp {expiration}: {e}")
            return []

    def theta_option_list_strikes(self, symbol: str, expiration: str, base_url: str = "http://localhost:25503/v3") -> list:
        """
        List all strikes for an option with a given symbol and expiration.
        GET /v3/option/list/strikes?symbol=AAPL&expiration=20220930
        Returns list of strike numbers or empty list on error.
        """
        url = f"{base_url.rstrip('/')}/option/list/strikes"
        exp_str = str(expiration)
        if len(exp_str) == 8 and exp_str.isdigit():
            pass
        else:
            try:
                from datetime import datetime
                exp_str = datetime.strptime(exp_str, "%Y-%m-%d").strftime("%Y%m%d")
            except ValueError:
                self.logger.warning(f"Invalid expiration format for list strikes: {expiration}")
                return []
        try:
            resp = httpx.get(url, params={"symbol": symbol, "expiration": exp_str}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response") or []
        except Exception as e:
            self.logger.debug(f"Error listing strikes for {symbol} exp {expiration}: {e}")
            return []

    def theta_options_quotes(
        self,
        symbol: str,
        date: str,
        end_date: str = None,
        expiration: str = "*",
        strike: str = "*",
        right: str = "both",
        interval: str = "1m",
        start_time: str = "09:30:00",
        end_time: str = "16:00:00",
        format: str = "csv",
        base_url: str = "http://localhost:25503/v3"
    ) -> list:
        """
        Fetches option quote data from Theta Terminal v3 API.
        Returns NBBO quotes as tuples (time, contract_id, bid, bid_size, bid_exchange, bid_condition, ask, ask_size, ask_exchange, ask_condition).
        
        Parameters:
            symbol (str): Underlying symbol (e.g., 'AAPL')
            date (str): Date in YYYYMMDD format (required)
            end_date (str): End date in YYYYMMDD format (optional)
            expiration (str): Expiration in YYYYMMDD/YYYY-MM-DD or '*' for all (default: '*')
            strike (str): Strike price or '*' for all (default: '*')
            right (str): 'call', 'put', or 'both' (default: 'both')
            interval (str): Time interval (default: '1m')
            start_time (str): Start time HH:MM:SS (default: '09:30:00')
            end_time (str): End time HH:MM:SS (default: '16:00:00')
            format (str): Response format (default: 'csv')
            base_url (str): API base URL (default: 'http://localhost:25503/v3')
        """
        from datetime import datetime, timedelta
        import io
        
        url = f"{base_url}/option/history/quote"
        
        # Build date list
        dates_to_fetch = [date]
        if end_date and end_date != date:
            start_dt = datetime.strptime(date, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")
            dates_to_fetch = []
            current_dt = start_dt
            while current_dt <= end_dt:
                dates_to_fetch.append(current_dt.strftime("%Y%m%d"))
                current_dt += timedelta(days=1)
        
        all_results = []
        contract_cache = {}  # Cache contract IDs: (symbol, expiration, strike, right) -> contract_id
        
        for fetch_date in dates_to_fetch:
            params = {
                "symbol": symbol,
                "date": fetch_date,
                "expiration": expiration,
                "strike": strike,
                "right": right,
                "interval": interval,
                "start_time": start_time,
                "end_time": end_time,
                "format": format
            }
            
            try:
                with httpx.stream("GET", url, params=params, timeout=60) as response:
                    response.raise_for_status()
                    first_line = True
                    
                    for line in response.iter_lines():
                        line = line.decode() if hasattr(line, "decode") else line
                        if not line.strip():
                            continue
                        
                        # Skip header
                        if first_line:
                            first_line = False
                            if 'symbol' in line.lower() or 'timestamp' in line.lower():
                                continue
                        
                        try:
                            row = next(csv.reader(io.StringIO(line)))
                            if len(row) < 13:
                                continue
                            
                            # Parse CSV: symbol, expiration, strike, right, timestamp, bid_size, bid_exchange, bid, bid_condition, ask_size, ask_exchange, ask, ask_condition
                            sym, exp_str, strike_str, right_str, timestamp_str = row[0], row[1], row[2], row[3], row[4]
                            bid_size, bid_exchange, bid, bid_condition = int(row[5]), int(row[6]), float(row[7]), int(row[8])
                            ask_size, ask_exchange, ask, ask_condition = int(row[9]), int(row[10]), float(row[11]), int(row[12])
                            
                            # Parse timestamp
                            try:
                                if 'T' in timestamp_str:
                                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                else:
                                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
                            except ValueError:
                                try:
                                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                except ValueError:
                                    self.logger.warning(f"Could not parse timestamp '{timestamp_str}'")
                                    continue
                            
                            # Convert expiration to integer YYYYMMDD
                            try:
                                if '-' in exp_str:
                                    exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
                                else:
                                    exp_dt = datetime.strptime(exp_str, "%Y%m%d")
                                expiration_int = int(exp_dt.strftime("%Y%m%d"))
                            except ValueError:
                                self.logger.warning(f"Could not parse expiration '{exp_str}'")
                                continue
                            
                            # Convert strike to numeric
                            try:
                                strike_float = float(strike_str)
                            except ValueError:
                                self.logger.warning(f"Could not parse strike '{strike_str}'")
                                continue
                            
                            # Get or create contract (with caching)
                            contract_key = (sym, expiration_int, strike_float, right_str)
                            if contract_key not in contract_cache:
                                contract_meta = {
                                    'root': sym,
                                    'expiration': expiration_int,
                                    'strike': strike_float,
                                    'right': right_str
                                }
                                contract_id = self.db.get_or_create_contract(contract_meta)
                                if contract_id is None:
                                    continue
                                contract_cache[contract_key] = contract_id
                            else:
                                contract_id = contract_cache[contract_key]
                            
                            # Build tuple: (time, contract_id, bid, bid_size, bid_exchange, bid_condition, ask, ask_size, ask_exchange, ask_condition)
                            all_results.append((
                                timestamp,
                                contract_id,
                                bid,
                                bid_size,
                                bid_exchange,
                                bid_condition,
                                ask,
                                ask_size,
                                ask_exchange,
                                ask_condition
                            ))
                        except (ValueError, IndexError) as e:
                            self.logger.warning(f"Could not parse row: {line[:100]} -> {e}")
                            continue
                            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 472:
                    self.logger.info(f"No data available for {symbol} on {fetch_date} (HTTP 472)")
                else:
                    self.logger.error(f"HTTP error fetching data for {symbol} on {fetch_date}: {e}")
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error fetching data for {symbol} on {fetch_date}: {e}")
                continue
        
        if all_results:
            self.logger.info(f"Collected {len(all_results)} option quote records for {symbol}.")
        else:
            self.logger.warning(f"No valid option quote records were parsed for {symbol}.")
        
        return all_results


    def populate_options(self, ticker, date, end_date, interval):
        import httpx

        import time
        from datetime import datetime, timedelta

        API_QUOTES_URL = "http://192.168.1.138:25503/v3/bulk_hist/option/quote"
        API_EXPIRATIONS_URL = "http://192.168.1.138:25503/v3/option/list/expirations"
        RETRIES = 3
        RETRY_DELAY = 5 
        
        def build_date_windows(expiration, date_bound=None, end_date_bound=None):
            try:
                expiration_str = str(expiration)
                expiration_date = datetime.strptime(expiration_str, "%Y%m%d")
            except Exception as e:
                raise ValueError(f"❌ Invalid expiration '{expiration}': {e}")

            # Default range: 210 days before expiration to 1 day before expiration
            date = expiration_date - timedelta(days=210)
            end_cutoff = expiration_date - timedelta(days=1)

            # Apply bounds if provided
            if date_bound:
                try:
                    date_str = str(date_bound)
                    date = max(date, datetime.strptime(date_str, "%Y%m%d"))
                except Exception as e:
                    raise ValueError(f"❌ Invalid date_bound '{date_bound}': {e}")

            if end_date_bound:
                try:
                    end_date_str = str(end_date_bound)
                    end_cutoff = min(end_cutoff, datetime.strptime(end_date_str, "%Y%m%d"))
                except Exception as e:
                    raise ValueError(f"❌ Invalid end_date_bound '{end_date_bound}': {e}")

            # Build windows
            windows = []
            current_day = date
            while current_day < end_cutoff:
                days_to_exp = (expiration_date - current_day).days
                step = timedelta(days=30 if days_to_exp > 180 else 20 if days_to_exp > 7 else 5)
                end_day = min(current_day + step - timedelta(days=1), end_cutoff)
                windows.append((int(current_day.strftime("%Y%m%d")), int(end_day.strftime("%Y%m%d"))))
                current_day = end_day + timedelta(days=1)

            return windows


        def safe_http_get(url, params, timeout=120):
            for attempt in range(RETRIES):
                try:
                    response = httpx.get(url, params=params, timeout=timeout)
                    if response.status_code == 472:
                        return None  # silently skip
                    response.raise_for_status()
                    return response
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 472:
                        return None  # silently skip
                    raise
                except (httpx.RequestError, httpx.TimeoutException) as e:
                    if attempt < RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        raise e

        def runmain(ticker, date, end_date, interval):
            try:
                response = safe_http_get(API_EXPIRATIONS_URL, params={"symbol": ticker})
                if response is None:
                    logger.info(f"[{ticker}] ⚠️ Skipping due to 472 response")
                    return
                expirations = response.json().get('response', [])
                filtered_expirations = [e for e in expirations if int(date) <= e <= int(end_date)]
            except Exception as e:
                logger.exception(f"[{ticker}] ❌ Error fetching expirations: {e}")
                return

            for expiration in filtered_expirations:
                windows = build_date_windows(expiration, date_bound=date, end_date_bound=end_date)
                for window_start, window_end in windows:
                    params = {
                        'symbol': ticker,
                        'exp': expiration,
                        'date': window_start,
                        'end_date': window_end,
                        'ivl': interval,
                        'pretty_time': False,
                        'use_csv': False
                    }
                    try:
                        response = safe_http_get(API_QUOTES_URL, params=params, timeout=120)
                        if response is None:
                            logger.info(f"[{ticker} {expiration}] ⚠️ Skipping window {window_start}–{window_end} due to 472")
                            continue

                        data = response.json()
                        rows = []
                
                        for item in data.get("response", []):
                            contract_info = item["contract"]
                            contract_meta = {
                                'symbol': contract_info["symbol"],
                                'expiration': int(contract_info["expiration"]),
                                'strike': int(contract_info["strike"]),
                                'right': contract_info["right"]
                            }
    
                            contract_id = self.db.get_or_create_contract(contract_meta)

                            for tick in item["ticks"]:
                                ms_of_day = tick[0]
                                bid_size = tick[1]
                                bid_ex = tick[2]
                                bid = tick[3]
                                bid_cond = tick[4]
                                ask_size = tick[5]
                                ask_ex = tick[6]
                                ask = tick[7]
                                ask_cond = tick[8]
                                date = tick[9]
                               
                                
                                ts = datetime.strptime(str(date), "%Y%m%d") + timedelta(milliseconds=ms_of_day)
                                timestampz = ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                                rows.append([
                                    timestampz,
                                    contract_id,
                                    float(bid), int(bid_size), int(bid_ex), int(bid_cond),
                                    float(ask), int(ask_size), int(ask_ex), int(ask_cond)
                                ])

                        if rows:
                            self.db.insert_option_quotes(rows)
                        logger.info(f"[{ticker} {expiration}] ✅ Finished {window_start}–{window_end}")
                    except Exception as e:
                        logger.exception(f"[{ticker} {expiration}] ❌ Error for window {window_start}–{window_end}: {e}")

        runmain(ticker, date, end_date, interval)

    def timestamp_to_datetime(self, timestamp):
        etz = pytz.timezone('US/Eastern')
        utc_time = datetime.datetime.fromtimestamp(timestamp, pytz.utc)
        eastern_timestamp = utc_time.astimezone(etz)
        return eastern_timestamp.strftime('%Y-%m-%d %H:%M:%S')

    def get_stocks_minute(self, ticker, for_the_past_x_days = 356):

        end_date = date.today()
        date = end_date - (timedelta(for_the_past_x_days))
        url = f'https://api.marketdata.app/v1/stocks/candles/minutely/{ticker}/?from={date}&to={end_date}'

        ticker_list = []
        response = requests.get(
            url, 
            headers=self.MD_HEADER
        )

        if response.status_code in (200, 203):
            data = response.json()
        else:
            logger.info(f'Failed API call for {ticker} minute stock: {response.status_code} for url: {url}')
            return None
        ticker_id = self.db.get_or_create_root(ticker)
        for i in range(0, len(data['t'])-1):
            
            data_tuple = (
                ticker_id, 
                self.timestamp_to_datetime(data['t'][i]), 
                data['o'][i], 
                data['h'][i], 
                data['l'][i], 
                data['c'][i], 
                data['v'][i]
            )
            ticker_list.append(data_tuple)

        logger.info(f"Collected {ticker} minute prices for the past {for_the_past_x_days} days for a total of {len(data['t'])}")
        return ticker_list
        
    def get_stocks_daily(self, ticker):
        end_date = date.today()
        date = end_date - (timedelta(365)*10)
        params = {'symbol': ticker, 'interval': 'daily', 'start': date, 'end': end_date, 'session_filter': 'all'}
        response = requests.get(
            HISTORY_URL,
            params=params,
            headers=self.MD_HEADER
        )

        if response. status_code in (200, 203):
            data = response.json()
            if data['history']==None:
                self.logger.info(f'Empty API Return for {ticker} perhaps its mispelled?')
                return
        else:
            self.logger.info(f'Failed to call data: {response.status_code} for url: {params}')
        ticker_id = self.db.get_or_create_root(ticker)

        data_tuples = [
            (
                ticker_id,
                f"{entry['date']} 16:30:00",
                entry["open"],
                entry["high"],
                entry["low"],
                entry["close"],
                entry["volume"]
            )
            for entry in data["history"]["day"]
        ]
        logger.info(f"Collected {ticker} daily prices for a total of {len(data_tuples)} entries")
        self.db.insert_stock_candles(data_tuples)


    def theta_bulk_options(self, params=None):
        """
        Collect historical minute data from ThetaData server. Needed Paramaters include
        
        exp: integer in format YYYYMMDD
        date: integer 
        end_date: integer
        symbol: string
        ivl: integer (in milliseconds)
        """
        selector_list = [
            'eod', 'ohlc', 'quote', 'open_interest' , 'trades', 'trade_quote']
        
        if params['selector'] not in selector_list:
            print(f'selector must be set to either ({selector_list})')
            

        BASE_URL = 'http://127.0.0.1:25503/v3'
        
        paramaters = {'exp': params['exp'], 
                  'date': params['date'],
                  'end_date': params['end_date'],
                  'use_csv': 'false',
                  'symbol': params['symbol'],
                  'ivl':   params['ivl'] 
        }
        
         
        url = BASE_URL + f"/bulk_hist/option/{params['selector']}/'"
        
        data = []

        while url is not None:
            response = httpx.get(url, params=paramaters, timeout=90)
            if response.status_code==200:
                data.append(response.json())
            else:
                return f"Error {response.raise_for_status()}"

            if 'Next-Page' in response.headers and response.headers['Next-Page'] != "null":
                url = response.headers['Next-Page']
                paramaters = None 
            else: 
                url = None
        return data


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


if __name__ == "__main__":

    db = DatabaseConnection.DatabaseConnection()
    data_collector = DataCollector(db)

    # Quick tests for the new function theta_options_quotes

    # Test 1: Basic usage with required parameters
    results = data_collector.theta_options_quotes(
        symbol="AAPL",
        date="20240105"
    )
    print(f"Test 1 - Results count for AAPL 20240105: {len(results)}")

    # Test 2: Range of dates
    results = data_collector.theta_options_quotes(
        symbol="MSFT",
        date="20240103",
        end_date="20240105"
    )
    print(f"Test 2 - Results count for MSFT 20240103-20240105: {len(results)}")

    # Test 3: With specific expiration and strike
    results = data_collector.theta_options_quotes(
        symbol="SPY",
        date="20240102",
        expiration="20240119",
        strike="450",
        right="call"
    )
    print(f"Test 3 - Results count for SPY 20240102 expiration 20240119 strike 450 call: {len(results)}")

    # Test 4: Nonexistent symbol (should handle gracefully)
    results = data_collector.theta_options_quotes(
        symbol="FAKE123",
        date="20240102"
    )
    print(f"Test 4 - Results count for FAKE123: {results}")

    # Test 5: Bad date format (should handle error and return empty or None)
    results = data_collector.theta_options_quotes(
        symbol="AAPL",
        date="bad-date"
    )
    print(f"Test 5 - Results for bad date input: {results}")

