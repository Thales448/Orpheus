FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
        websockets>=11.0 \
        python-dotenv \
        pytz \
        waitress>=2.1.0

# Copy only necessary application files
# Note: config.py and .env are NOT included - they should be mounted at runtime
COPY DatabaseConnection.py .
COPY DataCollector.py .
COPY ingest_historical_stock.py .

# Create directories for logs and healthcheck
RUN mkdir -p /app/logs /tmp && \
    chmod 777 /tmp

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /tmp
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO \
    RUN_MODE=service \
    DAYS_BACK=365 \
    API_PORT=8080 \
    PARALLEL_WORKERS=2 \
    SCHEDULE_ENABLED=true \
    SCHEDULE_TIME=08:00 \
    TICKER_SOURCE=env

# Expose API port
EXPOSE 8080

# Health check - verifies service is running and updating healthcheck file
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)" || exit 1

# Run the ingestion service
# Use production mode by default (can be overridden with USE_PRODUCTION_SERVER=false)
ENV USE_PRODUCTION_SERVER=true

# Option 1: Run as full service (includes scheduler + API)
ENTRYPOINT ["python", "ingest_historical_stock.py"]

# Option 2: Run with gunicorn (uncomment to use instead)
# ENTRYPOINT ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "--timeout", "120", "wsgi:app"]

# Option 3: Run with waitress (uncomment to use instead)
# ENTRYPOINT ["waitress-serve", "--host=0.0.0.0", "--port=8080", "--threads=4", "wsgi:app"]

