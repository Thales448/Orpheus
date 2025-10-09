import sys
import logging
import os
import pandas as pd
# Your base logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)

# Silence HTTP libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info("🚀 SyntxCharts container started...")
from Charts.DatabaseConnection import DatabaseConnection
import Charts.config as config
from Charts.DataCollector import DataCollector

# Init shared resources
db = DatabaseConnection()
data=DataCollector(db, config)


class SyntxDB():
    def __init__(self):
        self.rqdata = None
        # self.watchlists =  WatchlistLogic()
        self.conn = db
        self.datacollector = data

    def add_equity(self, ticker: str, resolution= "daily", start_time = None, end_time = None):
        
        data = self.conn.get_stock_data(ticker, resolution, start_time, end_time)
        
        if data:
            if len(data) != 0:
                df = pd.DataFrame(data, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
            else:
                return None 
        elif resolution in ["daily", "weekly", "monthly"]:
            try:
                data = self.conn.get_stock_data(ticker, resolution, start_time, end_time)
                if not data or len(data) == 0:
                    # No data in DB; trigger collection, then fetch again
                    self.datacollector.get_stocks_daily(ticker)
                    data = self.conn.get_stock_data(ticker, resolution, start_time, end_time)
            except Exception as e:
                # If DB query fails for any reason, try to populate and fetch again
                print(f"DB fetch error for {ticker} ({resolution}): {e}")
                self.datacollector.get_stocks_daily(ticker)
                data = self.conn.get_stock_data(ticker, resolution, start_time, end_time)

        
        elif resolution in ["1m", "5m", "10m", "15m", "30m", "minute", "hourly"]:
            try:
                # 1. Try to fetch data from the database
                data = self.conn.get_stock_data(ticker, resolution, start_time, end_time)
                if not data or len(data) == 0:
                    # No data found: trigger data collection, then retry
                    self.datacollector.get_stocks_minute(ticker)
                    data = self.conn.get_stock_data(ticker, resolution, start_time, end_time)
            except Exception as e:
                # Optional: log error for unexpected exceptions
                print(f"DB fetch error for {ticker}: {e}")
                # 2. On failure, try to collect and fetch again
                self.datacollector.get_stocks_minute(ticker)
                data = self.conn.get_stock_data(ticker, resolution, start_time, end_time)

        
        df = pd.DataFrame(data, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df["Time"]=pd.to_datetime(df["Time"],format='%d.%m.%Y %H:%M:%S')
        df.set_index("Time", inplace=True)
        df["Close"] = df["Close"].astype(float)
        df["Open"] = df["Open"].astype(float)
        df["High"] = df["High"].astype(float)
        df["Low"] = df["Low"].astype(float)
        df["Volume"] = df["Volume"].astype(float)


        return df

    def add_crypto(self, coin: str, resolution = "daily"):
        data = self.conn.get_crypto_data(coin, resolution)
        return pd.DataFrame(data, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])

    def add_chain(self, ticker, expiration=None, start_time=None, end_time=None, interval=None, side=None):
        data = self.conn.get_option_chain(ticker, expiration, start_time, end_time,interval,side)
        return data
    
    
def print_help():
    print("""
📘 Syntx Function Runner Help

Usage:
  docker run --rm thales884/charts:latest "function_name(param1, param2, ...)"
  or set EXEC_CODE env variable for dynamic execution
          
Available functions:

  populate_options(ticker: str, start_date: int, end_date: int, interval: int)
    - Fetches and stores option quotes for a ticker between two dates.

  populate_stocks(ticker: str, days: int)
    - Fetches minute-level stock OHLCV data for the last N days.

  -h, --help
    - Shows this help menu.

""")

def populate_options(ticker, start_date, end_date, interval):
    if not isinstance(ticker, str) or not ticker.isalpha():
        print("❌ Error: 'ticker' must be a valid string (e.g. 'SPY').")
        return
    if not isinstance(start_date, int) or not isinstance(end_date, int):
        print("❌ Error: 'start_date' and 'end_date' must be integers in YYYYMMDD format.")
        return
    if start_date >= end_date:
        print("❌ Error: 'start_date' must be earlier than 'end_date'.")
        return

    try:
        f.populate_options(ticker, start_date, end_date, interval)
        print(f"✅ Options collected for {ticker}")
    except Exception as e:
        print(f"❌ Failed to collect options for {ticker}: {e}")

def populate_stocks(ticker):
    if not isinstance(ticker, str) or not ticker.isalpha():
        print("❌ Error: 'ticker' must be a valid string (e.g. 'SPY').")
        return  

    try:
        data.get_stocks_minute(ticker)
        print(f"✅ Collected 245 days of minute stock data for {ticker}")
    except Exception as e:
        print(f"❌ Failed to collect stocks for {ticker}: {e}")


if __name__ == "__main__":
    exec_code = os.environ.get("EXEC_CODE")

    if exec_code:
        try:
            exec(exec_code)
        except Exception as e:
            print(f"❌ Error executing EXEC_CODE: {e}")
    elif len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print_help()
    else:
        try:
            eval(sys.argv[1])
        except Exception as e:
            print(f"❌ Error evaluating command: {e}")
            print("   Run with -h to see available commands and usage.")