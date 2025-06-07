
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import random

class OptionsDatabaseAnalyzer:
    def __init__(self, connection):
        self.connection = connection

    def log(self, msg):
        print(f"[{datetime.now()}] {msg}")

    # --- 1. Utilities for querying contracts, expirations, strikes

    def list_contracts(self, ticker, expiration=None, strike=None, side=None):
        """
        List all contracts for a ticker, optionally filtered by expiration, strike, or side (C/P).
        """
        query = "SELECT id, expiration, strike, side FROM options.contracts WHERE ticker_id = (SELECT id FROM options.tickers WHERE ticker = %s)"
        params = [ticker]
        if expiration:
            query += " AND expiration = %s"
            params.append(expiration)
        if strike:
            query += " AND strike = %s"
            params.append(strike)
        if side:
            query += " AND side = %s"
            params.append(side)
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            contracts = cursor.fetchall()
        # Format result
        contract_list = [
            {"contract_id": row[0], "expiration": row[1], "strike": float(row[2]), "side": row[3]}
            for row in contracts
        ]
        return contract_list

    def get_expirations(self, ticker):
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT expiration FROM options.contracts WHERE ticker_id = (SELECT id FROM options.tickers WHERE ticker = %s)",
                (ticker,))
            exps = sorted([int(x[0]) for x in cursor.fetchall()])
        return exps

    def get_strikes(self, ticker, expiration=None):
        query = "SELECT DISTINCT strike FROM options.contracts WHERE ticker_id = (SELECT id FROM options.tickers WHERE ticker = %s)"
        params = [ticker]
        if expiration:
            query += " AND expiration = %s"
            params.append(expiration)
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            strikes = sorted([float(x[0]) for x in cursor.fetchall()])
        return strikes

    # --- 2. Zoom and windowing for contract quotes

    def get_contract_quotes(self, contract_id, start_time=None, end_time=None):
        """
        Retrieve quotes for a contract, optionally within a time window.
        Returns a DataFrame.
        """
        query = "SELECT time, bid, ask, bid_size, ask_size FROM options.quotes WHERE contract_id = %s"
        params = [contract_id]
        if start_time:
            query += " AND time >= %s"
            params.append(start_time)
        if end_time:
            query += " AND time <= %s"
            params.append(end_time)
        query += " ORDER BY time ASC"
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            data = cursor.fetchall()
        df = pd.DataFrame(data, columns=['time', 'bid', 'ask', 'bid_size', 'ask_size'])
        df['time'] = pd.to_datetime(df['time'], utc=True)
        return df

    # --- 3. Interactive plotting for dashboard/zoom

    def plot_contract(self, contract_id, start_time=None, end_time=None, granularity="minute", output_prefix=None):
        """
        Plot bid, ask, and mid for a contract in a given time window.
        - granularity: "minute", "hour", "day" (for dashboard toggles)
        """
        df = self.get_contract_quotes(contract_id, start_time, end_time)
        # Filter: only keep where BOTH bid and ask > 0
        df = df[(df['bid'] > 0) & (df['ask'] > 0)].copy()
        if df.empty:
            self.log(f"⚠️ No valid quotes to plot for contract {contract_id} in selected window.")
            return None

        df['mid'] = (df['bid'] + df['ask']) / 2
        # Optionally resample (useful for large datasets and "minute"/"hour"/"day" views)
        if granularity != "minute":
            rule = {"hour": "H", "day": "D"}[granularity]
            df = df.resample(rule, on='time').agg({'bid':'mean', 'ask':'mean', 'mid':'mean'}).dropna().reset_index()
        # Plot
        plt.figure(figsize=(12,4))
        plt.plot(df['time'], df['bid'], label='Bid', color='red', alpha=0.6)
        plt.plot(df['time'], df['ask'], label='Ask', color='green', alpha=0.6)
        plt.plot(df['time'], df['mid'], label='Mid', color='blue')
        plt.legend()
        plt.title(f"Contract {contract_id} Quotes: {granularity.capitalize()} View")
        plt.xlabel("Time")
        plt.ylabel("Price")
        plt.tight_layout()
        fname = f"{output_prefix or contract_id}_quotes_{granularity}.png"
        plt.savefig(fname)
        plt.close()
        self.log(f"🖼️ Saved plot {fname}")
        return fname

    # --- 4. Random contract for spot check
    def random_contract_id(self, ticker, expiration=None):
        contracts = self.list_contracts(ticker, expiration)
        if not contracts:
            return None
        return random.choice(contracts)['contract_id']

    # --- 5. Zoom window helpers
    def window_for_contract(self, contract_id, period="day", which="first"):
        """
        Get start/end time for a given contract's first/last day/week.
        """
        df = self.get_contract_quotes(contract_id)
        if df.empty:
            return None, None
        if period == "day":
            day = df['time'].min().date() if which=="first" else df['time'].max().date()
            start = pd.Timestamp(f"{day} 00:00:00", tz='UTC')
            end = pd.Timestamp(f"{day} 23:59:59", tz='UTC')
        elif period == "week":
            base = df['time'].min() if which=="first" else df['time'].max()
            start = base - pd.Timedelta(days=base.weekday())
            end = start + pd.Timedelta(days=6, hours=23, minutes=59, seconds=59)
        else:
            # full contract history
            start, end = df['time'].min(), df['time'].max()
        return start, end

    # --- 6. API/JSON for dashboard integration
    def contract_overview_json(self, contract_id):
        """
        Returns all info needed for the dashboard for a contract:
        - Contract meta
        - Available time range
        - Data quality stats
        """
        df = self.get_contract_quotes(contract_id)
        n_total = len(df)
        n_zero_bid = (df['bid'] == 0).sum()
        n_zero_ask = (df['ask'] == 0).sum()
        n_zero_both = ((df['bid'] == 0) & (df['ask'] == 0)).sum()
        df_valid = df[(df['bid'] > 0) & (df['ask'] > 0)]
        meta = {"contract_id": contract_id,
                "n_quotes": int(n_total),
                "first_tick": str(df['time'].min()) if not df.empty else None,
                "last_tick": str(df['time'].max()) if not df.empty else None,
                "n_valid": int(len(df_valid)),
                "n_zero_bid": int(n_zero_bid),
                "n_zero_ask": int(n_zero_ask),
                "n_zero_both": int(n_zero_both),
                "valid_pct": float(len(df_valid)) / n_total if n_total > 0 else 0
                }
        return meta

# ---- Example: API/Backend Endpoints ----
# - /contracts?ticker=SPXS               (lists contracts/expirations/strikes/sides)
# - /contract?id=154315                  (returns meta/info for contract)
# - /contract/plot?id=154315&granularity=day&start=2024-04-15&end=2024-04-17
# - /contract/random?ticker=SPXS         (returns a random contract ID for spot-check)
# - /contract/zoom?id=154315&period=day&which=first

# ---- Example Usage ----
if __name__ == "__main__":
    conn = psycopg2.connect(
        host="192.168.1.149",
        port=35432,
        user="syntxdb-super",
        password="wucpeH32621",  # <--- replace with your real password
        dbname="historical",
    )
    analyzer = OptionsDatabaseAnalyzer(conn)
    # 1. List contracts for a ticker and expiration
    contracts = analyzer.list_contracts("SPXS")
    print("First 5 contracts:", contracts[:5])

    # 2. Random contract, zoom in on first day
    cid = analyzer.random_contract_id("SPXS")
    start, end = analyzer.window_for_contract(cid, period="day", which="first")
    analyzer.plot_contract(cid, start_time=start, end_time=end, granularity="minute", output_prefix=f"{cid}_day1")
    # 3. Get dashboard JSON
    print(analyzer.contract_overview_json(cid))
