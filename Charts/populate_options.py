
def populate_options(ticker, start_date, end_date, interval):
    import httpx
    import argparse 
    import time
    import os
    import logging
    from datetime import datetime, timedelta

    API_QUOTES_URL = "http://192.168.1.138:25510/v2/bulk_hist/option/quote"
    API_EXPIRATIONS_URL = "http://192.168.1.138:25510/v2/list/expirations"
    RETRIES = 3
    RETRY_DELAY = 5 
    
    def build_date_windows(expiration, start_date_bound=None, end_date_bound=None):
        expiration_date = datetime.strptime(str(expiration), "%Y%m%d")
        start_date = expiration_date - timedelta(days=210)
        if start_date_bound:
            start_date = max(start_date, datetime.strptime(start_date_bound, "%Y%m%d"))
        end_cutoff = expiration_date - timedelta(days=1)
        if end_date_bound:
            end_cutoff = min(end_cutoff, datetime.strptime(end_date_bound, "%Y%m%d"))

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

    def runmain(ticker, start_date, end_date, resolution):
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
                        contract_id = self.get_or_create_contract(contract_meta)

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
                        db.insert_option_quotes(rows)
                    logger.info(f"[{ticker} {expiration}] ✅ Finished {window_start}–{window_end}")
                except Exception as e:
                    logger.exception(f"[{ticker} {expiration}] ❌ Error for window {window_start}–{window_end}: {e}")

    runmain(ticker, start_date, end_date, interval)