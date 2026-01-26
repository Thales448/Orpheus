"""
StreamSimulator: Simulated real-time trade streaming engine for development/testing.

How to Use
----------
This script acts as a mock backend and streams trade-style JSON messages to stdout or over a WebSocket server every millisecond.
You can pipe its output to any consumer (for local CLI testing), or enable the websocket server for integration.

CLI Usage:
    python StreamSimulator.py --root AAPL --start_price 420 --interval_ms 1

Options:
    --root         Stock root symbol (default: AAPL)
    --date         YYYYMMDD (defaults to today)
    --start_price  Initial price (default: 100.0)
    --size         Max random trade size (default: 100)
    --exchange     Exchange code (default: 57)
    --interval_ms  Milliseconds between messages (default: 1)
    --no_json      Don't print to stdout
    --websocket    Enable WebSocket server mode (default port 8765)
    --ws_port      WebSocket port (default: 8765)

To connect as a consumer in your development environment:
    1. For CLI testing: `python StreamSimulator.py | <your_consumer>`
    2. For real websocket integration:
        - Start the server: `python StreamSimulator.py --websocket`
        - In your dev app set WEBSOCKET_URL=ws://localhost:8765/v1/events

--------------

"""

import asyncio
import random
import json
import argparse
from datetime import datetime, timedelta

try:
    import websockets
except ImportError:
    websockets = None

def random_walk_price(last_price, min_move=0.01, max_move=0.10):
    move = random.uniform(min_move, max_move) * random.choice([-1, 1])
    return max(0.01, round(last_price + move, 4))

async def stream_trades_to_stdout(
    root, date, start_price, base_size, exchange, interval_ms, show_json
):
    ms_of_day = 0
    sequence = 1
    last_price = start_price
    day_length_ms = 24 * 60 * 60 * 1000

    try:
        while True:
            ms_of_day = (ms_of_day + interval_ms) % day_length_ms
            if ms_of_day == 0 and sequence > 1:
                date_dt = datetime.strptime(str(date), "%Y%m%d")
                date_dt += timedelta(days=1)
                date = int(date_dt.strftime("%Y%m%d"))
            price = random_walk_price(last_price)
            last_price = price
            size = random.randint(1, base_size)
            trade_msg = {
                "header": {"type": "TRADE", "status": "CONNECTED"},
                "contract": {"security_type": "STOCK", "root": root},
                "trade": {
                    "ms_of_day": ms_of_day,
                    "sequence": sequence,
                    "size": size,
                    "condition": random.choice([0,1,2,4]),
                    "price": price,
                    "exchange": exchange,
                    "date": date
                }
            }
            sequence += 1
            if show_json:
                print(json.dumps(trade_msg, separators=(',', ':')), flush=True)
            await asyncio.sleep(interval_ms / 1000.0)
    except KeyboardInterrupt:
        print("\nStream stopped.")

async def stream_trades_websocket(
    root, date, start_price, base_size, exchange, interval_ms, ws_port
):
    if not websockets:
        raise RuntimeError("websockets library is required for websocket server mode.")

    async def handler(websocket, path):
        """Handler for websocket connections. Accepts websocket and path."""
        ms_of_day = 0
        sequence = 1
        local_date = date
        last_price = start_price
        day_length_ms = 24 * 60 * 60 * 1000
        while True:
            ms_of_day = (ms_of_day + interval_ms) % day_length_ms
            if ms_of_day == 0 and sequence > 1:
                date_dt = datetime.strptime(str(local_date), "%Y%m%d")
                date_dt += timedelta(days=1)
                local_date = int(date_dt.strftime("%Y%m%d"))
            price = random_walk_price(last_price)
            last_price = price
            size = random.randint(1, base_size)
            trade_msg = {
                "header": {"type": "TRADE", "status": "CONNECTED"},
                "contract": {"security_type": "STOCK", "root": root},
                "trade": {
                    "ms_of_day": ms_of_day,
                    "sequence": sequence,
                    "size": size,
                    "condition": random.choice([0,1,2,4]),
                    "price": price,
                    "exchange": exchange,
                    "date": local_date
                }
            }
            sequence += 1
            await websocket.send(json.dumps(trade_msg, separators=(',', ':')))
            await asyncio.sleep(interval_ms / 1000.0)

    print(f"Starting WebSocket trade stream at ws://localhost:{ws_port}/v1/events (ctrl+C to stop)")
    async with websockets.serve(handler, "0.0.0.0", ws_port):
        await asyncio.Future()  # run forever

def get_date(date_str):
    if date_str is None:
        return int(datetime.now().strftime("%Y%m%d"))
    try:
        return int(date_str)
    except ValueError:
        return int(datetime.strptime(date_str, "%Y%m%d").strftime("%Y%m%d"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate streaming trade messages to stdout or websocket.")
    parser.add_argument("--root", type=str, default="AAPL", help="Stock root symbol")
    parser.add_argument("--date", type=str, default=None, help="YYYYMMDD format (defaults to today)")
    parser.add_argument("--start_price", type=float, default=100.0, help="Initial price")
    parser.add_argument("--size", type=int, default=100, help="Base max size (default 100)")
    parser.add_argument("--exchange", type=int, default=57, help="Exchange code (default 57)")
    parser.add_argument("--interval_ms", type=int, default=1, help="Interval ms between messages")
    parser.add_argument("--no_json", action="store_true", help="Suppress printing json to stdout")
    parser.add_argument("--websocket", action="store_true", help="Enable WebSocket server mode")
    parser.add_argument("--ws_port", type=int, default=8765, help="WebSocket port (default 8765)")
    args = parser.parse_args()

    _date = get_date(args.date)
    loop = asyncio.get_event_loop()
    if args.websocket:
        if not websockets:
            print("websockets library not installed. Please install with: pip install websockets", flush=True)
            exit(1)
        loop.run_until_complete(
            stream_trades_websocket(
                root=args.root,
                date=_date,
                start_price=args.start_price,
                base_size=args.size,
                exchange=args.exchange,
                interval_ms=args.interval_ms,
                ws_port=args.ws_port
            )
        )
    else:
        print(
            f"Streaming simulated trades to stdout for root={args.root}, starting at price={args.start_price}, every {args.interval_ms}ms. (Ctrl+C to stop)",
            flush=True
        )
        loop.run_until_complete(
            stream_trades_to_stdout(
                root=args.root,
                date=_date,
                start_price=args.start_price,
                base_size=args.size,
                exchange=args.exchange,
                interval_ms=args.interval_ms,
                show_json=not args.no_json
            )
        )