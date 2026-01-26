#!/usr/bin/env python3
"""
Historical Stock Quote Ingestion Service

Long-running service that:
- Processes multiple tickers from various sources
- Runs scheduled jobs every Sunday at 8:00 AM
- Exposes HTTP REST API for on-demand commands
- Uses batch database checks and parallel processing for efficiency

Designed to run in a Kubernetes cluster as a long-running service.
"""

import os
import sys
import logging
import time
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Set, Tuple
import signal
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify
import psycopg2

# Add the Charts directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from DatabaseConnection import DatabaseConnection
    from DataCollector import DataCollector
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}", file=sys.stderr)
    raise

load_dotenv()

log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
    log_level = 'INFO'

log_handlers = [logging.StreamHandler(sys.stdout)]
log_file_paths = [
    '/app/logs/ingest_historical_stock.log',
    os.path.join(os.path.dirname(__file__), 'logs', 'ingest_historical_stock.log'),
    'ingest_historical_stock.log'
]
for log_path in log_file_paths:
    try:
        log_dir = os.path.dirname(log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        log_handlers.append(logging.FileHandler(log_path))
        break
    except (OSError, PermissionError):
        continue

class MemoryLogHandler(logging.Handler):
    def __init__(self, max_entries=1000):
        super().__init__()
        self.logs = []
        self.max_entries = max_entries
    def emit(self, record):
        try:
            log_entry = {
                'timestamp': self.format(record).split(' - ')[0] if ' - ' in self.format(record) else datetime.now().isoformat(),
                'level': record.levelname,
                'message': record.getMessage(),
                'module': record.module,
                'funcName': record.funcName,
                'lineno': record.lineno
            }
            self.logs.append(log_entry)
            if len(self.logs) > self.max_entries:
                self.logs.pop(0)
        except Exception as e:
            # Silently ignore logging errors to prevent recursion
            pass

memory_handler = MemoryLogHandler(max_entries=1000)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers + [memory_handler]
)
logger = logging.getLogger(__name__)

def parse_time_string(time_str: str) -> timedelta:
    time_str = time_str.strip().lower()
    if time_str.endswith('d'):
        days = int(time_str[:-1])
        return timedelta(days=days)
    elif time_str.endswith('h'):
        hours = int(time_str[:-1])
        return timedelta(hours=hours)
    elif time_str.endswith('m'):
        minutes = int(time_str[:-1])
        return timedelta(minutes=minutes)
    else:
        try:
            days = int(time_str)
            return timedelta(days=days)
        except ValueError:
            raise ValueError(f"Invalid time string format: {time_str}. Use format like '1d', '30m', '1h'")

def parse_lookback_range(lookback: str) -> Optional[Tuple[timedelta, timedelta]]:
    """
    Parse a range lookback format like "(500:200)" or "(500d:200d)"
    Returns a tuple of (start_lookback, end_lookback) or None if not a range format.
    """
    lookback = lookback.strip()
    if not (lookback.startswith('(') and lookback.endswith(')')):
        return None
    
    # Remove parentheses
    inner = lookback[1:-1].strip()
    if ':' not in inner:
        return None
    
    try:
        parts = inner.split(':', 1)
        if len(parts) != 2:
            return None
        
        start_str = parts[0].strip()
        end_str = parts[1].strip()
        
        start_delta = parse_time_string(start_str)
        end_delta = parse_time_string(end_str)
        
        # Ensure start is greater than end (more days back)
        if start_delta < end_delta:
            start_delta, end_delta = end_delta, start_delta
        
        return (start_delta, end_delta)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid range format: {lookback}. Use format like '(500:200)' or '(500d:200d)'. Error: {e}")

def is_minute_interval(lookback: str) -> bool:
    lookback = lookback.strip().lower()
    return lookback.endswith('m') and not lookback.startswith('(')

class HistoricalStockIngestionService:
    def __init__(self):
        self.shutdown_requested = False
        self.db = None
        self.metadb_connection = None
        self.datacollector = None
        self.base_url = os.getenv('BASE_URL', 'http://localhost:25503/v3')
        self.lookback = os.getenv('LOOKBACK', '1d')
        self.schedule = os.getenv('SCHEDULE', '1d')
        self.repair = os.getenv('REPAIR', 'true').lower() == 'true'
        days_back_env = os.getenv('DAYS_BACK')
        if days_back_env and not os.getenv('LOOKBACK'):
            self.lookback = f"{days_back_env}d"
        self.ticker_source = os.getenv('TICKER_SOURCE', 'db')
        self.parallel_workers = int(os.getenv('PARALLEL_WORKERS', '2'))
        self.schedule_enabled = os.getenv('SCHEDULE_ENABLED', 'true').lower() == 'true'
        self.schedule_time = os.getenv('SCHEDULE_TIME', '16:15')
        self.last_scheduled_run = None
        self.next_scheduled_run = None
        self.processing_lock = threading.Lock()
        self.ticker_id_cache = {}  # Cache ticker -> ticker_id to avoid repeated lookups
        self.app = Flask(__name__)
        self._setup_api_routes()

    def _setup_api_routes(self):
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({'status': 'healthy'}), 200

        @self.app.route('/logs', methods=['GET'])
        def get_logs():
            try:
                logs = memory_handler.logs.copy() if memory_handler else []
                level_filter = request.args.get('level', '').upper()
                limit = request.args.get('limit', type=int)
                if level_filter and level_filter in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                    logs = [log for log in logs if log['level'] == level_filter]
                if limit and limit > 0:
                    logs = logs[-limit:]
                return jsonify({'total_entries': len(logs), 'logs': logs}), 200
            except Exception as e:
                logger.error(f"Error retrieving logs: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/v1/status', methods=['GET'])
        def status():
            tickers = self._get_ticker_list()
            return jsonify({
                'status': 'running',
                'last_scheduled_run': self.last_scheduled_run.isoformat() if self.last_scheduled_run else None,
                'next_scheduled_run': self.next_scheduled_run.isoformat() if self.next_scheduled_run else None,
                'config': {
                    "base_url": self.base_url,
                    "lookback": self.lookback,
                    "schedule": self.schedule,
                    "repair": self.repair,
                    "ticker_source": self.ticker_source,
                    "parallel_workers": self.parallel_workers,
                    "schedule_enabled": self.schedule_enabled,
                    "schedule_time": self.schedule_time
                },
                'ticker_count': len(tickers),
                'tickers': tickers[:10] if len(tickers) > 10 else tickers
            }), 200

        @self.app.route('/api/v1/process-ticker', methods=['POST'])
        def process_ticker_api():
            try:
                data = request.get_json() or {}
                ticker = data.get('ticker')
                lookback = data.get('lookback') or data.get('days_back')
                if lookback and isinstance(lookback, int):
                    lookback = f"{lookback}d"
                elif not lookback:
                    lookback = self.lookback
                repair_override = data.get('repair')
                original_repair = self.repair
                if repair_override is not None:
                    self.repair = str(repair_override).lower() == 'true'
                if not ticker:
                    return jsonify({'error': 'ticker is required'}), 400
                logger.info(f"API: Processing ticker {ticker} with lookback={lookback}, repair={self.repair}")
                stats = self.process_ticker(ticker, lookback)
                if repair_override is not None:
                    self.repair = original_repair
                return jsonify({
                    'status': 'completed',
                    'ticker': ticker,
                    'stats': stats
                }), 200
            except Exception as e:
                logger.error(f"API error processing ticker: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/v1/process-all', methods=['POST'])
        def process_all_api():
            try:
                data = request.get_json() or {}
                lookback = data.get('lookback') or data.get('days_back')
                if lookback and isinstance(lookback, int):
                    lookback = f"{lookback}d"
                elif not lookback:
                    lookback = self.lookback

                logger.info(f"API: Processing all tickers with lookback={lookback}")
                stats = self.process_all_tickers(lookback)
                return jsonify({
                    'status': 'completed',
                    'stats': stats
                }), 200
            except Exception as e:
                logger.error(f"API error processing all tickers: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/v1/config', methods=['GET'])
        def get_config():
            return jsonify({
                "base_url": self.base_url,
                "lookback": self.lookback,
                "schedule": self.schedule,
                "repair": self.repair,
                "ticker_source": self.ticker_source,
                "parallel_workers": self.parallel_workers,
                "schedule_enabled": self.schedule_enabled,
                "schedule_time": self.schedule_time
            }), 200

        @self.app.route('/api/v1/config', methods=['POST'])
        def update_config():
            try:
                data = request.get_json() or {}
                if 'base_url' in data:
                    self.base_url = str(data['base_url'])
                if 'lookback' in data:
                    try:
                        lookback_str = str(data['lookback'])
                        # Try parsing as range first, then as regular lookback
                        lookback_range = parse_lookback_range(lookback_str)
                        if lookback_range is None:
                            # Not a range, validate as regular lookback
                            parse_time_string(lookback_str)
                        self.lookback = lookback_str
                    except ValueError as e:
                        return jsonify({'error': f"Invalid lookback format: {e}"}), 400
                if 'schedule' in data:
                    try:
                        parse_time_string(str(data['schedule']))
                        self.schedule = str(data['schedule'])
                        if self.schedule_enabled:
                            logger.info("Schedule changed, will restart scheduler on next cycle")
                    except ValueError as e:
                        return jsonify({'error': f"Invalid schedule format: {e}"}), 400
                if 'repair' in data:
                    self.repair = str(data['repair']).lower() == 'true'
                if 'days_back' in data:
                    self.lookback = f"{int(data['days_back'])}d"
                if 'ticker_source' in data:
                    self.ticker_source = data['ticker_source']
                if 'parallel_workers' in data:
                    self.parallel_workers = int(data['parallel_workers'])
                if 'schedule_enabled' in data:
                    self.schedule_enabled = str(data['schedule_enabled']).lower() == 'true'
                if 'schedule_time' in data:
                    self.schedule_time = data['schedule_time']
                logger.info(
                    f"Configuration updated: base_url={self.base_url}, lookback={self.lookback}, schedule={self.schedule}, repair={self.repair}, ticker_source={self.ticker_source}, parallel_workers={self.parallel_workers}, schedule_enabled={self.schedule_enabled}, schedule_time={self.schedule_time}")
                return jsonify({
                    'status': 'updated',
                    'config': {
                        "base_url": self.base_url,
                        "lookback": self.lookback,
                        "schedule": self.schedule,
                        "repair": self.repair,
                        "ticker_source": self.ticker_source,
                        "parallel_workers": self.parallel_workers,
                        "schedule_enabled": self.schedule_enabled,
                        "schedule_time": self.schedule_time
                    }
                }), 200
            except Exception as e:
                logger.error(f"API error updating config: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

    def initialize(self):
        try:
            self.db = DatabaseConnection()
            self.datacollector = DataCollector(self.db)
            self._connect_metadata_db()
            logger.info("Service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}", exc_info=True)
            raise

    def _connect_metadata_db(self):
        """Connect to the metadata database"""
        try:
            metadb_name = os.getenv('METADB_NAME') or os.getenv('METADB_DBNAME')
            metadb_user = os.getenv('METADB_USER')
            metadb_password = os.getenv('METADB_PASSWORD')
            metadb_host = os.getenv('METADB_HOST')
            metadb_port = os.getenv('METADB_PORT', '5432')
            
            if not all([metadb_name, metadb_user, metadb_password, metadb_host]):
                logger.warning("Metadata database credentials not fully configured. Metadata features will be disabled.")
                logger.warning("Required env vars: METADB_NAME, METADB_USER, METADB_PASSWORD, METADB_HOST, METADB_PORT (optional)")
                return
            
            self.metadb_connection = psycopg2.connect(
                dbname=metadb_name,
                user=metadb_user,
                password=metadb_password,
                host=metadb_host,
                port=metadb_port
            )
            logger.info("Connected to metadata database")
        except Exception as e:
            logger.warning(f"Failed to connect to metadata database: {e}. Metadata features will be disabled.")
            self.metadb_connection = None

    def _get_ticker_list(self) -> List[str]:
        source = self.ticker_source
        if source == 'db' or source == 'watchlist' or source == 'database':
            try:
                if not self.db:
                    logger.warning("Database not initialized, cannot query watchlist")
                    return []
                with self.db.connection.cursor() as cursor:
                    query = """
                        SELECT DISTINCT t.ticker
                        FROM public.tickers 
                        ORDER BY t.ticker
                    """
                    cursor.execute(query)
                    results = cursor.fetchall()
                    tickers = [row[0].upper() for row in results if row[0]]
                    logger.info(f"Loaded {len(tickers)} tickers from public.tickers table")
                    return tickers
            except Exception as e:
                logger.error(f"Failed to load from database watchlist: {e}", exc_info=True)
                ticker_list = os.getenv('TICKER_LIST', '')
                if ticker_list:
                    return [t.strip().upper() for t in ticker_list.split(',') if t.strip()]
        elif source == 'env':
            ticker_list = os.getenv('TICKER_LIST', '')
            if ticker_list:
                tickers = [t.strip().upper() for t in ticker_list.split(',') if t.strip()]
                logger.info(f"Loaded {len(tickers)} tickers from TICKER_LIST env var")
                return tickers
        elif source == 'config_file':
            config_file = os.path.join(os.path.dirname(__file__), 'tickers.json')
            try:
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        data = json.load(f)
                        tickers = data.get('tickers', [])
                        logger.info(f"Loaded {len(tickers)} tickers from config file")
                        return tickers
            except Exception as e:
                logger.warning(f"Failed to load from config file: {e}, falling back to env var")
        ticker_list = os.getenv('TICKER_LIST', '')
        if ticker_list:
            return [t.strip().upper() for t in ticker_list.split(',') if t.strip()]
        logger.warning("No tickers found from any source")
        return []

    def update_healthcheck(self):
        try:
            healthcheck_paths = [
                Path('/tmp/healthcheck'),
                Path(os.path.join(os.path.dirname(__file__), 'healthcheck'))
            ]
            for healthcheck_path in healthcheck_paths:
                try:
                    healthcheck_path.parent.mkdir(parents=True, exist_ok=True)
                    healthcheck_path.touch()
                    return
                except (OSError, PermissionError):
                    continue
        except Exception as e:
            logger.debug(f"Failed to update healthcheck file: {e}")

    def is_weekend(self, date_str: str) -> bool:
        try:
            if '-' in date_str:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            else:
                date_obj = datetime.strptime(date_str, '%Y%m%d')
            return date_obj.weekday() >= 5
        except Exception as e:
            logger.warning(f"Error parsing date {date_str}: {e}")
            return False

    def get_trading_days(self, start_date: datetime, end_date: datetime) -> List[str]:
        trading_days = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:
                trading_days.append(current_date.strftime('%Y%m%d'))
            current_date += timedelta(days=1)
        return trading_days

    def batch_check_data_availability(
        self, 
        tickers: List[str], 
        trading_days: List[str]
    ) -> Dict[str, Set[str]]:
        # Get or cache ticker IDs
        ticker_ids = {}
        for ticker in tickers:
            if ticker in self.ticker_id_cache:
                ticker_ids[ticker] = self.ticker_id_cache[ticker]
            else:
                try:
                    ticker_id = self.db.get_or_create_root(ticker)
                    if ticker_id:
                        ticker_ids[ticker] = ticker_id
                        self.ticker_id_cache[ticker] = ticker_id
                except Exception as e:
                    logger.warning(f"Failed to get ticker_id for {ticker}: {e}")
        if not ticker_ids:
            logger.warning("No valid ticker IDs found")
            return {}
        trading_days_db = [f"{d[:4]}-{d[4:6]}-{d[6:8]}" for d in trading_days]
        availability = {ticker: set() for ticker in tickers if ticker in ticker_ids}
        try:
            # Use metadata database if available, otherwise fall back to main database
            if self.metadb_connection:
                with self.metadb_connection.cursor() as cursor:
                    ticker_id_list = list(ticker_ids.values())
                    date_list = trading_days_db
                    batch_size = 50
                    for i in range(0, len(date_list), batch_size):
                        date_batch = date_list[i:i+batch_size]
                        ticker_placeholders = ','.join(['%s'] * len(ticker_id_list))
                        date_placeholders = ','.join(['%s'] * len(date_batch))
                        # Query metadata table for fast lookups
                        query = f"""
                            SELECT m.ticker_id, m.date
                            FROM metadata.quote_dates_summary m
                            WHERE m.ticker_id IN ({ticker_placeholders})
                            AND m.date IN ({date_placeholders})
                            AND m.record_count > 0
                        """
                        params = ticker_id_list + date_batch
                        cursor.execute(query, params)
                        results = cursor.fetchall()
                        # Map ticker_id back to ticker symbol
                        id_to_ticker = {tid: ticker for ticker, tid in ticker_ids.items()}
                        for row in results:
                            ticker_id = row[0]
                            date = row[1]
                            ticker = id_to_ticker.get(ticker_id)
                            if ticker and ticker in availability:
                                date_str = date.strftime('%Y%m%d') if hasattr(date, 'strftime') else str(date).replace('-', '')
                                availability[ticker].add(date_str)
            else:
                # Fallback to main database query
                with self.db.connection.cursor() as cursor:
                    ticker_id_list = list(ticker_ids.values())
                    date_list = trading_days_db
                    batch_size = 50
                    for i in range(0, len(date_list), batch_size):
                        date_batch = date_list[i:i+batch_size]
                        ticker_placeholders = ','.join(['%s'] * len(ticker_id_list))
                        date_placeholders = ','.join(['%s'] * len(date_batch))
                        query = f"""
                            SELECT DISTINCT ON (q.ticker_id, DATE(q.timestamp))
                                   t.ticker, DATE(q.timestamp) as date
                            FROM stocks.quote q
                            JOIN public.tickers t ON q.ticker_id = t.id
                            WHERE q.ticker_id IN ({ticker_placeholders})
                            AND DATE(q.timestamp) IN ({date_placeholders})
                            ORDER BY q.ticker_id, DATE(q.timestamp), q.timestamp
                        """
                        params = ticker_id_list + date_batch
                        cursor.execute(query, params)
                        results = cursor.fetchall()
                        for row in results:
                            ticker = row[0]
                            date = row[1]
                            if ticker in availability:
                                date_str = date.strftime('%Y%m%d') if hasattr(date, 'strftime') else str(date).replace('-', '')
                                availability[ticker].add(date_str)
        except Exception as e:
            logger.error(f"Error in batch check: {e}", exc_info=True)
        return availability

    def fetch_and_insert_data(self, ticker: str, date: str, ticker_id: Optional[int] = None) -> bool:
        """
        Fetch and insert data for a ticker/date combination.
        ticker_id can be provided to avoid lookup (performance optimization).
        """
        try:
            date_db_format = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            if self.is_weekend(date_db_format):
                return True
            
            # Skip existence check - we already know from batch_check that data is missing
            # This eliminates redundant database queries
            
            if not self.repair:
                logger.debug(f"Repair disabled: Skipping API fetch for {ticker} {date_db_format} (data missing)")
                return False
            
            logger.info(f"Fetching {ticker} {date_db_format} from API...")
            data = self.datacollector.theta_stocks_quote(
                ticker=ticker,
                date=date,
                interval='1s',
                base_url=self.base_url
            )
            if not data:
                logger.warning(f"No data returned for {ticker} on {date_db_format}")
                return False
            
            self.db.insert_stocks_quote(data)
            
            # Update metadata table with record count
            if ticker_id is None:
                ticker_id = self.ticker_id_cache.get(ticker)
                if not ticker_id:
                    ticker_id = self.db.get_or_create_root(ticker)
                    if ticker_id:
                        self.ticker_id_cache[ticker] = ticker_id
            
            if ticker_id:
                self._update_metadata(ticker_id, date_db_format, len(data))
            
            logger.info(f"✓ Successfully inserted {len(data)} quotes for {ticker} on {date_db_format}")
            return True
        except Exception as e:
            logger.error(f"Error fetching/inserting {ticker} {date}: {e}", exc_info=True)
            return False

    def _check_data_exists_single(self, ticker: str, date: str) -> bool:
        """Check if data exists using metadata table for fast lookup"""
        try:
            ticker_id = self.db.get_or_create_root(ticker)
            if not ticker_id:
                return False
            
            # Use metadata database if available
            if self.metadb_connection:
                with self.metadb_connection.cursor() as cursor:
                    query = """
                        SELECT record_count 
                        FROM metadata.quote_dates_summary
                        WHERE ticker_id = %s AND date = %s AND record_count > 0
                    """
                    cursor.execute(query, (ticker_id, date))
                    result = cursor.fetchone()
                    return bool(result and result[0] > 0)
            else:
                # Fallback to main database
                with self.db.connection.cursor() as cursor:
                    query = """
                        SELECT EXISTS(
                            SELECT 1 FROM stocks.quote
                            WHERE ticker_id = %s AND DATE(timestamp) = %s
                        ) as has_data
                    """
                    cursor.execute(query, (ticker_id, date))
                    result = cursor.fetchone()
                    return bool(result[0]) if result else False
        except Exception as e:
            logger.debug(f"Error checking data existence: {e}")
            return False

    def _update_metadata(self, ticker_id: int, date: str, record_count: int):
        """Update or insert metadata for a ticker/date combination in metadata database"""
        if not self.metadb_connection:
            return  # Skip if metadata DB not configured
        
        try:
            with self.metadb_connection.cursor() as cursor:
                # Use INSERT ... ON CONFLICT to update or insert
                query = """
                    INSERT INTO metadata.quote_dates_summary (ticker_id, date, record_count)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (ticker_id, date) 
                    DO UPDATE SET record_count = EXCLUDED.record_count
                """
                cursor.execute(query, (ticker_id, date, record_count))
                self.metadb_connection.commit()
        except Exception as e:
            logger.warning(f"Failed to update metadata for ticker_id={ticker_id}, date={date}: {e}")
            if self.metadb_connection:
                self.metadb_connection.rollback()

    def process_ticker(self, ticker: str, lookback: Optional[str] = None) -> Dict:
        if lookback is None:
            lookback = self.lookback
        stats = {
            'ticker': ticker,
            'total_days': 0,
            'days_with_data': 0,
            'days_fetched': 0,
            'days_failed': 0,
            'good_data': [],
            'no_data_dates': [],
            'errors': []
        }
        try:
            # Check if lookback is a range format like "(500:200)"
            lookback_range = parse_lookback_range(lookback)
            if lookback_range:
                # Process range: from start_lookback to end_lookback
                start_lookback, end_lookback = lookback_range
                end_date = datetime.now() - end_lookback  # End of range (more recent)
                start_date = datetime.now() - start_lookback  # Start of range (older)
                logger.info(f"Processing {ticker} for range lookback: {lookback} (from {start_date.date()} to {end_date.date()})")
                trading_days = self.get_trading_days(start_date, end_date)
                stats['total_days'] = len(trading_days)
                logger.info(f"Processing {ticker} from {start_date.date()} to {end_date.date()} ({len(trading_days)} trading days, lookback={lookback})")
                availability = self.batch_check_data_availability([ticker], trading_days)
                available_dates = availability.get(ticker, set())
                stats['good_data'] = sorted(list(available_dates))
                stats['days_with_data'] = len(available_dates)
                missing_dates = [d for d in trading_days if d not in available_dates]
                if not missing_dates:
                    logger.info(f"✓ {ticker}: All {len(available_dates)} days have data")
                    return stats
                logger.info(f"✗ {ticker}: {len(missing_dates)} days missing data, fetching...")
                # Get ticker_id from cache to avoid repeated lookups
                ticker_id = self.ticker_id_cache.get(ticker)
                if not ticker_id:
                    ticker_id = self.db.get_or_create_root(ticker)
                    if ticker_id:
                        self.ticker_id_cache[ticker] = ticker_id
                workers = min(self.parallel_workers, len(missing_dates))
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = {
                        executor.submit(self.fetch_and_insert_data, ticker, date, ticker_id): date
                        for date in missing_dates
                    }
                    for future in as_completed(futures):
                        date = futures[future]
                        try:
                            success = future.result()
                            if success:
                                stats['days_fetched'] += 1
                                stats['good_data'].append(date)
                            else:
                                stats['days_failed'] += 1
                                stats['no_data_dates'].append(date)
                        except Exception as e:
                            logger.error(f"Error processing {ticker} {date}: {e}")
                            stats['days_failed'] += 1
                            stats['no_data_dates'].append(date)
                            stats['errors'].append(f"{date}: {str(e)}")
                stats['good_data'] = sorted(stats['good_data'])
                stats['no_data_dates'] = sorted(stats['no_data_dates'])
                logger.info(
                    f"Completed {ticker}: {stats['days_with_data']} existing, "
                    f"{stats['days_fetched']} fetched, {stats['days_failed']} failed"
                )
                return stats
            
            # Regular single lookback period
            lookback_delta = parse_time_string(lookback)
            end_date = datetime.now()
            start_date = end_date - lookback_delta
            if is_minute_interval(lookback):
                current_date = end_date.strftime('%Y%m%d')
                start_time_obj = end_date - lookback_delta
                start_time = start_time_obj.strftime('%H:%M:%S')
                end_time = end_date.strftime('%H:%M:%S')
                logger.info(f"Processing {ticker} for minute interval: {current_date} from {start_time} to {end_time}")
                try:
                    date_db_format = f"{current_date[:4]}-{current_date[4:6]}-{current_date[6:8]}"
                    if not self.is_weekend(date_db_format):
                        if not self.repair:
                            logger.debug(f"Repair disabled: Skipping API fetch for {ticker} (minute interval)")
                            stats['days_failed'] = 1
                            stats['no_data_dates'].append(current_date)
                        else:
                            logger.info(f"Fetching {ticker} {current_date} from API (minute interval)...")
                            data = self.datacollector.theta_stocks_quote(
                                ticker=ticker,
                                date=current_date,
                                interval='1s',
                                start_time=start_time,
                                end_time=end_time,
                                base_url=self.base_url
                            )
                            if data:
                                self.db.insert_stocks_quote(data)
                                stats['days_fetched'] = 1
                                stats['good_data'].append(current_date)
                                logger.info(f"✓ Successfully inserted {len(data)} quotes for {ticker} (minute interval)")
                            else:
                                stats['days_failed'] = 1
                                stats['no_data_dates'].append(current_date)
                except Exception as e:
                    logger.error(f"Error processing {ticker} (minute interval): {e}", exc_info=True)
                    stats['days_failed'] = 1
                    stats['no_data_dates'].append(current_date)
                    stats['errors'].append(f"Processing error: {str(e)}")
                return stats
            trading_days = self.get_trading_days(start_date, end_date)
            stats['total_days'] = len(trading_days)
            logger.info(f"Processing {ticker} from {start_date.date()} to {end_date.date()} ({len(trading_days)} trading days, lookback={lookback})")
            availability = self.batch_check_data_availability([ticker], trading_days)
            available_dates = availability.get(ticker, set())
            stats['good_data'] = sorted(list(available_dates))
            stats['days_with_data'] = len(available_dates)
            missing_dates = [d for d in trading_days if d not in available_dates]
            if not missing_dates:
                logger.info(f"✓ {ticker}: All {len(available_dates)} days have data")
                return stats
            logger.info(f"✗ {ticker}: {len(missing_dates)} days missing data, fetching...")
            # Get ticker_id from cache to avoid repeated lookups
            ticker_id = self.ticker_id_cache.get(ticker)
            if not ticker_id:
                ticker_id = self.db.get_or_create_root(ticker)
                if ticker_id:
                    self.ticker_id_cache[ticker] = ticker_id
            workers = min(self.parallel_workers, len(missing_dates))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(self.fetch_and_insert_data, ticker, date, ticker_id): date
                    for date in missing_dates
                }
                for future in as_completed(futures):
                    date = futures[future]
                    try:
                        success = future.result()
                        if success:
                            stats['days_fetched'] += 1
                            stats['good_data'].append(date)
                        else:
                            stats['days_failed'] += 1
                            stats['no_data_dates'].append(date)
                    except Exception as e:
                        logger.error(f"Error processing {ticker} {date}: {e}")
                        stats['days_failed'] += 1
                        stats['no_data_dates'].append(date)
                        stats['errors'].append(f"{date}: {str(e)}")
            stats['good_data'] = sorted(stats['good_data'])
            stats['no_data_dates'] = sorted(stats['no_data_dates'])
            logger.info(
                f"Completed {ticker}: {stats['days_with_data']} existing, "
                f"{stats['days_fetched']} fetched, {stats['days_failed']} failed"
            )
        except Exception as e:
            logger.error(f"Error processing ticker {ticker}: {e}", exc_info=True)
            stats['errors'].append(f"Processing error: {str(e)}")
        return stats

    def process_all_tickers(self, lookback: Optional[str] = None) -> Dict:
        if lookback is None:
            lookback = self.lookback
        tickers = self._get_ticker_list()
        if not tickers:
            logger.error("No tickers to process")
            return {'error': 'No tickers found'}
        logger.info(f"Tickers: {', '.join(tickers)} ({len(tickers)} total)")
        
        # Check if lookback is a range format
        lookback_range = parse_lookback_range(lookback)
        if lookback_range:
            # Process range: from start_lookback to end_lookback
            start_lookback, end_lookback = lookback_range
            end_date = datetime.now() - end_lookback  # End of range (more recent)
            start_date = datetime.now() - start_lookback  # Start of range (older)
            logger.info(f"Processing all tickers for range lookback: {lookback} (from {start_date.date()} to {end_date.date()})")
        else:
            # Regular single lookback period
            lookback_delta = parse_time_string(lookback)
            end_date = datetime.now()
            start_date = end_date - lookback_delta
        
        if is_minute_interval(lookback) and not lookback_range:
            overall_stats = {
                'total_tickers': len(tickers),
                'total_tasks': len(tickers),
                'completed_tasks': 0,
                'failed_tasks': 0,
                'ticker_stats': {}
            }
            for ticker in tickers:
                try:
                    stats = self.process_ticker(ticker, lookback)
                    if stats.get('days_failed', 0) == 0:
                        overall_stats['completed_tasks'] += 1
                        overall_stats['ticker_stats'][ticker] = {'fetched': stats.get('days_fetched', 0), 'failed': 0}
                    else:
                        overall_stats['failed_tasks'] += 1
                        overall_stats['ticker_stats'][ticker] = {'fetched': stats.get('days_fetched', 0), 'failed': stats.get('days_failed', 0)}
                except Exception as e:
                    logger.error(f"Error processing {ticker}: {e}")
                    overall_stats['failed_tasks'] += 1
                    overall_stats['ticker_stats'][ticker] = {'fetched': 0, 'failed': 1}
            return overall_stats
        trading_days = self.get_trading_days(start_date, end_date)
        availability = self.batch_check_data_availability(tickers, trading_days)
        missing_tasks = []
        missing_summary = []
        for ticker in tickers:
            available_dates = availability.get(ticker, set())
            missing_dates = [d for d in trading_days if d not in available_dates]
            missing_dates_filtered = [d for d in missing_dates if not self.is_weekend(f"{d[:4]}-{d[4:6]}-{d[6:8]}")]
            if missing_dates_filtered:
                missing_summary.append(f"{ticker}: {len(missing_dates_filtered)} missing ({', '.join(sorted(missing_dates_filtered))})")
                for date in missing_dates_filtered:
                    missing_tasks.append((ticker, date))
            else:
                missing_summary.append(f"{ticker}: complete")
        if missing_summary:
            logger.info("Status: " + " | ".join(missing_summary))
        if missing_tasks:
            logger.info(f"Fetching {len(missing_tasks)} missing date(s)")
        overall_stats = {
            'total_tickers': len(tickers),
            'total_tasks': len(missing_tasks),
            'completed_tasks': 0,
            'failed_tasks': 0,
            'ticker_stats': {}
        }
        if missing_tasks:
            workers = min(self.parallel_workers, len(missing_tasks))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(
                        self.fetch_and_insert_data, 
                        ticker, 
                        date, 
                        self.ticker_id_cache.get(ticker)  # Use cached ticker_id
                    ): (ticker, date)
                    for ticker, date in missing_tasks
                }
                for future in as_completed(futures):
                    ticker, date = futures[future]
                    try:
                        success = future.result()
                        if success:
                            overall_stats['completed_tasks'] += 1
                            if ticker not in overall_stats['ticker_stats']:
                                overall_stats['ticker_stats'][ticker] = {'fetched': 0, 'failed': 0}
                            overall_stats['ticker_stats'][ticker]['fetched'] += 1
                        else:
                            overall_stats['failed_tasks'] += 1
                            if ticker not in overall_stats['ticker_stats']:
                                overall_stats['ticker_stats'][ticker] = {'fetched': 0, 'failed': 0}
                            overall_stats['ticker_stats'][ticker]['failed'] += 1
                    except Exception as e:
                        logger.error(f"Error processing {ticker} {date}: {e}")
                        overall_stats['failed_tasks'] += 1
                        if ticker not in overall_stats['ticker_stats']:
                            overall_stats['ticker_stats'][ticker] = {'fetched': 0, 'failed': 0}
                        overall_stats['ticker_stats'][ticker]['failed'] += 1
        if overall_stats['completed_tasks'] > 0 or overall_stats['failed_tasks'] > 0:
            logger.info(f"Result: {overall_stats['completed_tasks']} fetched, {overall_stats['failed_tasks']} failed")
        return overall_stats

    def start_scheduler(self):
        import schedule
        def scheduled_job():
            logger.info(f"Scheduled job started (lookback={self.lookback})")
            self.last_scheduled_run = datetime.now()
            self.process_all_tickers()
            self.update_healthcheck()
        try:
            schedule_delta = parse_time_string(self.schedule)
            schedule_seconds = int(schedule_delta.total_seconds())
            min_seconds = 60
            max_seconds = 7 * 24 * 60 * 60
            if schedule_seconds < min_seconds:
                logger.warning(f"Schedule {self.schedule} is less than 1 minute, using 1 minute minimum")
                schedule_seconds = min_seconds
            elif schedule_seconds > max_seconds:
                logger.warning(f"Schedule {self.schedule} is more than 7 days, using 7 days maximum")
                schedule_seconds = max_seconds
            if self.schedule == '1d' or schedule_seconds == 86400:
                try:
                    hour, minute = map(int, self.schedule_time.split(':'))
                    schedule.every().day.at(self.schedule_time).do(scheduled_job)
                    now = datetime.now()
                    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if next_run <= now:
                        next_run += timedelta(days=1)
                    self.next_scheduled_run = next_run
                    logger.info(f"Scheduler started: Runs daily at {self.schedule_time} (lookback={self.lookback})")
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Invalid schedule_time format '{self.schedule_time}', using interval-based schedule")
                    schedule.every(schedule_seconds).seconds.do(scheduled_job)
                    self.next_scheduled_run = datetime.now() + timedelta(seconds=schedule_seconds)
                    logger.info(f"Scheduler started: Runs every {self.schedule} (lookback={self.lookback})")
            else:
                schedule.every(schedule_seconds).seconds.do(scheduled_job)
                self.next_scheduled_run = datetime.now() + timedelta(seconds=schedule_seconds)
                logger.info(f"Scheduler started: Runs every {self.schedule} (lookback={self.lookback})")
        except Exception as e:
            logger.error(f"Error setting up scheduler: {e}", exc_info=True)
            schedule.every().sunday.at(self.schedule_time).do(scheduled_job)
            logger.warning(f"Fell back to legacy schedule: Sunday at {self.schedule_time}")
        def scheduler_loop():
            check_interval = 10 if is_minute_interval(self.schedule) else 60
            while not self.shutdown_requested:
                schedule.run_pending()
                time.sleep(check_interval)
        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()

    def start_api_server(self, host='0.0.0.0', port=8080):
        def run_server():
            use_production_server = os.getenv('USE_PRODUCTION_SERVER', 'true').lower() == 'true'
            if use_production_server:
                try:
                    from waitress import serve
                    logger.info(f"Starting production WSGI server (waitress) on {host}:{port}")
                    serve(self.app, host=host, port=port, threads=4, channel_timeout=120)
                except ImportError:
                    logger.warning("waitress not available, falling back to development server")
                    logger.warning("Install waitress for production: pip install waitress")
                    self.app.run(host=host, port=port, debug=False, use_reloader=False)
                except Exception as e:
                    logger.error(f"Error starting waitress server: {e}, falling back to development server")
                    self.app.run(host=host, port=port, debug=False, use_reloader=False)
            else:
                logger.warning("Using Flask development server (not recommended for production)")
                self.app.run(host=host, port=port, debug=False, use_reloader=False)
        api_thread = threading.Thread(target=run_server, daemon=True)
        api_thread.start()
        logger.info(f"API server thread started on {host}:{port}")

    def run(self):
        self.initialize()
        self.update_healthcheck()
        if self.schedule_enabled:
            self.start_scheduler()
        api_port = int(os.getenv('API_PORT', '8080'))
        self.start_api_server(port=api_port)
        logger.info("Service started and running. Press Ctrl+C to stop.")
        try:
            while not self.shutdown_requested:
                self.update_healthcheck()
                time.sleep(30)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.shutdown()

    def shutdown(self):
        logger.info("Shutting down service...")
        self.shutdown_requested = True
        if self.db:
            self.db.close()
        if self.metadb_connection:
            try:
                self.metadb_connection.close()
                logger.info("Metadata database connection closed")
            except Exception as e:
                logger.warning(f"Error closing metadata database connection: {e}")
        logger.info("Service shut down complete")

service = None

def signal_handler(signum, frame):
    global service
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    if service:
        service.shutdown()
    sys.exit(0)

def main():
    global service
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    log_dirs = ['/app/logs', os.path.join(os.path.dirname(__file__), 'logs')]
    for log_dir in log_dirs:
        try:
            os.makedirs(log_dir, exist_ok=True)
            break
        except (OSError, PermissionError):
            continue
    ticker = os.getenv('TICKER')
    run_mode = os.getenv('RUN_MODE', 'service')
    if run_mode == 'once' and ticker:
        logger.info("Running in legacy mode (single ticker)")
        service = HistoricalStockIngestionService()
        service.initialize()
        lookback = os.getenv('LOOKBACK') or os.getenv('DAYS_BACK', '365')
        if isinstance(lookback, str) and lookback.isdigit():
            lookback = f"{lookback}d"
        elif not isinstance(lookback, str):
            lookback = f"{int(lookback)}d"
        stats = service.process_ticker(ticker, lookback)
        logger.info(f"Processing completed: {stats}")
        service.shutdown()
        sys.exit(0 if stats['days_failed'] == 0 else 1)
    else:
        logger.info("Starting historical stock ingestion service")
        service = HistoricalStockIngestionService()
        service.run()

if __name__ == '__main__':
    main()