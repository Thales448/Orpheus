import requests
import psycopg2
import datetime
from datetime import timedelta, date
import pytz
from psycopg2 import sql
from psycopg2.extras import execute_values
import logging
import Charts.config
from Charts.conn import DatabaseConnection
import httpx

logger = logging.getLogger(__name__)

class DataCollector():
    """
    This Class connects multiple providers of data into one object
    """
    def __init__(self, db, config):
        self.db = db
        self.config = config
        self.logger = logger
    def collect_expiration_dates(self, paramaters):
        """
        Paramaters needed: 
        
        "root":string

        """

        url = 'http://127.0.0.1:25510/v2/list/expirations'

        while url is not None:
            response = httpx.get(url, params=paramaters, timeout=60)  # make the request
            response.raise_for_status() 

            if 'Next-Page' in response.headers and response.headers['Next-Page'] != "null":
                url = response.headers['Next-Page']
                params = None
            else:
                url = None
        try:
            
            return response.json()['response']
        except Exception as e:
            # Optionally log the error
            return None

    def populate_options(self, ticker, start_date, end_date, interval):
        import httpx

        import time
        from datetime import datetime, timedelta

        API_QUOTES_URL = "http://192.168.1.138:25510/v2/bulk_hist/option/quote"
        API_EXPIRATIONS_URL = "http://192.168.1.138:25510/v2/list/expirations"
        RETRIES = 3
        RETRY_DELAY = 5 
        
        def build_date_windows(expiration, start_date_bound=None, end_date_bound=None):
            try:
                expiration_str = str(expiration)
                expiration_date = datetime.strptime(expiration_str, "%Y%m%d")
            except Exception as e:
                raise ValueError(f"❌ Invalid expiration '{expiration}': {e}")

            # Default range: 210 days before expiration to 1 day before expiration
            start_date = expiration_date - timedelta(days=210)
            end_cutoff = expiration_date - timedelta(days=1)

            # Apply bounds if provided
            if start_date_bound:
                try:
                    start_date_str = str(start_date_bound)
                    start_date = max(start_date, datetime.strptime(start_date_str, "%Y%m%d"))
                except Exception as e:
                    raise ValueError(f"❌ Invalid start_date_bound '{start_date_bound}': {e}")

            if end_date_bound:
                try:
                    end_date_str = str(end_date_bound)
                    end_cutoff = min(end_cutoff, datetime.strptime(end_date_str, "%Y%m%d"))
                except Exception as e:
                    raise ValueError(f"❌ Invalid end_date_bound '{end_date_bound}': {e}")

            # Build windows
            windows = []
            current_day = start_date
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

        def runmain(ticker, start_date, end_date, interval):
            try:
                response = safe_http_get(API_EXPIRATIONS_URL, params={"root": ticker})
                if response is None:
                    logger.info(f"[{ticker}] ⚠️ Skipping due to 472 response")
                    return
                expirations = response.json().get('response', [])
                filtered_expirations = [e for e in expirations if int(start_date) <= e <= int(end_date)]
            except Exception as e:
                logger.exception(f"[{ticker}] ❌ Error fetching expirations: {e}")
                return

            for expiration in filtered_expirations:
                windows = build_date_windows(expiration, start_date_bound=start_date, end_date_bound=end_date)
                for window_start, window_end in windows:
                    params = {
                        'root': ticker,
                        'exp': expiration,
                        'start_date': window_start,
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
                                'root': contract_info["root"],
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

        runmain(ticker, start_date, end_date, interval)


    def get_options_chains(self,ticker):

        self.db.archive_options(ticker)
        expiry_list = self.collect_expiration_dates(ticker)
        if expiry_list == None:
            logger.error(f"API returned no contracts for {ticker}")
            return None
        l = []
        current_time = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")

        for expiration in expiry_list:
            chains = requests.get(
                config.OPTIONS_URL,
                params={'symbol': ticker, 'expiration': expiration, 'greeks': 'true'},
                headers=self.config.HEADERS
            )
            
            if chains.status_code == 200:
                chain_json = chains.json()  # Attempt to parse JSON
                if chain_json == None:
                    self.logger.info(f"Failed to call option data for {ticker}")
                options = chain_json['options']['option']

                for option in options:
                    
                    def get_greek(option, key):
                        try:
                            return option["greeks"][key]
                        except (KeyError, TypeError):
                            return None

                    option_tuple = (
                    option.get("underlying", None),
                    option.get("symbol", None),
                    option.get("description", None),
                    option.get("strike", None),
                    option.get("bid", None),
                    option.get("ask", None),
                    option.get("volume", None),
                    option.get("option_type", None),
                    option.get("expiration_date", None),  
                    option.get("last_volume", None),
                    get_greek(option, "delta"),
                    get_greek(option, "gamma"),
                    get_greek(option, "theta"),
                    get_greek(option, "vega"),
                    get_greek(option, "rho"),
                    get_greek(option, "mid_iv"),
                    current_time  
                )

                    l.append(option_tuple)
            else:
                self.logger.info(f"Failed to call option data for {ticker}")

        self.db.insert_option_data(l)

    def timestamp_to_datetime(self, timestamp):
        etz = pytz.timezone('US/Eastern')
        utc_time = datetime.datetime.fromtimestamp(timestamp, pytz.utc)
        eastern_timestamp = utc_time.astimezone(etz)
        return eastern_timestamp.strftime('%Y-%m-%d %H:%M:%S')

    def get_stocks_minute(self, ticker, for_the_past_x_days = 245):

        end_date = date.today()
        start_date = end_date - (timedelta(for_the_past_x_days))
        url = f'https://api.marketdata.app/v1/stocks/candles/minutely/{ticker}/?from={start_date}&to={end_date}'

        ticker_list = []
        response = requests.get(
            url, 
            headers=self.config.MD_HEADER
        )

        if response.status_code in (200, 203):
            data = response.json()
        else:
            logger.info(f'Failed API call for {ticker} minute stock: {response.status_code} for url: {url}')
            return None

        for i in range(0, len(data['t'])-1):
            
            data_tuple = (
                ticker, 
                self.timestamp_to_datetime(data['t'][i]), 
                data['o'][i], 
                data['h'][i], 
                data['l'][i], 
                data['c'][i], 
                data['v'][i]
            )
            ticker_list.append(data_tuple)

        logger.info(f"Collected {ticker} minute prices for the past {for_the_past_x_days} days for a total of {len(data['t'])}")
        self.db.insert_stock_minute(ticker_list)

    def get_stocks_10year_daily(self, ticker):
        end_date = date.today()
        start_date = end_date - (timedelta(365)*10)
        
        response = requests.get(
            self.config.HISTORY_URL,
            params=  {'symbol': ticker, 'interval': 'daily', 'start': start_date, 'end': end_date, 'session_filter': 'all'},
            headers=self.config.HEADERS
            )

        if response. status_code in (200, 203):
            data = response.json()
            if data['history']==None:
                self.logger.info(f'Empty API Return for {ticker} perhaps its mispelled?')
                return
        else:
            self.logger.info(f'Failed to call data: {response.status_code} for url: {url}')

        data_tuples = [
            (
                ticker,
                entry["date"],
                entry["open"],
                entry["high"],
                entry["low"],
                entry["close"],
                entry["volume"]
            )
            for entry in data["history"]["day"]
        ]
        self.db.insert_stock_daily(data_tuples)

    def update_stocks_quote(self, ticker):

        end_date = date.today()
        start_date = end_date - (timedelta(1))

        url = f'https://api.marketdata.app/v1/stocks/quotes/{ticker}/'

        response = requests.get(url, headers=self.config.MD_HEADER)
        current_time = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")

        if response.status_code in (200, 203):
            data = response.json()
        else:
           self.logger.error(f'Failed to retrieve data for url: {url}')

        data_tuple = (
        ticker, 
        data['ask'][0],
        data['askSize'][0],
        data['bid'][0],
        data['bidSize'][0],
        data['mid'][0],
        data['last'][0],
        data['volume'][0],
        current_time
        )
        
        self.logger.info(f"Collected {ticker} quotes succesfully")
        self.db.insert_stocks_realtime(data_tuple)

    def theta_bulk_options(self, params=None):
        """
        Collect historical minute data from ThetaData server. Needed Paramaters include
        
        exp: integer in format YYYYMMDD
        start_date: integer 
        end_date: integer
        root: string
        ivl: integer (in milliseconds)
        """
        selector_list = [
            'eod', 'ohlc', 'quote', 'open_interest' , 'trades', 'trade_quote']
        
        if params['selector'] not in selector_list:
            print(f'selector must be set to either ({selector_list})')
            

        BASE_URL = 'http://127.0.0.1:25510/v2'
        
        paramaters = {'exp': params['exp'], 
                  'start_date': params['start_date'],
                  'end_date': params['end_date'],
                  'use_csv': 'false',
                  'root': params['root'],
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

    def theta_bulk_greeks(self, params=None):
        return

    def theta_stocks_quote(self, 
                        ticker: str,
                        start_date: str,
                        end_date: str,
                        ivl: int = 0,
                        use_csv: bool = True,
                        pretty_time: bool = False,
                        rth: bool = True,
                        start_time: str = None,
                        end_time: str = None,
                        venue: str = "nqb") -> list[dict]:
        """
        Fetches NBBO quote data for a given ticker using the Theta Terminal API.

        Parameters:
        - ticker (str): The stock symbol (e.g., 'AAPL').
        - start_date (str): Start date in YYYYMMDD format (e.g., '20240401').
        - end_date (str): End date in YYYYMMDD format.
        - ivl (int): Interval in milliseconds (e.g., 60000 for 1-minute). Use 0 for tick-level data.
        - use_csv (bool): If True, use CSV format. If False, use JSON (legacy).
        - pretty_time (bool): If True, returns human-readable timestamps (overrides ms).
        - rth (bool): If True, limits to regular trading hours (09:30–16:00 ET).
        - start_time (str): Milliseconds since midnight to start (optional, e.g., '34200000').
        - end_time (str): Milliseconds since midnight to end (optional).
        - venue (str): Market feed ('nqb' = Nasdaq Basic, 'utp_cta' = consolidated).

        Returns:
        - List of dictionaries with quote data. Each dictionary includes:
        ['symbol', 'timestamp', 'bid_size', 'bid_exchange', 'bid', 'bid_condition',
        'ask_size', 'ask_exchange', 'ask', 'ask_condition', 'date']
        """

        base_url = "http://127.0.0.1:25510/v2/hist/stock/quote"

        params = {
            "root": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "ivl": ivl,
            "use_csv": use_csv,
            "pretty_time": pretty_time,
            "rth": rth,
            "venue": venue
        }

        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        try:
            response = requests.get(base_url, params=params, timeout=15)
            response.raise_for_status()
        except Exception as e:
            self.logger.error(f"❌ Failed to fetch NBBO quote for {ticker}: {e}")
            return []

        rows = response.text.strip().split("\n")
        if not rows:
            self.logger.warning(f"⚠ No data returned for {ticker}")
            return []

        records = []
        for row in rows:
            fields = row.split(",")
            if len(fields) != 10:
                continue
            ms_of_day, bid_size, bid_ex, bid, bid_cond, ask_size, ask_ex, ask, ask_cond, date_str = fields
            try:
                timestamp = datetime.strptime(date_str, "%Y%m%d") + timedelta(milliseconds=int(ms_of_day))
                record = {
                    "symbol": ticker,
                    "timestamp": timestamp,
                    "bid_size": int(bid_size),
                    "bid_exchange": int(bid_ex),
                    "bid": float(bid),
                    "bid_condition": int(bid_cond),
                    "ask_size": int(ask_size),
                    "ask_exchange": int(ask_ex),
                    "ask": float(ask),
                    "ask_condition": int(ask_cond),
                    "date": int(date_str)
                }
                records.append(record)
            except Exception as e:
                self.logger.warning(f"⚠ Could not parse row: {row} -> {e}")

        return records
