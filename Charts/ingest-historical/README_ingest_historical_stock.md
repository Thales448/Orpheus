# Historical Stock Quote Ingestion Service

This service checks if a ticker has quote data for each day in the past year, and if not, fetches and inserts the missing data into the database.

## Features

- **Automatic Data Gap Detection**: Checks for missing quote data for each trading day
- **Backfill Missing Data**: Automatically fetches and inserts missing data from Theta Terminal API
- **Kubernetes Ready**: Designed to run as a containerized service in Kubernetes
- **Flexible Execution Modes**: Run once or continuously with configurable intervals
- **Health Checks**: Built-in health check support for Kubernetes liveness/readiness probes
- **Graceful Shutdown**: Handles SIGTERM/SIGINT signals for clean shutdowns

## Usage

### Local Execution

```bash
# Run once for a specific ticker
python ingest_historical_stock.py SPY

# Or set environment variables
export TICKER=SPY
export DAYS_BACK=365
export RUN_MODE=once
python ingest_historical_stock.py
```

### Environment Variables

- `TICKER` (required): Stock ticker symbol (e.g., "SPY")
- `DAYS_BACK` (optional, default: 365): Number of days to look back
- `RUN_MODE` (optional, default: "once"): Execution mode
  - `once`: Run once and exit
  - `continuous`: Run continuously with interval
- `INTERVAL_HOURS` (optional, default: 24): Hours between runs (only used in continuous mode)
- `LOG_LEVEL` (optional, default: "INFO"): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Database connection variables (required):
  - `DB_NAME`: Database name
  - `DB_USER`: Database user
  - `DB_PASSWORD`: Database password
  - `DB_HOST`: Database host
  - `DB_PORT`: Database port

## Docker Build

```bash
# Build the Docker image
docker build -f Dockerfile.ingest_historical -t ingest-historical-stock:latest .

# Run the container
docker run --rm \
  -e TICKER=SPY \
  -e DB_NAME=your_db \
  -e DB_USER=your_user \
  -e DB_PASSWORD=your_password \
  -e DB_HOST=your_host \
  -e DB_PORT=5432 \
  ingest-historical-stock:latest
```

## Kubernetes Deployment

### Option 1: Deployment (Long-running service)

Deploy as a long-running service that runs continuously:

```bash
kubectl apply -f k8s/ingest_historical_stock_deployment.yaml
```

### Option 2: CronJob (Scheduled runs)

Deploy as a CronJob that runs on a schedule (default: daily at 2 AM UTC):

```bash
# The CronJob is included in the same YAML file
kubectl apply -f k8s/ingest_historical_stock_deployment.yaml
```

To customize the schedule, edit the `schedule` field in the CronJob spec:
```yaml
spec:
  schedule: "0 2 * * *"  # Cron expression: minute hour day month weekday
```

### Configuration

Before deploying, update the following in `k8s/ingest_historical_stock_deployment.yaml`:

1. **Image registry**: Update `your-registry/ingest-historical-stock:latest` with your container registry
2. **Database credentials**: Update the `db-config` ConfigMap and `db-credentials` Secret
3. **Ticker**: Update the `TICKER` environment variable if you want a different default

### Secrets and ConfigMaps

The deployment expects:
- **ConfigMap** `db-config` with keys: `db-host`, `db-port`
- **Secret** `db-credentials` with keys: `db-name`, `db-user`, `db-password`

Create them if they don't exist:

```bash
# Create ConfigMap
kubectl create configmap db-config \
  --from-literal=db-host=your-db-host \
  --from-literal=db-port=5432

# Create Secret
kubectl create secret generic db-credentials \
  --from-literal=db-name=your-database-name \
  --from-literal=db-user=your-db-user \
  --from-literal=db-password=your-db-password
```

## How It Works

1. **Date Range Calculation**: Calculates the date range for the past N days (default: 365)
2. **Trading Days**: Generates a list of trading days (excludes weekends)
3. **Data Check**: For each trading day, checks if quote data exists in the database
4. **Data Fetching**: If data is missing, fetches it from Theta Terminal API using `theta_stocks_quote()`
5. **Data Insertion**: Inserts the fetched data into the `stocks.quote` table using `insert_stocks_quote()`
6. **Health Checks**: Updates a healthcheck file periodically for Kubernetes monitoring

## Logging

Logs are written to:
- **Console**: Standard output (for Kubernetes logs)
- **File**: `/app/logs/ingest_historical_stock.log` (inside container)

View logs in Kubernetes:
```bash
# For Deployment
kubectl logs -f deployment/ingest-historical-stock

# For CronJob
kubectl logs -f job/ingest-historical-stock-cron-<timestamp>
```

## Error Handling

- **API Errors**: If the API returns no data (HTTP 472), the service logs a warning and continues
- **Database Errors**: Database connection errors are logged and the service exits with error code
- **Graceful Shutdown**: The service handles SIGTERM/SIGINT signals and stops processing gracefully

## Performance Considerations

- **Rate Limiting**: Includes a 0.5 second delay between API calls to avoid overwhelming the API
- **Batch Processing**: Data is inserted in batches for efficiency
- **Resource Limits**: Default Kubernetes resource limits are set (512Mi-2Gi memory, 200m-1000m CPU)

## Monitoring

The service includes:
- **Health Check File**: `/tmp/healthcheck` is updated periodically
- **Liveness Probe**: Checks that the healthcheck file exists and was updated recently
- **Readiness Probe**: Checks that the healthcheck file exists

## Troubleshooting

### Service exits immediately
- Check database connection variables are set correctly
- Verify database is accessible from the Kubernetes cluster
- Check logs for connection errors

### No data being fetched
- Verify Theta Terminal API is accessible
- Check API endpoint configuration in `DataCollector.py`
- Review logs for API errors (HTTP 472 means no data available for that date)

### High memory usage
- Reduce `DAYS_BACK` if processing many days
- Process one ticker at a time
- Adjust Kubernetes resource limits

## Development

To test locally:
```bash
# Set up environment
export TICKER=SPY
export DAYS_BACK=7  # Test with just 7 days
export RUN_MODE=once

# Run
python ingest_historical_stock.py
```


