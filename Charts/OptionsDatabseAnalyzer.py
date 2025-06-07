import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

class OptionsDatabaseAnalyzer:
    def __init__(self, connection):
        self.connection = connection

    def log(self, msg):
        print(f"[{datetime.now()}] {msg}")

    def run_macro_analysis(self, ticker):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT id FROM options.tickers WHERE ticker = %s", (ticker,))
                ticker_row = cursor.fetchone()
                if not ticker_row:
                    self.log(f"❌ Ticker '{ticker}' not found.")
                    return None, None
                ticker_id = ticker_row[0]

                cursor.execute("""
                    SELECT id, expiration, strike, side
                    FROM options.contracts
                    WHERE ticker_id = %s
                """, (ticker_id,))
                contracts = cursor.fetchall()
                df_contracts = pd.DataFrame(contracts, columns=['id', 'expiration', 'strike', 'side'])
                self.log(f"📊 Total contracts: {len(df_contracts)}")
                # Convert expiration ints (e.g. 20250425) to datetime
                df_contracts['expiration_dt'] = pd.to_datetime(df_contracts['expiration'].astype(str), format="%Y%m%d", errors="coerce")
                self.log(f"📅 Expiration range: {df_contracts['expiration_dt'].min()} → {df_contracts['expiration_dt'].max()}")

                # Macro stats: contracts per year/month/week
                chains_per_year = df_contracts['expiration_dt'].dt.year.value_counts().sort_index()
                chains_per_month = df_contracts['expiration_dt'].dt.to_period('M').value_counts().sort_index()
                chains_per_week = df_contracts['expiration_dt'].dt.to_period('W').value_counts().sort_index()
                self.log("📈 Chains per year:\n" + chains_per_year.to_string())
                self.log("📈 Chains per month:\n" + chains_per_month.to_string())
                self.log("📈 Chains per week:\n" + chains_per_week.to_string())

                # Calls/Puts count
                side_counts = df_contracts['side'].value_counts().to_dict()
                self.log(f"🟦 Calls: {side_counts.get('C',0)}   🟥 Puts: {side_counts.get('P',0)}")

                # Strike histogram
                plt.figure(figsize=(12,6))
                sns.histplot(data=df_contracts, x='strike', hue='side', multiple='stack', bins=50)
                plt.title(f"{ticker} - Strike Distribution Across All Expirations")
                plt.xlabel("Strike")
                plt.ylabel("Number of Contracts")
                plt.savefig(f"{ticker}_strike_histogram.png")
                plt.close()
                self.log(f"📈 Strike histogram saved as {ticker}_strike_histogram.png")

                # Heatmap: contracts by expiration × strike
                heatmap_data = df_contracts.pivot_table(index='expiration_dt', columns='strike', values='id', aggfunc='count', fill_value=0)
                plt.figure(figsize=(16, 8))
                sns.heatmap(heatmap_data, cmap='YlGnBu')
                plt.title(f"{ticker} Contract Heatmap (Expiration x Strike)")
                plt.xlabel("Strike")
                plt.ylabel("Expiration")
                plt.tight_layout()
                plt.savefig(f"{ticker}_contract_heatmap.png")
                plt.close()
                self.log(f"📈 Contract heatmap saved as {ticker}_contract_heatmap.png")

                # Quote coverage per contract
                cursor.execute(f"SELECT contract_id, COUNT(*) FROM options.quotes WHERE contract_id = ANY(%s) GROUP BY contract_id", (list(df_contracts['id']),))
                quote_counts = cursor.fetchall()
                quote_count_dict = {cid: cnt for cid, cnt in quote_counts}
                df_contracts['quote_count'] = df_contracts['id'].map(quote_count_dict).fillna(0).astype(int)
                self.log(f"📥 Quote stats: min={df_contracts['quote_count'].min()}, max={df_contracts['quote_count'].max()}, mean={df_contracts['quote_count'].mean():.2f}")

                plt.figure(figsize=(10,4))
                plt.hist(df_contracts['quote_count'], bins=50, color='green', alpha=0.7)
                plt.title(f"{ticker} Quote Count per Contract")
                plt.xlabel("Quotes per Contract")
                plt.ylabel("Number of Contracts")
                plt.tight_layout()
                plt.savefig(f"{ticker}_quote_count_histogram.png")
                plt.close()
                self.log(f"📊 Quote count histogram saved as {ticker}_quote_count_histogram.png")

                cursor.execute("SELECT COUNT(*) FROM options.quotes")
                total_quotes = cursor.fetchone()[0]
                self.log(f"📥 Total option quotes in DB: {total_quotes}")

                cursor.execute("SELECT MIN(time), MAX(time) FROM options.quotes")
                time_bounds = cursor.fetchone()
                self.log(f"🕒 Quote time range: {time_bounds[0]} → {time_bounds[1]}")

                # Build API-like summary result
                summary = {
                    "ticker": ticker,
                    "total_contracts": int(len(df_contracts)),
                    "calls": int(side_counts.get('C',0)),
                    "puts": int(side_counts.get('P',0)),
                    "expiration_range": [str(df_contracts['expiration_dt'].min()), str(df_contracts['expiration_dt'].max())],
                    "chains_per_year": chains_per_year.to_dict(),
                    "chains_per_month": {str(k): int(v) for k,v in chains_per_month.items()},
                    "strike_stats": {
                        "min": float(df_contracts['strike'].min()),
                        "max": float(df_contracts['strike'].max()),
                        "mean": float(df_contracts['strike'].mean()),
                        "median": float(df_contracts['strike'].median())
                    },
                    "quote_stats": {
                        "min": int(df_contracts['quote_count'].min()),
                        "max": int(df_contracts['quote_count'].max()),
                        "mean": float(df_contracts['quote_count'].mean()),
                        "median": float(df_contracts['quote_count'].median()),
                        "total_quotes": int(total_quotes)
                    },
                    "quote_time_bounds": [str(time_bounds[0]), str(time_bounds[1])]
                }
                return df_contracts, summary

        except Exception as e:
            self.log(f"❌ Error during macro analysis: {e}")
            return None, None

    def run_micro_analysis(self, df_contracts, sample_pct=0.2, max_contracts=50):
        sampled_contracts = df_contracts.sample(frac=sample_pct, random_state=42).head(max_contracts)
        contract_analysis = []
        try:
            for _, row in sampled_contracts.iterrows():
                contract_id = row['id']
                cursor = self.connection.cursor()
                cursor.execute("""
                    SELECT time, bid, ask, bid_size, ask_size
                    FROM options.quotes
                    WHERE contract_id = %s
                    ORDER BY time ASC
                """, (contract_id,))
                data = cursor.fetchall()
                if not data:
                    self.log(f"⚠️ No quote data for contract {contract_id}")
                    continue

                df_quotes = pd.DataFrame(data, columns=['time', 'bid', 'ask', 'bid_size', 'ask_size'])
                df_quotes['time'] = pd.to_datetime(df_quotes['time'], utc=True)  # Use UTC for all times

                # Count data quality issues
                n_total = len(df_quotes)
                n_zero_bid = (df_quotes['bid'] == 0).sum()
                n_zero_ask = (df_quotes['ask'] == 0).sum()
                n_zero_both = ((df_quotes['bid'] == 0) & (df_quotes['ask'] == 0)).sum()
                self.log(f"Contract {contract_id} - total: {n_total}, zero bid: {n_zero_bid}, zero ask: {n_zero_ask}, zero both: {n_zero_both}")

                # Filter: keep only rows where BOTH bid and ask are > 0
                df_quotes_valid = df_quotes[(df_quotes['bid'] > 0) & (df_quotes['ask'] > 0)].copy()
                if df_quotes_valid.empty:
                    self.log(f"⚠️ No valid bid/ask pairs for contract {contract_id} after filtering zeros.")
                    continue

                df_quotes_valid['mid'] = (df_quotes_valid['bid'] + df_quotes_valid['ask']) / 2
                df_quotes_valid['spread'] = df_quotes_valid['ask'] - df_quotes_valid['bid']
                df_quotes_valid['mid_change'] = df_quotes_valid['mid'].diff().abs()
                df_quotes_valid['gap'] = df_quotes_valid['time'].diff().dt.total_seconds().fillna(0)

                # Large gaps or holes (e.g., missing ticks)
                expected_interval = df_quotes_valid['gap'].median() if len(df_quotes_valid['gap']) > 2 else 60
                large_gaps = df_quotes_valid[df_quotes_valid['gap'] > expected_interval * 2]

                # Price spikes and wide spreads
                large_spikes = df_quotes_valid[df_quotes_valid['mid_change'] > df_quotes_valid['mid'].median() * 10]
                wide_spreads = df_quotes_valid[df_quotes_valid['spread'] > df_quotes_valid['spread'].median() * 5]

                # Plot: valid points only
                plt.figure(figsize=(14, 4))
                plt.plot(df_quotes_valid['time'], df_quotes_valid['mid'], label='Mid Price', color='blue')
                plt.title(f"Contract {contract_id} Mid Price")
                plt.xlabel("Time")
                plt.ylabel("Price")
                plt.grid(True)
                plt.tight_layout()
                plt.savefig(f"contract_{contract_id}_price_chart.png")
                plt.close()

                # Optional: also plot bid/ask for diagnostics
                plt.figure(figsize=(14, 4))
                plt.plot(df_quotes['time'], df_quotes['bid'], label='Bid', color='red', alpha=0.6)
                plt.plot(df_quotes['time'], df_quotes['ask'], label='Ask', color='green', alpha=0.6)
                plt.legend()
                plt.title(f"Contract {contract_id} Bid/Ask Over Time")
                plt.xlabel("Time")
                plt.ylabel("Price")
                plt.tight_layout()
                plt.savefig(f"contract_{contract_id}_bidask_chart.png")
                plt.close()

                contract_result = {
                    "contract_id": int(contract_id),
                    "n_ticks": int(len(df_quotes_valid)),
                    "first_tick": str(df_quotes_valid['time'].min()),
                    "last_tick": str(df_quotes_valid['time'].max()),
                    "large_gap_count": int(len(large_gaps)),
                    "large_spike_count": int(len(large_spikes)),
                    "wide_spread_count": int(len(wide_spreads)),
                    "sample_large_gaps": large_gaps[['time','gap']].head(5).to_dict('records'),
                    "sample_spikes": large_spikes[['time','mid_change']].head(5).to_dict('records'),
                    "sample_wide_spreads": wide_spreads[['time','spread']].head(5).to_dict('records'),
                    "chart_file": f"contract_{contract_id}_price_chart.png"
                }
                self.log(f"🔬 Contract {contract_id}: {contract_result}")
                contract_analysis.append(contract_result)

            return contract_analysis
        except Exception as e:
            self.log(f"❌ Error during micro analysis: {e}")
            return []

# Example usage:
if __name__ == "__main__":
    conn = psycopg2.connect(
        host="192.168.1.149",
        port=35432,
        user="syntxdb-super",
        password="wucpeH32621",  # <--- replace with your real password
        dbname="historical"
    )
    analyzer = OptionsDatabaseAnalyzer(conn)
    df_contracts, summary = analyzer.run_macro_analysis("SPXS")
    if df_contracts is not None:
        contract_analyses = analyzer.run_micro_analysis(df_contracts)
        api_result = {
            "macro_summary": summary,
            "micro_details": contract_analyses
        }
        print(api_result)
