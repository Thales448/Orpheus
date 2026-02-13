# Historical Stock Ingestion Service Documentation

## Overview

The Historical Stock Ingestion Service is a long-running service that:
- Fetches historical stock quote data from Theta Terminal API
- Stores data in PostgreSQL/TimescaleDB
- Runs scheduled jobs to keep data up-to-date
- Provides REST API for on-demand data processing
- Supports flexible lookback periods (from 1 minute to 700 days)
- Uses batch database checks and parallel processing for efficiency

## How It Works

### Architecture

1. **Service Initialization**
   - Connects to PostgreSQL database
   - Initializes DataCollector for API calls
   - Loads ticker list from configured source (database, env var, or config file)
   - Sets up Flask API server with production WSGI (Waitress)

2. **Scheduled Processing**
   - Runs periodic jobs based on `schedule` config (default: daily at 4:15 PM)
   - For each run, processes all tickers from the watchlist
   - Checks database for existing data for the lookback period (default: 1 day)
   - Fetches missing data from Theta Terminal API (if `repair=true`)
   - Updates healthcheck file for monitoring

3. **Data Processing Flow**
   - Batch checks database for all tickers and dates at once (efficient)
   - Identifies missing ticker-date combinations
   - Fetches missing data in parallel (configurable workers)
   - Inserts data into `stocks.quote` table
   - Verifies data was inserted successfully

4. **API Endpoints**
   - Provides REST API for on-demand processing
   - Supports configuration updates
   - Returns detailed status and logs

### Key Features

- **Flexible Time Ranges**: Supports lookback from 1 minute to 700 days
- **Smart Scheduling**: Configurable schedule from 1 minute to 7 days
- **Repair Mode**: Can check database only (`repair=false`) or fetch missing data (`repair=true`)
- **Production Ready**: Uses Waitress WSGI server (no Flask dev server warnings)
- **Efficient**: Batch database checks and parallel API calls
- **Observable**: Health checks, status endpoint, and log access

---

## API Endpoints

### Health Check

**GET** `/health`

Check if the service is running.

**Response:**
```json
{
  "status": "healthy"
}
```

**Example:**
```bash
curl http://localhost:8080/health
```

---

### Help (Endpoints & Examples)

**GET** `/help` or **GET** `/api/v1/help`

Returns all available endpoints, short descriptions, and example `curl` commands. The base URL in examples matches the request host. Default is JSON; use query `?format=text` for human-readable plain text.

**Response:**
```json
{
  "service": "Historical Stock Ingestion Service",
  "description": "Fetches historical stock quote data from Theta Terminal API...",
  "endpoints": [
    {
      "method": "GET",
      "path": "/health",
      "description": "Check if the service is running.",
      "example": "curl http://localhost:8080/health"
    },
    ...
  ]
}
```

**Examples:**
```bash
# JSON (default)
curl http://localhost:8080/help

# Human-readable plain text
curl "http://localhost:8080/help?format=text"
```

---

### Get Service Status

**GET** `/api/v1/status`

Get current service status, configuration, and ticker list.

**Response:**
```json
{
  "status": "running",
  "last_scheduled_run": "2025-12-22T23:26:04",
  "next_scheduled_run": "2025-12-22T23:27:04",
  "config": {
    "base_url": "http://192.168.1.132:25503/v3",
    "lookback": "1d",
    "schedule": "1d",
    "repair": true,
    "ticker_source": "db",
    "parallel_workers": 2,
    "schedule_enabled": true,
    "schedule_time": "16:15"
  },
  "ticker_count": 3,
  "tickers": ["AAPL", "HD", "QQQ"]
}
```

**Example:**
```bash
curl http://localhost:8080/api/v1/status
```

---

### Process Single Ticker

**POST** `/api/v1/process-ticker`

Process a single ticker on demand. Can override lookback period and repair setting.

**Request Body:**
```json
{
  "ticker": "AAPL",
  "lookback": "1d",
  "repair": false
}
```

**Parameters:**
- `ticker` (required): Ticker symbol (e.g., "AAPL", "HD")
- `lookback` (optional): Time period to look back. Formats:
  - `"40d"` - 40 days
  - `"1h"` - 1 hour
  - `"30m"` - 30 minutes
  - `"700d"` - 700 days
  - Integer (e.g., `40`) - converted to days
- `repair` (optional): If `false`, only checks database, doesn't fetch from API. If `true` (default), fetches missing data.

**Response:**
```json
{
  "status": "completed",
  "ticker": "AAPL",
  "stats": {
    "ticker": "AAPL",
    "total_days": 29,
    "days_with_data": 0,
    "days_fetched": 0,
    "days_failed": 29,
    "good_data": [],
    "no_data_dates": [
      "20251112",
      "20251113",
      "20251114",
      "20251117",
      "20251118",
      "20251119",
      "20251120",
      "20251121",
      "20251124",
      "20251125",
      "20251126",
      "20251127",
      "20251128",
      "20251201",
      "20251202",
      "20251203",
      "20251204",
      "20251205",
      "20251208",
      "20251209",
      "20251210",
      "20251211",
      "20251212",
      "20251215",
      "20251216",
      "20251217",
      "20251218",
      "20251219",
      "20251222"
    ],
    "errors": []
  }
}
```

**Example:**
```bash
# Process with default lookback
curl -X POST http://localhost:8080/api/v1/process-ticker \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'

# Process with custom lookback (40 days)
curl -X POST http://localhost:8080/api/v1/process-ticker \
  -H "Content-Type: application/json" \
  -d '{"ticker": "HD", "lookback": 40}'

# Check only (don't fetch from API)
curl -X POST http://localhost:8080/api/v1/process-ticker \
  -H "Content-Type: application/json" \
  -d '{"ticker": "HD", "lookback": "40d", "repair": false}'
```

---

### Process All Tickers

**POST** `/api/v1/process-all`

Process all tickers from the configured source (watchlist, env var, or config file).

**Request Body:**
```json
{
  "lookback": "1d",
  "repair": true
}
```

**Parameters:**
- `lookback` (optional): Time period to look back (same format as process-ticker)
- `repair` (optional): If `false`, only checks database

**Response:**
```json
{
  "status": "completed",
  "stats": {
    "total_tickers": 3,
    "total_tasks": 0,
    "completed_tasks": 0,
    "failed_tasks": 0,
    "ticker_stats": {}
  }
}
```

**Example:**
```bash
# Process all with default lookback
curl -X POST http://localhost:8080/api/v1/process-all \
  -H "Content-Type: application/json" \
  -d '{}'

# Process all with custom lookback
curl -X POST http://localhost:8080/api/v1/process-all \
  -H "Content-Type: application/json" \
  -d '{"lookback": "7d"}'
```

---

### Get Configuration

**GET** `/api/v1/config`

Get current service configuration.

**Response:**
```json
{
  "base_url": "http://192.168.1.132:25503/v3",
  "lookback": "1d",
  "schedule": "1d",
  "repair": true,
  "ticker_source": "db",
  "parallel_workers": 2,
  "schedule_enabled": true,
  "schedule_time": "16:15"
}
```

**Example:**
```bash
curl http://localhost:8080/api/v1/config
```

---

### Update Configuration

**POST** `/api/v1/config`

Update service configuration. Only provided fields are updated.

**Request Body:**
```json
{
  "base_url": "http://192.168.1.132:25503/v3",
  "lookback": "1d",
  "schedule": "1d",
  "repair": false,
  "parallel_workers": 4
}
```

**Parameters:**
- `base_url`: Theta Terminal API base URL
- `lookback`: Default lookback period (e.g., "1d", "30m", "700d")
- `schedule`: Schedule interval (e.g., "1m", "1h", "7d")
- `repair`: If `false`, only checks database
- `ticker_source`: Source for ticker list ("db", "env", "config_file")
- `parallel_workers`: Number of parallel workers for fetching
- `schedule_enabled`: Enable/disable scheduled jobs
- `schedule_time`: Legacy schedule time (HH:MM format)

**Response:**
```json
{
  "status": "updated",
  "config": {
    "base_url": "http://192.168.1.132:25503/v3",
    "lookback": "1d",
    "schedule": "1d",
    "repair": false,
    "ticker_source": "db",
    "parallel_workers": 4,
    "schedule_enabled": true,
    "schedule_time": "16:15"
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:8080/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "lookback": "1d",
    "schedule": "1d",
    "schedule_time": "16:15",
    "repair": true
  }'
```

---

### Get Logs

**GET** `/logs`

Get session logs from memory. Useful for debugging and monitoring.

**Query Parameters:**
- `level` (optional): Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `limit` (optional): Limit number of entries returned

**Response:**
```json
{
  "total_entries": 150,
  "logs": [
    {
      "timestamp": "2025-12-22 23:26:04,717",
      "level": "INFO",
      "message": "Scheduled job started (lookback=1d)",
      "module": "ingest_historical_stock",
      "funcName": "scheduled_job",
      "lineno": 896
    },
    {
      "timestamp": "2025-12-22 23:26:04,718",
      "level": "INFO",
      "message": "Tickers: AAPL, HD, QQQ (3 total)",
      "module": "ingest_historical_stock",
      "funcName": "process_all_tickers",
      "lineno": 790
    }
  ]
}
```

**Examples:**
```bash
# Get all logs
curl http://localhost:8080/logs

# Get only ERROR logs
curl http://localhost:8080/logs?level=ERROR

# Get last 50 logs
curl http://localhost:8080/logs?limit=50

# Get last 20 ERROR logs
curl http://localhost:8080/logs?level=ERROR&limit=20
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:25503/v3` | Theta Terminal API base URL |
| `LOOKBACK` | `1d` | Default lookback period (1m to 700d) |
| `SCHEDULE` | `1d` | Schedule interval (1m to 7d). For 1d, runs at SCHEDULE_TIME |
| `REPAIR` | `true` | If false, only checks DB, doesn't fetch |
| `TICKER_SOURCE` | `db` | Source: "db", "env", or "config_file" |
| `PARALLEL_WORKERS` | `2` | Number of parallel workers |
| `SCHEDULE_ENABLED` | `true` | Enable scheduled jobs |
| `SCHEDULE_TIME` | `16:15` | Daily schedule time (HH:MM). Used when schedule=1d |
| `API_PORT` | `8080` | API server port |
| `USE_PRODUCTION_SERVER` | `true` | Use Waitress (production WSGI) |
| `LOG_LEVEL` | `INFO` | Logging level |

### Ticker Sources

#### 1. Database (Default)
```bash
export TICKER_SOURCE=db
```
Queries `public.alpha_list` table for ticker IDs, joins with `public.tickers` to get symbols.

#### 2. Environment Variable
```bash
export TICKER_SOURCE=env
export TICKER_LIST="AAPL,HD,QQQ"
```

#### 3. Config File
```bash
export TICKER_SOURCE=config_file
```
Reads from `tickers.json` in the service directory:
```json
{
  "tickers": ["AAPL", "HD", "QQQ"]
}
```

---

## Time Format Examples

### Lookback Periods

- `"1m"` - 1 minute
- `"30m"` - 30 minutes
- `"1h"` - 1 hour
- `"1d"` - 1 day
- `"7d"` - 7 days
- `"40d"` - 40 days
- `"700d"` - 700 days

### Schedule Intervals

- `"1m"` - Every 1 minute
- `"5m"` - Every 5 minutes
- `"1h"` - Every 1 hour
- `"1d"` - Every 1 day at time specified by `SCHEDULE_TIME` (default: 4:15 PM / 16:15)
- `"7d"` - Every 7 days

**Note:** When `schedule=1d`, the job runs daily at the time specified by `SCHEDULE_TIME` (default: 16:15 / 4:15 PM). This ensures data is fetched after market close.

---

## Usage Examples

### Basic Setup

```bash
# Set environment variables
export BASE_URL="http://192.168.1.132:25503/v3"
export LOOKBACK="1d"
export SCHEDULE="1d"
export SCHEDULE_TIME="16:15"
export TICKER_SOURCE="db"
export REPAIR="true"

# Run service
python ingest_historical_stock.py
```

### Check Data Availability (No Fetching)

```bash
# Set repair to false
export REPAIR=false

# Or via API
curl -X POST http://localhost:8080/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{"repair": false}'

# Process ticker (will only check, not fetch)
curl -X POST http://localhost:8080/api/v1/process-ticker \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "lookback": "40d"}'
```

### Process Historical Data

```bash
# Process last 700 days for a ticker
curl -X POST http://localhost:8080/api/v1/process-ticker \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "lookback": "700d"}'

# Process all tickers for last 7 days
curl -X POST http://localhost:8080/api/v1/process-all \
  -H "Content-Type: application/json" \
  -d '{"lookback": "7d"}'
```

### Monitor Service

```bash
# Check health
curl http://localhost:8080/health

# Get status
curl http://localhost:8080/api/v1/status

# View recent logs
curl http://localhost:8080/logs?limit=20

# View only errors
curl http://localhost:8080/logs?level=ERROR
```

---

## Response Format Details

### Process Ticker Response

The `stats` object contains:

- `ticker`: Ticker symbol processed
- `total_days`: Total trading days in lookback period
- `days_with_data`: Number of days that already had data
- `days_fetched`: Number of days successfully fetched
- `days_failed`: Number of days that failed
- `good_data`: Array of dates (YYYYMMDD) that have data
- `no_data_dates`: Array of dates that don't have data
- `errors`: Array of actual errors (not just missing data)

**Example with data:**
```json
{
  "stats": {
    "ticker": "AAPL",
    "total_days": 5,
    "days_with_data": 3,
    "days_fetched": 2,
    "days_failed": 0,
    "good_data": ["20251218", "20251219", "20251220", "20251221", "20251222"],
    "no_data_dates": [],
    "errors": []
  }
}
```

**Example with missing data:**
```json
{
  "stats": {
    "ticker": "HD",
    "total_days": 29,
    "days_with_data": 0,
    "days_fetched": 0,
    "days_failed": 29,
    "good_data": [],
    "no_data_dates": ["20251112", "20251113", "20251114", ...],
    "errors": []
  }
}
```

---

## Production Deployment

The service uses **Waitress** production WSGI server by default (no Flask dev server warnings).

See `PRODUCTION_DEPLOYMENT.md` for detailed deployment instructions.

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run service (automatically uses Waitress)
python ingest_historical_stock.py
```

---

## Troubleshooting

### Service Won't Start

1. Check database connectivity
2. Verify environment variables
3. Check logs: `GET /logs`

### No Data Being Fetched

1. Check `repair` setting (must be `true` to fetch)
2. Verify `base_url` points to correct Theta Terminal API
3. Check API connectivity
4. Review logs for errors

### Missing Tickers

1. Verify ticker source configuration
2. For `db` source, check `public.alpha_list` table has entries
3. For `env` source, check `TICKER_LIST` environment variable

---

## Logging

The service provides concise, informative logs:

```
Scheduled job started (lookback=1d)
Tickers: AAPL, HD, QQQ (3 total)
Status: AAPL: complete | HD: 2 missing (20251220, 20251221) | QQQ: complete
Fetching 2 missing date(s)
Result: 2 fetched, 0 failed
```

Logs show:
- Which tickers are being processed
- Per-ticker status (complete or missing dates)
- Fetching progress
- Final results

---

## Database Schema

Data is stored in:
- **Table**: `stocks.quote`
- **Ticker Reference**: `public.tickers`
- **Watchlist**: `public.alpha_list` (contains `ticker_id` references)

---

## Notes

- The service automatically skips weekends
- Minute-level intervals fetch only the specified time range (e.g., past 1 minute)
- Day-level intervals fetch full trading days
- Parallel processing improves performance for multiple tickers
- Healthcheck file is updated every 30 seconds for monitoring
