#!/usr/bin/env python3
"""
Live Stock Ingestion Service

This service connects to Theta Terminal websocket, loads all tickers from public.alpha_list watchlist,
subscribes to live stock trade streams for all tickers, and inserts individual trade quotes
directly into stocks.quote table. Each quote is logged as it comes through.
Includes market hours checking and enhanced error handling.
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import sys
import os
import pytz
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the Charts directory to the path to import DatabaseConnection
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from DatabaseConnection import DatabaseConnection

# Configure logging
# Allow DEBUG level via environment variable
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
    log_level = 'INFO'

# Configure logging - ensure stdout is unbuffered for Kubernetes logs
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ingest_live_stocks.log'),
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # Override any existing configuration
)

# Ensure stdout is unbuffered for real-time log viewing in Kubernetes
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
logger = logging.getLogger(__name__)
logger.info(f"Logging level set to: {log_level}")

# Suppress DatabaseConnection INFO logs to reduce log flooding
# Only show WARNING and above from DatabaseConnection
db_logger = logging.getLogger('DatabaseConnection')
db_logger.setLevel(logging.WARNING)


class MarketHoursChecker:
    """Check if US stock market is open (NYSE/NASDAQ)"""
    
    def __init__(self):
        self.et_tz = pytz.timezone('US/Eastern')
        self.market_open = datetime.strptime("09:30", "%H:%M").time()
        self.market_close = datetime.strptime("16:00", "%H:%M").time()
    
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        now_et = datetime.now(self.et_tz)
        current_time = now_et.time()
        current_date = now_et.date()
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if now_et.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Check if it's a market holiday (simplified - you may want to add full holiday list)
        # Major holidays: New Year's Day, MLK Day, Presidents Day, Good Friday, Memorial Day,
        # Independence Day, Labor Day, Thanksgiving, Christmas
        month_day = (current_date.month, current_date.day)
        market_holidays = [
            (1, 1),   # New Year's Day
            (7, 4),   # Independence Day
            (12, 25), # Christmas
        ]
        
        if month_day in market_holidays:
            return False
        
        # Check if within trading hours (9:30 AM - 4:00 PM ET)
        return self.market_open <= current_time <= self.market_close
    
    def time_until_market_open(self) -> Optional[timedelta]:
        """Calculate time until market opens (returns None if market is open)"""
        if self.is_market_open():
            return None
        
        now_et = datetime.now(self.et_tz)
        current_time = now_et.time()
        current_date = now_et.date()
        
        # If before market open today
        if current_time < self.market_open:
            market_open_dt = self.et_tz.localize(
                datetime.combine(current_date, self.market_open)
            )
            return market_open_dt - now_et
        
        # Otherwise, market opens tomorrow (or next trading day)
        next_date = current_date + timedelta(days=1)
        # Skip weekends
        while next_date.weekday() >= 5:
            next_date += timedelta(days=1)
        
        market_open_dt = self.et_tz.localize(
            datetime.combine(next_date, self.market_open)
        )
        return market_open_dt - now_et


class LiveStockIngestService:
    """Service to stream live stock trades and insert quotes directly into database"""
    
    def __init__(self, websocket_url: Optional[str] = None, symbol: Optional[str] = None, test_mode: bool = False):
        # Get websocket URL from environment variable if not provided
        self.websocket_url = websocket_url or os.getenv('WEBSOCKET_URL', 'ws://127.0.0.1:25520/v1/events')
        self.symbol = symbol  # Deprecated - now using watchlist
        self.test_mode = test_mode  # If True, don't insert to database, just log
        
        # Initialize database connection with error handling
        if not test_mode:
            try:
                self.db = DatabaseConnection()
                logger.info("Database connection established")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}", exc_info=True)
                print(f"ERROR: Database connection failed: {e}", file=sys.stderr, flush=True)
                raise
        else:
            self.db = None
        self.ticker_ids: Dict[str, int] = {}  # Map symbol -> ticker_id
        self.symbols: List[str] = []  # List of symbols from watchlist
        self.stream_id = 0  # Next ID to use for subscription
        self.pending_subscriptions: Dict[int, tuple] = {}  # Track pending subscription IDs: {id: (symbol, timestamp)}
        self.confirmed_subscriptions: Dict[int, str] = {}  # Track confirmed subscription IDs: {id: symbol}
        self.websocket = None
        self.running = False
        self.market_checker = MarketHoursChecker()
        
        # Batch insertion
        self.quote_buffer: List[tuple] = []
        self.buffer_size = 200  # Insert every 200 quotes or every 1 second
        self.last_insert_time = datetime.now()
        
        # Statistics for aggregated logging
        self.stats = {
            'total_messages': 0,
            'total_trades_parsed': 0,
            'total_quotes_buffered': 0,
            'total_quotes_inserted': 0,
            'total_errors': 0,
            'last_summary_time': datetime.now(),
            'quotes_per_second': 0.0,
            'messages_per_second': 0.0,
            'last_price': {},  # Dict of symbol -> last price
            'last_quote_time': None,
            'buffer_flush_count': 0,
            'quotes_by_symbol': {}  # Track quotes per symbol
        }
        
        # Error handling
        self.consecutive_errors = 0
        self.max_consecutive_errors = 10
        self.base_retry_delay = 5  # seconds
        self.max_retry_delay = 300  # 5 minutes
        
        # Health check file for Kubernetes
        self.healthcheck_file = '/tmp/healthcheck'
        
        if test_mode:
            logger.warning("TEST MODE ENABLED - Database inserts are DISABLED")
    
    def load_watchlist(self) -> List[str]:
        """Load all tickers from public.alpha_list watchlist"""
        if self.test_mode:
            # Return test symbols
            return ['SPY', 'AAPL', 'QQQ']
        
        if not self.db:
            logger.error("Database connection not available")
            # Fallback to single symbol if provided
            if self.symbol:
                logger.warning(f"Falling back to single symbol: {self.symbol}")
                return [self.symbol.upper()]
            return []
        
        try:
            with self.db.connection.cursor() as cursor:
                query = """
                    SELECT DISTINCT t.ticker
                    FROM public.alpha_list w
                    JOIN public.tickers t ON w.ticker_id = t.id
                    ORDER BY t.ticker
                """
                cursor.execute(query)
                results = cursor.fetchall()
                tickers = [row[0].upper() for row in results if row[0]]
                logger.info(f"Loaded {len(tickers)} tickers from public.alpha_list: {', '.join(tickers)}")
                return tickers
        except Exception as e:
            logger.error(f"Failed to load watchlist from database: {e}", exc_info=True)
            print(f"ERROR: Failed to load watchlist: {e}", file=sys.stderr, flush=True)
            # Fallback to single symbol if provided
            if self.symbol:
                logger.warning(f"Falling back to single symbol: {self.symbol}")
                return [self.symbol.upper()]
            return []
    
    def get_ticker_id(self, symbol: str) -> Optional[int]:
        """Get or create ticker ID for the symbol"""
        symbol_upper = symbol.upper()
        if symbol_upper in self.ticker_ids:
            return self.ticker_ids[symbol_upper]
        
        if self.test_mode:
            # Use hash of symbol for test mode
            ticker_id = hash(symbol_upper) % 10000
            self.ticker_ids[symbol_upper] = ticker_id
            return ticker_id
        
        try:
            ticker_id = self.db.get_or_create_root(symbol_upper)
            self.ticker_ids[symbol_upper] = ticker_id
            logger.debug(f"Ticker ID for {symbol_upper}: {ticker_id}")
            return ticker_id
        except Exception as e:
            logger.error(f"Failed to get ticker ID for {symbol_upper}: {e}")
            return None
    
    def parse_trade_message(self, message: str) -> Optional[Dict]:
        """
        Parse a trade message from the websocket.
        Expected format:
        {
          "header": {
            "type": "TRADE",
            "status": "CONNECTED"
          },
          "contract": {
            "security_type": "STOCK",
            "root": "AAPL"
          },
          "trade": {
            "ms_of_day": 38437607,
            "sequence": 12150295,
            "size": 500,
            "condition": 0,
            "price": 184.5099,
            "exchange": 57,
            "date": 20240503
          }
        }
        """
        try:
            # Parse JSON
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            
            # Check if this is a trade message
            if isinstance(data, dict):
                # Check header
                header = data.get('header', {})
                header_type = header.get('type')
                header_status = header.get('status')
                
                # Log header info for debugging
                if not hasattr(self, '_last_logged_header') or self._message_count <= 5:
                    logger.debug(f"Message header: type={header_type}, status={header_status}")
                
                # Check if this is a trade message with trade data
                if header_type == 'TRADE' and 'trade' in data:
                    trade_data = data['trade']
                    contract_data = data.get('contract', {})
                    
                    # Verify it's for one of our watchlist symbols (case-insensitive)
                    root = contract_data.get('root', '').upper()
                    # If symbols not loaded yet, accept all (will be filtered later)
                    if self.symbols and root not in self.symbols:
                        if not hasattr(self, '_last_wrong_symbol') or self._message_count % 100 == 0:
                            logger.debug(f"Ignoring trade for symbol '{root}' (not in watchlist)")
                            self._last_wrong_symbol = True
                        return None  # Not in our watchlist, ignore
                    
                    # Add symbol to trade dict for later use
                    trade_dict = {
                        'symbol': root,
                        'ms_of_day': trade_data.get('ms_of_day'),
                        'sequence': trade_data.get('sequence'),
                        'size': trade_data.get('size'),
                        'condition': trade_data.get('condition'),
                        'price': trade_data.get('price'),
                        'exchange': trade_data.get('exchange'),
                        'date': trade_data.get('date')
                    }
                    
                    # Validate we have all required fields
                    missing_fields = [k for k, v in trade_dict.items() if v is None and k != 'symbol']
                    if missing_fields:
                        logger.warning(f"Trade missing fields: {missing_fields}. Trade data: {trade_dict}")
                        return None
                    
                    return trade_dict
                
                # Handle subscription confirmation
                if header_type == 'TRADE' and header_status == 'CONNECTED':
                    # Check if this confirmation includes an ID that matches our pending subscription
                    confirmation_id = data.get('id')
                    if confirmation_id is not None:
                        if confirmation_id in self.pending_subscriptions:
                            symbol, _ = self.pending_subscriptions[confirmation_id]
                            logger.info(f"Trade stream subscription confirmed for {symbol} (ID: {confirmation_id})")
                            self.confirmed_subscriptions[confirmation_id] = symbol
                            del self.pending_subscriptions[confirmation_id]
                            self.consecutive_errors = 0  # Reset error count on successful connection
                        elif confirmation_id in self.confirmed_subscriptions:
                            logger.debug(f"Duplicate confirmation for subscription ID: {confirmation_id}")
                        else:
                            logger.warning(f"Received confirmation for unknown subscription ID: {confirmation_id}")
                    else:
                        logger.info(f"Trade stream connected (no ID in confirmation)")
                        self.consecutive_errors = 0
                    return None
                
                # Handle other message types
                if 'error' in data or 'Error' in data:
                    logger.error(f"Error message received: {json.dumps(data, indent=2)}")
                    return None
                
                # Log unknown message structure (first few only)
                if self._message_count <= 5:
                    logger.debug(f"Unknown message structure: {json.dumps(data, indent=2)[:500]}")
            
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {message[:200]} - {e}")
            logger.debug(f"Full message: {message}")
            return None
        except Exception as e:
            logger.error(f"Error parsing trade message: {e}", exc_info=True)
            return None
    
    def calculate_timestamp(self, date: int, ms_of_day: int) -> Optional[datetime]:
        """Calculate full timestamp from date (YYYYMMDD) and ms_of_day"""
        try:
            # Parse date
            date_str = str(date)
            if len(date_str) != 8:
                logger.error(f"Invalid date format: {date}")
                return None
            
            year = int(date_str[0:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            
            # Create base datetime at midnight
            base_time = datetime(year, month, day)
            
            # Add milliseconds
            timestamp = base_time + timedelta(milliseconds=ms_of_day)
            
            return timestamp
            
        except Exception as e:
            logger.error(f"Error calculating timestamp from date={date}, ms_of_day={ms_of_day}: {e}")
            return None
    
    def prepare_quote_for_insert(self, trade: Dict) -> Optional[tuple]:
        """Prepare a trade quote for database insertion into stocks.quote table
        
        stocks.quote expects: (timestamp, ticker_id, bid, bid_size, bid_exchange, bid_condition,
                               ask, ask_size, ask_exchange, ask_condition)
        Since we're receiving trade data, we'll use the trade price as both bid and ask.
        """
        try:
            symbol = trade.get('symbol')
            if not symbol:
                logger.warning(f"Trade missing symbol: {trade}")
                return None
            
            ticker_id = self.get_ticker_id(symbol)
            if ticker_id is None:
                logger.warning(f"Could not get ticker_id for symbol {symbol}")
                return None
            
            date = trade.get('date')
            ms_of_day = trade.get('ms_of_day')
            size = trade.get('size')
            condition = trade.get('condition')
            price = trade.get('price')
            exchange = trade.get('exchange')
            
            # Validate required fields
            if None in [date, ms_of_day, size, condition, price, exchange]:
                logger.warning(f"Missing required fields in trade: {trade}")
                return None
            
            # Calculate full timestamp
            timestamp = self.calculate_timestamp(date, ms_of_day)
            if timestamp is None:
                return None
            
            # Convert trade data to quote format
            # Use trade price as both bid and ask (since we only have trade price, not separate bid/ask)
            bid = float(price)
            ask = float(price)
            bid_size = int(size)
            ask_size = int(size)
            bid_exchange = int(exchange)
            ask_exchange = int(exchange)
            bid_condition = int(condition)
            ask_condition = int(condition)
            
            # Return tuple for database insertion into stocks.quote
            # Format: (timestamp, ticker_id, bid, bid_size, bid_exchange, bid_condition,
            #          ask, ask_size, ask_exchange, ask_condition)
            return (
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
            
        except Exception as e:
            logger.error(f"Error preparing quote for insert: {e}")
            return None
    
    def insert_quotes_batch(self, quotes: List[tuple]):
        """Insert a batch of quotes into the database"""
        if not quotes:
            return
        
        if self.test_mode:
            logger.info(f"TEST MODE: Would insert {len(quotes)} quotes to database")
            logger.info(f"TEST MODE: Sample quote: {quotes[0] if quotes else 'N/A'}")
            return
        
        try:
            self.db.insert_stocks_quote(quotes)  # Note: method name is insert_stocks_quote (singular)
            self.consecutive_errors = 0  # Reset on successful insert
        except Exception as e:
            self.consecutive_errors += 1
            self.stats['total_errors'] += 1
            logger.error(f"Error inserting quotes (error {self.consecutive_errors}/{self.max_consecutive_errors}): {e}")
            
            if self.consecutive_errors >= self.max_consecutive_errors:
                logger.critical(f"Too many consecutive errors ({self.consecutive_errors}). Stopping service.")
                self.running = False
                raise
    
    def flush_buffer(self):
        """Flush the quote buffer to database"""
        if not self.quote_buffer:
            return
        
        buffer_size = len(self.quote_buffer)
        self.insert_quotes_batch(self.quote_buffer)
        self.stats['total_quotes_inserted'] += buffer_size
        self.stats['buffer_flush_count'] += 1
        self.quote_buffer = []
        self.last_insert_time = datetime.now()
    
    async def subscribe_to_trades(self):
        """Subscribe to trade stream for all symbols in watchlist
        
        Per Theta Terminal docs: The ID should be incremented for each new stream request.
        The ID is returned in a confirmation message to verify the request was successful.
        Failure to increment will prevent automatic resubscription.
        """
        if not self.symbols:
            logger.error("No symbols in watchlist to subscribe to")
            return
        
        logger.info(f"Subscribing to {len(self.symbols)} symbols from watchlist")
        
        # Subscribe to each symbol
        for symbol in self.symbols:
            subscription_id = self.stream_id
            
            req = {
                "msg_type": "STREAM",
                "sec_type": "STOCK",
                "req_type": "TRADE",
                "add": True,
                "id": subscription_id,
                "contract": {
                    "root": symbol
                }
            }
            
            message = json.dumps(req)
            await self.websocket.send(message)
            
            # Track this as a pending subscription with symbol info
            self.pending_subscriptions[subscription_id] = (symbol, datetime.now())
            
            logger.info(f"Subscription request sent for {symbol} trade stream (ID: {subscription_id})")
            
            # Small delay between subscriptions to avoid overwhelming the websocket
            await asyncio.sleep(0.1)
            
            # Increment for next subscription request (per documentation requirement)
            self.stream_id += 1
        
        logger.info(f"Sent {len(self.symbols)} subscription requests. Waiting for confirmations...")
    
    async def handle_message(self, message: str):
        """Handle incoming websocket message"""
        try:
            # Track message count
            if not hasattr(self, '_message_count'):
                self._message_count = 0
            self._message_count += 1
            self.stats['total_messages'] += 1
            
            # Log first 10 messages and then every 100th message (debug only)
            if self._message_count <= 10 or self._message_count % 100 == 0:
                logger.debug(f"Message #{self._message_count} received (length: {len(message)} chars)")
                if logger.level == logging.DEBUG:
                    logger.debug(f"Raw message: {message[:500]}")
            
            # Parse the message
            trade = self.parse_trade_message(message)
            
            if trade:
                symbol = trade.get('symbol', 'UNKNOWN')
                self.stats['total_trades_parsed'] += 1
                self.stats['last_quote_time'] = datetime.now()
                
                # Update quote count per symbol
                if symbol not in self.stats['quotes_by_symbol']:
                    self.stats['quotes_by_symbol'][symbol] = 0
                self.stats['quotes_by_symbol'][symbol] += 1
                
                # Update last price for this symbol
                price = trade.get('price')
                if price is not None:
                    self.stats['last_price'][symbol] = float(price)
                
                # Log each quote as it comes through
                logger.info(
                    f"QUOTE {symbol} price=${price:.2f} size={trade.get('size')} "
                    f"exchange={trade.get('exchange')} time={trade.get('date')} "
                    f"ms={trade.get('ms_of_day')}"
                )
                
                # Prepare quote for insertion
                quote = self.prepare_quote_for_insert(trade)
                
                if quote:
                    # Add to buffer
                    self.quote_buffer.append(quote)
                    self.stats['total_quotes_buffered'] += 1
                    logger.debug(f"Quote added to buffer (buffer size: {len(self.quote_buffer)}/{self.buffer_size})")
                    
                    # Flush if buffer is full or enough time has passed (every 1 second)
                    now = datetime.now()
                    if (len(self.quote_buffer) >= self.buffer_size or 
                        (now - self.last_insert_time).total_seconds() >= 1):
                        self.flush_buffer()
                    
                    # Log aggregated stats every 3 seconds (independent of flush)
                    self.log_aggregated_stats()
                else:
                    logger.warning(f"Failed to prepare quote for insert from trade: {trade}")
                    self.stats['total_errors'] += 1
            else:
                # Log non-trade messages for debugging (first few only)
                if self._message_count <= 10 and logger.level == logging.DEBUG:
                    try:
                        if isinstance(message, str):
                            data = json.loads(message)
                        else:
                            data = message
                        logger.debug(f"Non-trade message: {json.dumps(data, indent=2)[:300]}")
                    except:
                        logger.debug(f"Non-trade message (non-JSON): {message[:200]}")
                    
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            self.stats['total_errors'] += 1
    
    def calculate_retry_delay(self) -> float:
        """Calculate exponential backoff retry delay"""
        delay = min(
            self.base_retry_delay * (2 ** min(self.consecutive_errors, 8)),
            self.max_retry_delay
        )
        return delay
    
    def log_aggregated_stats(self):
        """Log aggregated statistics every 3 seconds"""
        now = datetime.now()
        time_since_last = (now - self.stats['last_summary_time']).total_seconds()
        
        # Only log if 3+ seconds have passed
        if time_since_last < 3:
            return
        
        # Calculate rates
        if time_since_last > 0:
            trades_in_period = self.stats['total_trades_parsed'] - self.stats.get('_last_trades_count', 0)
            messages_in_period = self.stats['total_messages'] - self.stats.get('_last_messages_count', 0)
            
            self.stats['quotes_per_second'] = trades_in_period / time_since_last
            self.stats['messages_per_second'] = messages_in_period / time_since_last
            
            self.stats['_last_trades_count'] = self.stats['total_trades_parsed']
            self.stats['_last_messages_count'] = self.stats['total_messages']
        
        # Format last prices for top symbols
        top_symbols = sorted(
            self.stats['last_price'].items(),
            key=lambda x: self.stats['quotes_by_symbol'].get(x[0], 0),
            reverse=True
        )[:5]  # Top 5 by quote count
        price_str = ", ".join([f"{sym}=${price:.2f}" for sym, price in top_symbols])
        
        # Log aggregated summary
        logger.info(
            f"STATS prices=[{price_str}] "
            f"quotes={self.stats['quotes_per_second']:.1f}/sec "
            f"messages={self.stats['messages_per_second']:.1f}/sec "
            f"buffer={len(self.quote_buffer)}/{self.buffer_size} "
            f"parsed={self.stats['total_trades_parsed']} "
            f"inserted={self.stats['total_quotes_inserted']} "
            f"errors={self.stats['total_errors']} "
            f"flushes={self.stats['buffer_flush_count']} "
            f"symbols={len(self.symbols)} "
            f"period={time_since_last:.1f}s"
        )
        
        # Reset timer
        self.stats['last_summary_time'] = now
    
    def update_healthcheck(self):
        """Update healthcheck file for Kubernetes probes"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.healthcheck_file), exist_ok=True)
            # Touch the file to update its modification time
            with open(self.healthcheck_file, 'w') as f:
                f.write(str(datetime.now().isoformat()))
            # Also ensure file is readable
            os.chmod(self.healthcheck_file, 0o644)
        except Exception as e:
            logger.warning(f"Could not update healthcheck file: {e}", exc_info=True)
    
    async def healthcheck_updater(self):
        """Periodically update healthcheck file"""
        # Update immediately on startup
        self.update_healthcheck()
        
        while self.running:
            try:
                self.update_healthcheck()
                await asyncio.sleep(30)  # Update every 30 seconds (more frequent for better health checks)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error in healthcheck updater: {e}")
                await asyncio.sleep(30)
    
    async def wait_for_market_open(self):
        """Wait until market opens"""
        while not self.market_checker.is_market_open():
            time_until_open = self.market_checker.time_until_market_open()
            if time_until_open:
                hours = time_until_open.total_seconds() / 3600
                logger.info(f"Market is closed. Waiting {hours:.1f} hours until market open")
                # Wait in smaller chunks to check for shutdown
                wait_seconds = min(time_until_open.total_seconds(), 300)  # Max 5 minutes at a time
                await asyncio.sleep(wait_seconds)
            else:
                break
    
    async def connect_and_stream(self):
        """Main connection and streaming loop"""
        retry_count = 0
        max_retries = 5
        retry_delay = 5  # seconds
        
        while self.running:
            try:
                # Check if market is open
                if not self.market_checker.is_market_open():
                    await self.wait_for_market_open()
                    if not self.running:
                        break
                
                logger.info(f"Connecting to websocket: {self.websocket_url}")
                
                async with websockets.connect(
                    self.websocket_url,
                    ping_interval=20,
                    ping_timeout=10
                ) as websocket:
                    self.websocket = websocket
                    logger.info("Websocket connection established")
                    
                    # Subscribe to trades
                    await self.subscribe_to_trades()
                    
                    # Reset retry count on successful connection
                    retry_count = 0
                    self.consecutive_errors = 0
                    
                    # Clear old pending subscriptions (they're from previous connection)
                    if self.pending_subscriptions:
                        logger.warning(f"Clearing {len(self.pending_subscriptions)} pending subscriptions from previous connection")
                        self.pending_subscriptions.clear()
                    self.confirmed_subscriptions.clear()
                    
                    # Ensure watchlist is loaded (should already be loaded in run(), but reload if empty)
                    if not self.symbols:
                        logger.warning("Watchlist not loaded, reloading...")
                        self.symbols = self.load_watchlist()
                        if not self.symbols:
                            logger.error("No symbols loaded from watchlist. Cannot proceed.")
                            await asyncio.sleep(60)  # Wait before retrying
                            continue
                        # Pre-load ticker IDs for all symbols
                        logger.info(f"Initializing ticker IDs for {len(self.symbols)} symbols...")
                        for symbol in self.symbols:
                            self.get_ticker_id(symbol)
                        logger.info(f"Initialized {len(self.ticker_ids)} ticker IDs")
                    
                    # Update healthcheck file immediately after connection
                    self.update_healthcheck()
                    logger.info("Healthcheck file updated after websocket connection")
                    
                    # Start healthcheck updater task
                    healthcheck_task = asyncio.create_task(self.healthcheck_updater())
                    
                    # Wait a moment for subscription confirmation
                    await asyncio.sleep(1)
                    
                    # Check if we got confirmation
                    if self.pending_subscriptions:
                        pending_ids = list(self.pending_subscriptions.keys())
                        logger.warning(f"Still waiting for subscription confirmation (IDs: {pending_ids})")
                        # Wait a bit more
                        await asyncio.sleep(2)
                        if self.pending_subscriptions:
                            logger.warning(f"Subscription confirmation timeout. Proceeding anyway")
                    
                    try:
                        # Main message loop
                        logger.info("Starting message loop, waiting for quotes")
                        if self.confirmed_subscriptions:
                            confirmed_symbols = list(self.confirmed_subscriptions.values())
                            logger.info(f"Active subscriptions: {len(self.confirmed_subscriptions)} symbols - {', '.join(confirmed_symbols[:10])}{'...' if len(confirmed_symbols) > 10 else ''}")
                        
                        async for message in websocket:
                            if not self.running:
                                break
                            
                            # Check if market closed during streaming
                            if not self.market_checker.is_market_open():
                                logger.info("Market closed. Disconnecting")
                                break
                            
                            await self.handle_message(message)
                    finally:
                        healthcheck_task.cancel()
                        try:
                            await healthcheck_task
                        except asyncio.CancelledError:
                            pass
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                if self.running:
                    retry_count += 1
                    retry_delay = self.calculate_retry_delay()
                    if retry_count < max_retries:
                        logger.info(f"Connection lost. Retrying in {retry_delay:.1f} seconds (attempt {retry_count}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error("Max retries reached. Waiting 60 seconds before retry")
                        retry_count = 0
                        await asyncio.sleep(60)  # Wait 1 minute before trying again
                        
            except Exception as e:
                logger.error(f"Error in websocket connection: {e}")
                if self.running:
                    retry_count += 1
                    retry_delay = self.calculate_retry_delay()
                    if retry_count < max_retries:
                        logger.info(f"Connection error. Retrying in {retry_delay:.1f} seconds (attempt {retry_count}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error("Max retries reached. Waiting 60 seconds before retry")
                        retry_count = 0
                        await asyncio.sleep(60)
        
        # Flush any remaining quotes before exiting
        logger.info("Flushing remaining quotes before shutdown")
        self.flush_buffer()
    
    async def run(self):
        """Start the service"""
        self.running = True
        logger.info(f"Starting Live Stock Ingestion Service")
        logger.info(f"WebSocket: {self.websocket_url}")
        
        # Create healthcheck file immediately on startup
        try:
            self.update_healthcheck()
            logger.info("Healthcheck file created")
        except Exception as e:
            logger.warning(f"Could not create initial healthcheck file: {e}")
        
        # Load watchlist and initialize ticker IDs
        self.symbols = self.load_watchlist()
        if not self.symbols:
            logger.error("No symbols loaded from watchlist. Exiting.")
            return
        
        logger.info(f"Loaded {len(self.symbols)} symbols from watchlist")
        
        # Pre-load ticker IDs for all symbols
        logger.info(f"Initializing ticker IDs for {len(self.symbols)} symbols...")
        for symbol in self.symbols:
            self.get_ticker_id(symbol)
        logger.info(f"Initialized {len(self.ticker_ids)} ticker IDs")
        
        try:
            await self.connect_and_stream()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down")
        finally:
            self.running = False
            if self.db and not self.test_mode:
                self.db.close()
            logger.info("Service stopped")


async def main():
    """Main entry point"""
    # Allow override via environment variables
    websocket_url = os.getenv('WEBSOCKET_URL', 'ws://127.0.0.1:25520/v1/events')
    symbol = os.getenv('SYMBOL', 'SPY')
    test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
    
    service = LiveStockIngestService(
        websocket_url=websocket_url,
        symbol=symbol,
        test_mode=test_mode
    )
    await service.run()


if __name__ == "__main__":
    try:
        # Flush stdout immediately to ensure logs are visible in Kubernetes
        print("Starting Live Stock Ingestion Service...", flush=True)
        sys.stdout.flush()
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"FATAL ERROR: {e}", file=sys.stderr, flush=True)
        sys.stderr.flush()
        sys.exit(1)

