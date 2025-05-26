import sys
import logging
import os
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
from conn import DatabaseConnection
import config
from datacollector import DataCollector

# Init shared resources
db = DatabaseConnection()
data=DataCollector(db, config)

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

def test(a, b):
    print(f"Test function called with arguments: {a}, {b}")
    return a + b

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
        data.populate_options(ticker, start_date, end_date, interval)
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