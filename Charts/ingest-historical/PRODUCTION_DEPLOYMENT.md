# Production Deployment Guide

This guide explains how to deploy the Historical Stock Ingestion Service in production.

## Production WSGI Server

The service now uses **Waitress** as the production WSGI server by default, which eliminates the Flask development server warning.

### Current Setup (Recommended)

The service automatically uses Waitress when `USE_PRODUCTION_SERVER=true` (default). No changes needed!

```bash
# The service will automatically use Waitress
python ingest_historical_stock.py
```

### Environment Variables

- `USE_PRODUCTION_SERVER=true` (default) - Uses Waitress production server
- `USE_PRODUCTION_SERVER=false` - Uses Flask development server (not recommended for production)

## Deployment Options

### Option 1: Full Service (Recommended for Single Instance)

Run the complete service with scheduler + API:

```bash
python ingest_historical_stock.py
```

**Docker:**
```bash
docker build -f Dockerfile.ingest_historical -t ingest-service .
docker run -p 8080:8080 ingest-service
```

### Option 2: WSGI Entry Point (For Load Balancing)

If you need to run multiple API instances behind a load balancer, use the WSGI entry point:

**With Gunicorn:**
```bash
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -b 0.0.0.0:8080 --timeout 120 --access-logfile - wsgi:app
```

**With Waitress:**
```bash
waitress-serve --host=0.0.0.0 --port=8080 --threads=4 wsgi:app
```

**Note:** The WSGI entry point (`wsgi.py`) only exposes the Flask API. The scheduler runs in the main service process.

### Option 3: Docker with Gunicorn

Update `Dockerfile.ingest_historical`:

```dockerfile
# Install gunicorn
RUN pip install --no-cache-dir gunicorn

# Use gunicorn instead
ENTRYPOINT ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "--timeout", "120", "wsgi:app"]
```

## Production Checklist

### 1. Environment Variables

Set production environment variables:

```bash
export USE_PRODUCTION_SERVER=true
export LOG_LEVEL=INFO
export API_PORT=8080
export BASE_URL=http://your-theta-api:25503/v3
export LOOKBACK=1h
export SCHEDULE=1m
export REPAIR=true
export TICKER_SOURCE=db
```

### 2. Security

- ✅ Service runs as non-root user (Dockerfile already configured)
- ✅ Health check endpoint configured
- ✅ Proper logging configured
- ⚠️ Consider adding authentication for API endpoints in production
- ⚠️ Use HTTPS/TLS in production (via reverse proxy like nginx)

### 3. Monitoring

- Health check: `GET /health`
- Status: `GET /api/v1/status`
- Logs: `GET /logs`
- Metrics: Consider adding Prometheus metrics endpoint

### 4. Reverse Proxy (Recommended)

Use nginx or similar reverse proxy:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. Process Management

**Systemd Service (Linux):**

Create `/etc/systemd/system/ingest-stock.service`:

```ini
[Unit]
Description=Historical Stock Ingestion Service
After=network.target postgresql.service

[Service]
Type=simple
User=appuser
WorkingDirectory=/app
Environment="USE_PRODUCTION_SERVER=true"
Environment="LOG_LEVEL=INFO"
ExecStart=/usr/bin/python3 /app/ingest_historical_stock.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ingest-stock
sudo systemctl start ingest-stock
```

**Docker Compose:**

```yaml
version: '3.8'
services:
  ingest-stock:
    build:
      context: .
      dockerfile: Dockerfile.ingest_historical
    ports:
      - "8080:8080"
    environment:
      - USE_PRODUCTION_SERVER=true
      - LOG_LEVEL=INFO
      - BASE_URL=http://theta-api:25503/v3
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8080/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Performance Tuning

### Waitress Configuration

The service uses Waitress with these defaults:
- Threads: 4
- Channel timeout: 120 seconds

To customize, modify `start_api_server()` in `ingest_historical_stock.py`:

```python
serve(self.app, host=host, port=port, threads=8, channel_timeout=120)
```

### Gunicorn Configuration

For high-traffic deployments:

```bash
gunicorn -w 8 -b 0.0.0.0:8080 \
  --timeout 120 \
  --worker-class sync \
  --worker-connections 1000 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --access-logfile - \
  --error-logfile - \
  wsgi:app
```

## Troubleshooting

### Warning Still Appears

If you still see the development server warning:

1. Check `USE_PRODUCTION_SERVER` is set to `true`
2. Verify `waitress` is installed: `pip install waitress`
3. Check logs for any import errors

### Service Won't Start

1. Check database connectivity
2. Verify all environment variables are set
3. Check logs: `GET /logs` or check log files

### High Memory Usage

1. Reduce `parallel_workers` if processing many tickers
2. Adjust Waitress/Gunicorn worker count
3. Monitor with: `GET /api/v1/status`

## Verification

After deployment, verify production server is running:

```bash
# Check health
curl http://localhost:8080/health

# Check status (should not show development server warning in logs)
curl http://localhost:8080/api/v1/status

# Check logs (should not see "WARNING: This is a development server")
curl http://localhost:8080/logs?limit=10
```

The service is now production-ready! 🚀



