#!/usr/bin/env python3
"""
Options Metadata and Quote Ingestion Service

- Metadata: POST /api/options/ingest/metadata — Populates options.expirations,
  options.quote_dates, options.strikes for a symbol (and optional expiration range).
- Quotes: POST /api/options/ingest/quotes — Fetches 1m option quotes from ThetaData
  for a symbol and date range; requires metadata to exist first (returns 409 with
  instructions if not).

Only the last 8 years of options data are available for ingestion; older dates
and expirations are rejected with 400.

A Sunday scheduler (OPTIONS_METADATA_SCHEDULE_TIME, default 20:00) refreshes
metadata for all tickers for the upcoming ~60 days. Disable with
OPTIONS_SCHEDULE_ENABLED=false.

Uses BASE_URL from .env for ThetaData.
"""

import os
import sys
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import signal
from dotenv import load_dotenv
from flask import Flask, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from DatabaseConnection import DatabaseConnection
    from DataCollector import DataCollector
except ImportError:
    pass

load_dotenv()

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
    log_level = "INFO"

log_handlers = [logging.StreamHandler(sys.stdout)]
for log_path in [
    "/app/logs/options_ingest.log",
    os.path.join(os.path.dirname(__file__), "logs", "options_ingest.log"),
    "options_ingest.log",
]:
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
            msg = self.format(record)
            ts = msg.split(" - ")[0] if " - " in msg else datetime.now().isoformat()
            self.logs.append({
                "timestamp": ts,
                "level": record.levelname,
                "message": record.getMessage(),
                "module": record.module,
                "funcName": record.funcName,
                "lineno": record.lineno,
            })
            if len(self.logs) > self.max_entries:
                self.logs.pop(0)
        except Exception:
            pass


memory_handler = MemoryLogHandler(max_entries=1000)
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=log_handlers + [memory_handler],
)
logger = logging.getLogger(__name__)

# Only the last 8 years of options data are available for ingestion.
OPTIONS_DATA_MAX_YEARS = 8


def options_cutoff_yyyymmdd() -> int:
    """Return cutoff date as YYYYMMDD; dates before this are not available for options data."""
    cutoff = datetime.utcnow().date() - timedelta(days=OPTIONS_DATA_MAX_YEARS * 365)
    return int(cutoff.strftime("%Y%m%d"))


def validate_date_within_limit(date_yyyymmdd: int) -> Optional[str]:
    """Return None if date is within the 8-year limit, else an error message."""
    if date_yyyymmdd < options_cutoff_yyyymmdd():
        return (
            "Options data is only available for the last %s years. "
            "Requested date exceeds this limit." % OPTIONS_DATA_MAX_YEARS
        )
    return None


def validate_expiration_range_within_limit(exp_range: Optional[Tuple[int, int]]) -> Optional[str]:
    """Return None if expiration range is within the 8-year limit, else an error message."""
    if exp_range is None:
        return None
    low, high = exp_range
    cutoff = options_cutoff_yyyymmdd()
    if low < cutoff or high < cutoff:
        return (
            "Options data is only available for the last %s years. "
            "Requested expiration range exceeds this limit." % OPTIONS_DATA_MAX_YEARS
        )
    return None


def get_help_text(base_url: str = "http://localhost:8081") -> str:
    """Human-readable help for -h and GET /api/options/help?format=text."""
    base = base_url.rstrip("/")
    return """Options API - Metadata and Quote Ingestion

    Only the last 8 years of options data are available. Metadata refresh runs every Sunday (OPTIONS_METADATA_SCHEDULE_TIME, default 20:00).

    ENDPOINTS

    GET  %s/health
        
        Health check.

    GET  %s/api/options/help?format=text
    
        This help (JSON or plain text).

    GET  %s/api/options/status
    
        Status, base_url, tickers from public.tickers.

    POST %s/api/options/ingest/metadata
    
        Ingest metadata only. Body: symbol (required), expiration (optional YYYYMMDD or YYYYMMDD:YYYYMMDD).

    POST %s/api/options/ingest/quotes

        Ingest 1m option quotes. Body: symbol (required), date (required YYYYMMDD), end_date (optional), expiration (optional). Omit or "*" = send "*" to API (all expirations, one request per date). Or expiration=YYYYMMDD for one. Requires metadata first.

    GET  %s/api/options/fetch/metadata/expirations

        Fetch expirations from DB (no external API). Query: symbol (required), expiration_min, expiration_max (optional YYYYMMDD).

    GET  %s/api/options/fetch/metadata/contracts

        Fetch contracts from DB. Query: symbol (required), expiration_min, expiration_max, side (optional call|put).

    GET  %s/api/options/fetch/metadata/strikes

        Fetch strikes from DB. Query: symbol (required), expiration_min, expiration_max (optional YYYYMMDD).

    GET  %s/api/options/fetch/metadata/all

        Fetch expirations, contracts, and strikes in one response. Same query params as above.

    GET  %s/api/options/fetch/quotes?symbol=...&expiration=...&strike=...&side=call|put&date=...&time=...
        Fetch option quotes from DB for one contract. Required: symbol, expiration (YYYYMMDD), strike, side (call|put). Optional: date (default today), time (HH:MM or HH:MM:SS). For data integrity checks.

    GET  %s/logs

        Session logs.

    EXAMPLE COMMANDS

    # Ingest metadata for AAPL (all expirations in 8-year window)
    curl -X POST %s/api/options/ingest/metadata -H "Content-Type: application/json" -d '{"symbol": "AAPL"}'

    # Ingest metadata for a date range
    curl -X POST %s/api/options/ingest/metadata -H "Content-Type: application/json" -d '{"symbol": "AAPL", "expiration": "20240101:20251231"}'

    # Ingest quotes for one day (all expirations; run metadata first if 409)
    curl -X POST %s/api/options/ingest/quotes -H "Content-Type: application/json" -d '{"symbol": "AAPL", "date": "20241104"}'

    # Ingest quotes for one day, single expiration: add "expiration": "20241220"
    # Ingest quotes for a date range (all expirations)
    curl -X POST %s/api/options/ingest/quotes -H "Content-Type: application/json" -d '{"symbol": "AAPL", "date": "20241101", "end_date": "20241105"}'

    # Fetch expirations for AAPL (all expirations in 8-year window)
    curl -X GET %s/api/options/fetch/metadata/expirations -G -d 'symbol=AAPL'

    # Fetch contracts for AAPL (all contracts in 8-year window)
    curl -X GET %s/api/options/fetch/metadata/contracts -G -d 'symbol=AAPL'

    # Fetch strikes for AAPL (all strikes in 8-year window)
    curl -X GET %s/api/options/fetch/metadata/strikes -G -d 'symbol=AAPL'

    # Fetch quotes for one contract (date/time optional; default today, all times)
    curl -X GET "%s/api/options/fetch/quotes?symbol=AAPL&expiration=20241220&strike=150&side=call"

    """ % (base, base, base, base, base, base, base, base, base, base, base, base, base, base, base, base, base, base, base)


def parse_expiration_spec(spec) -> Optional[Tuple[int, int]]:
    """Parse expiration as YYYYMMDD or range YYYYMMDD:YYYYMMDD. Returns (min_exp, max_exp) or None."""
    if spec is None or (isinstance(spec, str) and not spec.strip()):
        return None
    s = str(spec).strip()
    if ":" in s:
        parts = s.split(":", 1)
        try:
            low, high = int(parts[0].strip()), int(parts[1].strip())
            if low <= high and 19000101 <= low <= 21001231 and 19000101 <= high <= 21001231:
                return (low, high)
        except ValueError:
            pass
        logger.warning("Invalid expiration range: %s", spec)
        return None
    try:
        single = int(s)
        if 19000101 <= single <= 21001231:
            return (single, single)
    except ValueError:
        pass
    logger.warning("Invalid expiration: %s", spec)
    return None


class OptionsIngestionService:
    def __init__(self):
        self.shutdown_requested = False
        self.db = None
        self.datacollector = None
        self.base_url = os.getenv("BASE_URL", "http://127.0.0.1:25503/v3").strip().rstrip("/")
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route("/health", methods=["GET"])
        def health():
            return jsonify({"status": "healthy"}), 200

        @self.app.route("/help", methods=["GET"])
        @self.app.route("/api/options/help", methods=["GET"])
        def help_endpoint():
            if request.args.get("format", "").strip().lower() == "text":
                base = request.url_root.rstrip("/") or "http://localhost:8081"
                return get_help_text(base), 200, {"Content-Type": "text/plain; charset=utf-8"}
            return jsonify({
                "service": "Options Metadata and Quote Ingestion",
                "description": "Metadata: options.expirations, quote_dates, strikes. Quotes: options.quotes. Only the last 8 years of options data are available.",
                "schedule": "Metadata refresh every Sunday at OPTIONS_METADATA_SCHEDULE_TIME (default 20:00) for upcoming ~60 days.",
                "endpoints": [
                    {"method": "GET", "path": "/health", "description": "Health check."},
                    {"method": "POST", "path": "/api/options/ingest/metadata",
                     "description": "Ingest metadata only. Body: symbol (required), expiration (optional YYYYMMDD or YYYYMMDD:YYYYMMDD). Enforces 8-year limit."},
                    {"method": "POST", "path": "/api/options/ingest/quotes",
                     "description": "Ingest option quotes (1m). Body: symbol (required), date (required YYYYMMDD), end_date (optional), expiration (optional; omit or \"*\" = send \"*\" to API for all expirations, or YYYYMMDD for one). Requires metadata first; returns 409 if missing."},
                    {"method": "GET", "path": "/api/options/fetch/metadata/expirations",
                     "description": "Fetch expirations from DB only. Query: symbol (required), expiration_min, expiration_max (optional YYYYMMDD)."},
                    {"method": "GET", "path": "/api/options/fetch/metadata/contracts",
                     "description": "Fetch contracts from DB only. Query: symbol (required), expiration_min, expiration_max, side (optional call|put)."},
                    {"method": "GET", "path": "/api/options/fetch/metadata/strikes",
                     "description": "Fetch strikes from DB only. Query: symbol (required), expiration_min, expiration_max (optional YYYYMMDD)."},
                    {"method": "GET", "path": "/api/options/fetch/metadata/all",
                     "description": "Fetch expirations, contracts, and strikes from DB in one response. Same query params."},
                    {"method": "GET", "path": "/api/options/fetch/quotes",
                     "description": "Fetch option quotes from DB. Query: symbol, expiration (YYYYMMDD), strike, side (call|put); optional date (default today), time (HH:MM). For data integrity."},
                    {"method": "GET", "path": "/api/options/status", "description": "Status and config."},
                    {"method": "GET", "path": "/logs", "description": "Session logs. Query: level, limit."},
                ],
            }), 200

        @self.app.route("/logs", methods=["GET"])
        def get_logs():
            try:
                logs = memory_handler.logs.copy() if memory_handler else []
                level_filter = request.args.get("level", "").upper()
                limit = request.args.get("limit", type=int)
                if level_filter and level_filter in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
                    logs = [x for x in logs if x["level"] == level_filter]
                if limit and limit > 0:
                    logs = logs[-limit:]
                return jsonify({"total_entries": len(logs), "logs": logs}), 200
            except Exception as e:
                logger.error("Error retrieving logs: %s", e, exc_info=True)
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/options/status", methods=["GET"])
        def status():
            tickers = self._get_ticker_list()
            return jsonify({
                "status": "running",
                "base_url": self.base_url,
                "ticker_count": len(tickers),
                "tickers": tickers[:20] if len(tickers) > 20 else tickers,
            }), 200

        def _fetch_metadata_params():
            """Parse symbol, expiration_min, expiration_max, side from request.args. Returns (ticker_id, exp_min, exp_max, side) or (None, None, None, None), error_response."""
            symbol = request.args.get("symbol") or request.args.get("ticker")
            if not symbol or not str(symbol).strip():
                return None, None, None, None, (jsonify({"error": "symbol (or ticker) is required"}), 400)
            ticker = str(symbol).strip().upper()
            ticker_id = self.db.get_or_create_options_ticker(ticker)
            if not ticker_id:
                return None, None, None, None, (jsonify({"error": "Unknown symbol: %s (add to public.tickers first)" % ticker}), 400)
            exp_min = request.args.get("expiration_min") or request.args.get("exp_min")
            exp_max = request.args.get("expiration_max") or request.args.get("exp_max")
            exp_min_int = None
            exp_max_int = None
            if exp_min:
                try:
                    exp_min_int = int(str(exp_min).strip().replace("-", ""))
                    if len(str(exp_min_int)) != 8:
                        raise ValueError("invalid")
                except ValueError:
                    return None, None, None, None, (jsonify({"error": "expiration_min must be YYYYMMDD"}), 400)
            if exp_max:
                try:
                    exp_max_int = int(str(exp_max).strip().replace("-", ""))
                    if len(str(exp_max_int)) != 8:
                        raise ValueError("invalid")
                except ValueError:
                    return None, None, None, None, (jsonify({"error": "expiration_max must be YYYYMMDD"}), 400)
            side = request.args.get("side")
            if side is not None and str(side).strip():
                side = str(side).strip().lower()
                if side not in ("call", "put"):
                    return None, None, None, None, (jsonify({"error": "side must be 'call' or 'put'"}), 400)
            else:
                side = None
            return ticker_id, exp_min_int, exp_max_int, side, None

        @self.app.route("/api/options/fetch/metadata/expirations", methods=["GET"])
        def fetch_metadata_expirations():
            """Fetch expirations from DB only. Query: symbol (required), expiration_min, expiration_max (optional YYYYMMDD)."""
            try:
                ticker_id, exp_min, exp_max, _, err = _fetch_metadata_params()
                if err is not None:
                    return err[0], err[1]
                expirations = self.db.fetch_option_expirations(ticker_id, expiration_min=exp_min, expiration_max=exp_max)
                return jsonify({"symbol": request.args.get("symbol") or request.args.get("ticker"), "expirations": expirations, "count": len(expirations)}), 200
            except Exception as e:
                logger.error("Fetch metadata expirations error: %s", e, exc_info=True)
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/options/fetch/metadata/contracts", methods=["GET"])
        def fetch_metadata_contracts():
            """Fetch contracts from DB only. Query: symbol (required), expiration_min, expiration_max, side (optional call|put)."""
            try:
                ticker_id, exp_min, exp_max, side, err = _fetch_metadata_params()
                if err is not None:
                    return err[0], err[1]
                contracts = self.db.fetch_option_contracts(ticker_id, expiration_min=exp_min, expiration_max=exp_max, side=side)
                return jsonify({"symbol": request.args.get("symbol") or request.args.get("ticker"), "contracts": contracts, "count": len(contracts)}), 200
            except Exception as e:
                logger.error("Fetch metadata contracts error: %s", e, exc_info=True)
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/options/fetch/metadata/strikes", methods=["GET"])
        def fetch_metadata_strikes():
            """Fetch strikes from DB only. Query: symbol (required), expiration_min, expiration_max (optional YYYYMMDD)."""
            try:
                ticker_id, exp_min, exp_max, _, err = _fetch_metadata_params()
                if err is not None:
                    return err[0], err[1]
                strikes = self.db.fetch_option_strikes(ticker_id, expiration_min=exp_min, expiration_max=exp_max)
                return jsonify({"symbol": request.args.get("symbol") or request.args.get("ticker"), "strikes": strikes, "count": len(strikes)}), 200
            except Exception as e:
                logger.error("Fetch metadata strikes error: %s", e, exc_info=True)
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/options/fetch/metadata/all", methods=["GET"])
        def fetch_metadata_all():
            """Fetch expirations, contracts, and strikes from DB in one response. Same query params: symbol, expiration_min, expiration_max, side (for contracts)."""
            try:
                ticker_id, exp_min, exp_max, side, err = _fetch_metadata_params()
                if err is not None:
                    return err[0], err[1]
                symbol = request.args.get("symbol") or request.args.get("ticker")
                expirations = self.db.fetch_option_expirations(ticker_id, expiration_min=exp_min, expiration_max=exp_max)
                contracts = self.db.fetch_option_contracts(ticker_id, expiration_min=exp_min, expiration_max=exp_max, side=side)
                strikes = self.db.fetch_option_strikes(ticker_id, expiration_min=exp_min, expiration_max=exp_max)
                return jsonify({
                    "symbol": symbol,
                    "expirations": expirations,
                    "contracts": contracts,
                    "strikes": strikes,
                    "counts": {"expirations": len(expirations), "contracts": len(contracts), "strikes": len(strikes)},
                }), 200
            except Exception as e:
                logger.error("Fetch metadata all error: %s", e, exc_info=True)
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/options/fetch/quotes", methods=["GET"])
        def fetch_quotes():
            """Fetch option quotes from DB for one contract. Params: symbol, expiration (YYYYMMDD), strike, side (call|put); optional date (default today), time (HH:MM or HHMMSS). Used for data integrity checks."""
            try:
                symbol = request.args.get("symbol") or request.args.get("ticker")
                if not symbol or not str(symbol).strip():
                    return jsonify({"error": "symbol (or ticker) is required"}), 400
                ticker = str(symbol).strip().upper()
                ticker_id = self.db.get_or_create_options_ticker(ticker)
                if not ticker_id:
                    return jsonify({"error": "Unknown symbol: %s (add to public.tickers first)" % ticker}), 400
                exp_spec = request.args.get("expiration")
                if not exp_spec:
                    return jsonify({"error": "expiration is required (YYYYMMDD)"}), 400
                try:
                    expiration = int(str(exp_spec).strip().replace("-", ""))
                    if len(str(expiration)) != 8:
                        raise ValueError("invalid length")
                except ValueError:
                    return jsonify({"error": "expiration must be YYYYMMDD"}), 400
                strike_spec = request.args.get("strike")
                if strike_spec is None or strike_spec == "":
                    return jsonify({"error": "strike is required"}), 400
                try:
                    strike = float(strike_spec)
                except (ValueError, TypeError):
                    return jsonify({"error": "strike must be a number"}), 400
                side = request.args.get("side")
                if not side or str(side).strip().lower() not in ("call", "put"):
                    return jsonify({"error": "side is required (call or put)"}), 400
                side = str(side).strip().lower()
                date_spec = request.args.get("date")
                date_yyyymmdd = None
                if date_spec:
                    try:
                        date_yyyymmdd = int(str(date_spec).strip().replace("-", ""))
                        if len(str(date_yyyymmdd)) != 8:
                            raise ValueError("invalid length")
                    except ValueError:
                        return jsonify({"error": "date must be YYYYMMDD"}), 400
                time_str = request.args.get("time")
                if time_str is not None:
                    time_str = str(time_str).strip()
                quotes, contract_id = self.db.fetch_option_quotes(
                    ticker_id, expiration, strike, side,
                    date_yyyymmdd=date_yyyymmdd, time_str=time_str or None,
                )
                queried_date = date_yyyymmdd if date_yyyymmdd is not None else int(datetime.now().strftime("%Y%m%d"))
                payload = {
                    "symbol": ticker,
                    "expiration": expiration,
                    "strike": strike,
                    "side": side,
                    "date": queried_date,
                    "time_filter": time_str,
                    "count": len(quotes),
                    "quotes": quotes,
                }
                if contract_id is None:
                    payload["contract_found"] = False
                    payload["message"] = (
                        "No contract found for this symbol/expiration/strike/side. "
                        "Run POST /api/options/ingest/metadata for the symbol (and expiration range), then POST /api/options/ingest/quotes."
                    )
                else:
                    payload["contract_found"] = True
                    if len(quotes) == 0:
                        payload["message"] = (
                            "Contract exists but no quotes for this date. "
                            "Run POST /api/options/ingest/quotes for this symbol and date (and optional expiration)."
                        )
                return jsonify(payload), 200
            except Exception as e:
                logger.error("Fetch quotes error: %s", e, exc_info=True)
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/options/ingest/metadata", methods=["POST"])
        def ingest_metadata():
            try:
                data = request.get_json() or {}
                symbol = data.get("symbol") or data.get("ticker")
                if not symbol or not str(symbol).strip():
                    return jsonify({"error": "symbol (or ticker) is required"}), 400
                ticker = str(symbol).strip().upper()
                exp_spec = data.get("expiration")
                exp_range = parse_expiration_spec(exp_spec)
                err = validate_expiration_range_within_limit(exp_range)
                if err:
                    return jsonify({"error": err}), 400
                logger.info("Options metadata ingest: symbol=%s, expiration=%s", ticker, exp_spec)
                stats = self.run_metadata_ingest([ticker], exp_range=exp_range)
                return jsonify({"status": "completed", "stats": stats}), 200
            except Exception as e:
                logger.error("Options metadata ingest error: %s", e, exc_info=True)
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/options/ingest/quotes", methods=["POST"])
        def ingest_quotes():
            try:
                data = request.get_json() or {}
                symbol = data.get("symbol") or data.get("ticker")
                if not symbol or not str(symbol).strip():
                    return jsonify({"error": "symbol (or ticker) is required"}), 400
                ticker = str(symbol).strip().upper()
                date_spec = data.get("date")
                if not date_spec:
                    return jsonify({"error": "date is required (YYYYMMDD)"}), 400
                try:
                    date_int = int(str(date_spec).strip().replace("-", ""))
                    if len(str(date_int)) != 8:
                        raise ValueError("invalid length")
                except ValueError:
                    return jsonify({"error": "date must be YYYYMMDD"}), 400
                end_spec = data.get("end_date")
                if end_spec:
                    try:
                        end_int = int(str(end_spec).strip().replace("-", ""))
                        if len(str(end_int)) != 8:
                            raise ValueError("invalid length")
                        if end_int < date_int:
                            date_int, end_int = end_int, date_int
                    except ValueError:
                        return jsonify({"error": "end_date must be YYYYMMDD"}), 400
                else:
                    end_int = date_int
                err = validate_date_within_limit(date_int)
                if err:
                    return jsonify({"error": err}), 400
                err = validate_date_within_limit(end_int)
                if err:
                    return jsonify({"error": err}), 400
                ticker_id = self.db.get_or_create_options_ticker(ticker)
                if not ticker_id:
                    return jsonify({"error": "Unknown symbol: %s (add to public.tickers first)" % ticker}), 400
                # Require at least one expiration for this ticker; do not require quote_dates for requested dates
                expirations = self.db.fetch_option_expirations(ticker_id)
                if not expirations:
                    exp_lo = date_int
                    exp_hi = end_int
                    base = request.url_root.rstrip("/") or "http://localhost:8081"
                    curl_metadata = "curl -X POST %s/api/options/ingest/metadata -H 'Content-Type: application/json' -d '{\"symbol\": \"%s\", \"expiration\": \"%s:%s\"}'" % (base, ticker, exp_lo, exp_hi)
                    curl_quotes = "curl -X POST %s/api/options/ingest/quotes -H 'Content-Type: application/json' -d '{\"symbol\": \"%s\", \"date\": \"%s\", \"end_date\": \"%s\"}'" % (base, ticker, date_int, end_int)
                    return jsonify({
                        "error": "No options metadata for this symbol. Run metadata ingest first, then quotes ingest.",
                        "ingest_metadata_first": {
                            "endpoint": "POST /api/options/ingest/metadata",
                            "body": {"symbol": ticker, "expiration": "%s:%s" % (exp_lo, exp_hi)},
                        },
                        "run_metadata_first": curl_metadata,
                        "run_quotes_after": curl_quotes,
                        "copy_paste_tip": "To get a command without escaped quotes, run: jq -r '.run_metadata_first' (or .run_quotes_after) on this JSON.",
                    }), 409
                requested_dates = set()
                current = datetime.strptime(str(date_int), "%Y%m%d").date()
                end_d = datetime.strptime(str(end_int), "%Y%m%d").date()
                while current <= end_d:
                    requested_dates.add(int(current.strftime("%Y%m%d")))
                    current += timedelta(days=1)
                # Parse expiration: optional. Omit or "*" or "all" = send "*" to external API (all expirations, one request per date). Single YYYYMMDD = one expiration only.
                exp_spec = (data.get("expiration") or "").strip()
                if exp_spec and exp_spec.upper() not in ("*", "ALL"):
                    try:
                        single_exp = int(str(exp_spec).replace("-", ""))
                        if len(str(single_exp)) != 8:
                            raise ValueError("invalid length")
                        expiration_param = single_exp
                    except ValueError:
                        return jsonify({"error": "expiration must be YYYYMMDD, or omit / \"*\" for all expirations"}), 400
                else:
                    expiration_param = None  # DataCollector will send "*" to the external API
                total_quotes = 0
                dates_processed = []
                for d in sorted(requested_dates):
                    try:
                        n = self.datacollector.theta_option_quotes(
                            ticker, str(d), expiration=expiration_param, base_url=self.base_url
                        )
                        total_quotes += n
                        dates_processed.append({"date": d, "quotes_inserted": n})
                    except Exception as e:
                        logger.error("Quote ingest failed for %s %s: %s", ticker, d, e, exc_info=True)
                        return jsonify({"error": "Quote ingest failed for date %s: %s" % (d, e)}), 500
                return jsonify({
                    "status": "completed",
                    "symbol": ticker,
                    "dates_processed": len(dates_processed),
                    "quotes_inserted": total_quotes,
                    "by_date": dates_processed,
                }), 200
            except Exception as e:
                logger.error("Options quote ingest error: %s", e, exc_info=True)
                return jsonify({"error": str(e)}), 500

    def initialize(self):
        self.db = DatabaseConnection()
        self.datacollector = DataCollector(self.db)
        logger.info("Options metadata service initialized (BASE_URL=%s)", self.base_url)

    def _get_ticker_list(self) -> List[str]:
        if not self.db:
            return []
        try:
            with self.db.connection.cursor() as cursor:
                cursor.execute("SELECT DISTINCT ticker FROM public.tickers ORDER BY ticker")
                return [row[0].upper() for row in cursor.fetchall() if row[0]]
        except Exception as e:
            logger.error("Failed to load tickers: %s", e, exc_info=True)
            return []

    def run_metadata_ingest(
        self,
        tickers: List[str],
        exp_range: Optional[Tuple[int, int]] = None,
    ) -> Dict:
        """
        For each ticker: get ticker_id, fetch expirations -> options.expirations.
        For each expiration: fetch quote_dates -> options.quote_dates, strikes -> options.strikes.
        """
        stats = {
            "tickers_processed": 0,
            "expirations_inserted": 0,
            "quote_dates_inserted": 0,
            "strikes_inserted": 0,
            "by_ticker": [],
            "errors": [],
        }
        for ticker in tickers:
            ticker_stats = {"ticker": ticker, "ticker_id": None, "expirations": 0, "quote_dates": 0, "strikes": 0, "per_expiration": []}
            try:
                ticker_id = self.db.get_or_create_options_ticker(ticker)
                if not ticker_id:
                    stats["errors"].append("No ticker_id for %s" % ticker)
                    continue
                ticker_stats["ticker_id"] = ticker_id
                logger.info("--- %s (ticker_id=%s) ---", ticker, ticker_id)

                expirations = self.datacollector.theta_option_list_expirations(ticker, base_url=self.base_url)
                if not expirations:
                    logger.warning("No expirations from ThetaData for %s", ticker)
                    stats["by_ticker"].append(ticker_stats)
                    continue
                cutoff = options_cutoff_yyyymmdd()
                expirations = [e for e in expirations if e >= cutoff]
                if exp_range:
                    exp_min, exp_max = exp_range
                    expirations = [e for e in expirations if exp_min <= e <= exp_max]
                if not expirations:
                    logger.info("No expirations in range for %s", ticker)
                    stats["by_ticker"].append(ticker_stats)
                    continue

                self.db.insert_expiration_dates(ticker_id, expirations)
                ticker_stats["expirations"] = len(expirations)
                stats["expirations_inserted"] += len(expirations)
                logger.info("Inserted %s expirations for %s", len(expirations), ticker)

                for exp in expirations:
                    qd = self.datacollector.theta_option_list_dates_quote(ticker, str(exp), base_url=self.base_url)
                    if qd:
                        self.db.insert_option_quote_dates(ticker_id, exp, qd)
                        ticker_stats["quote_dates"] += len(qd)
                        stats["quote_dates_inserted"] += len(qd)
                    strikes = self.datacollector.theta_option_list_strikes(ticker, str(exp), base_url=self.base_url)
                    if strikes:
                        self.db.insert_option_strikes(ticker_id, exp, strikes)
                        ticker_stats["strikes"] += len(strikes)
                        stats["strikes_inserted"] += len(strikes)
                    per_exp = {"expiration": exp, "quote_dates": len(qd) if qd else 0, "strikes": len(strikes) if strikes else 0}
                    ticker_stats["per_expiration"].append(per_exp)
                    logger.info("  expiration %s: quote_dates=%s, strikes=%s", exp, per_exp["quote_dates"], per_exp["strikes"])

                stats["tickers_processed"] += 1
                stats["by_ticker"].append(ticker_stats)
                logger.info("Summary for %s: expirations=%s, quote_dates=%s, strikes=%s",
                            ticker, ticker_stats["expirations"], ticker_stats["quote_dates"], ticker_stats["strikes"])
            except Exception as e:
                logger.error("Error processing %s: %s", ticker, e, exc_info=True)
                stats["errors"].append("%s: %s" % (ticker, e))
                stats["by_ticker"].append(ticker_stats)

        logger.info("=== Ingest complete: tickers=%s, expirations=%s, quote_dates=%s, strikes=%s, errors=%s",
                    stats["tickers_processed"], stats["expirations_inserted"],
                    stats["quote_dates_inserted"], stats["strikes_inserted"], len(stats["errors"]))
        return stats

    def start_scheduler(self):
        """Run metadata ingest every Sunday at OPTIONS_METADATA_SCHEDULE_TIME for upcoming expirations."""
        import schedule
        schedule_time = os.getenv("OPTIONS_METADATA_SCHEDULE_TIME", "20:00")

        def scheduled_metadata_job():
            logger.info("Scheduled options metadata refresh started (Sunday)")
            tickers = self._get_ticker_list()
            if not tickers:
                return
            today_int = int(datetime.utcnow().date().strftime("%Y%m%d"))
            end_int = int((datetime.utcnow().date() + timedelta(days=60)).strftime("%Y%m%d"))
            exp_range = (today_int, end_int)
            self.run_metadata_ingest(tickers, exp_range=exp_range)

        try:
            hour, minute = map(int, schedule_time.split(":"))
            schedule.every().sunday.at(schedule_time).do(scheduled_metadata_job)
            logger.info("Options metadata scheduler: every Sunday at %s (upcoming 60 days)", schedule_time)
        except (ValueError, AttributeError) as e:
            logger.warning("Invalid OPTIONS_METADATA_SCHEDULE_TIME, using Sunday 20:00: %s", e)
            schedule.every().sunday.at("20:00").do(scheduled_metadata_job)

        def scheduler_loop():
            while not self.shutdown_requested:
                try:
                    schedule.run_pending()
                except Exception as e:
                    logger.error("Scheduler error: %s", e)
                time.sleep(60)

        threading.Thread(target=scheduler_loop, daemon=True).start()

    def start_api_server(self, host="0.0.0.0", port=8081):
        def run_server():
            try:
                from waitress import serve
                logger.info("Options API (waitress) on %s:%s", host, port)
                serve(self.app, host=host, port=port, threads=4, channel_timeout=120)
            except ImportError:
                self.app.run(host=host, port=port, debug=False, use_reloader=False)
            except Exception as e:
                logger.error("Server error: %s", e)
                self.app.run(host=host, port=port, debug=False, use_reloader=False)
        t = threading.Thread(target=run_server, daemon=True)
        t.start()
        logger.info("Options API listening on %s:%s", host, port)

    def run(self):
        self.initialize()
        port = int(os.getenv("API_PORT", "8081"))
        schedule_enabled = os.getenv("OPTIONS_SCHEDULE_ENABLED", "true").lower() == "true"
        if schedule_enabled:
            self.start_scheduler()
        self.start_api_server(port=port)
        logger.info("Options metadata service running. Ctrl+C to stop.")
        try:
            while not self.shutdown_requested:
                time.sleep(30)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt")
        finally:
            self.shutdown()

    def shutdown(self):
        self.shutdown_requested = True
        if self.db:
            self.db.close()
        logger.info("Options service shut down.")


service = None


def signal_handler(signum, frame):
    global service
    logger.info("Signal %s, shutting down.", signum)
    if service:
        service.shutdown()
    sys.exit(0)


def main():
    if len(sys.argv) >= 2 and sys.argv[1] in ("-h", "--help"):
        print(get_help_text())
        sys.exit(0)
    global service
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    for log_dir in ["/app/logs", os.path.join(os.path.dirname(__file__), "logs")]:
        try:
            os.makedirs(log_dir, exist_ok=True)
            break
        except (OSError, PermissionError):
            pass
    logger.info("Starting options metadata ingestion service")
    service = OptionsIngestionService()
    service.run()


if __name__ == "__main__":
    main()
