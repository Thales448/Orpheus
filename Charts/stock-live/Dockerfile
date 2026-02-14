FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
        websockets>=11.0 \
        python-dotenv \
        pytz

# Copy only necessary application files
# Note: config.py and .env are NOT included - they should be mounted at runtime
COPY DatabaseConnection.py .
COPY ingest_live_stocks.py .
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
    LOG_LEVEL=INFO

# Health check - verifies service is running and updating healthcheck file
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os, time; \
        hc_file = '/tmp/healthcheck'; \
        if not os.path.exists(hc_file): exit(1); \
        mtime = os.path.getmtime(hc_file); \
        if time.time() - mtime > 120: exit(1); \
        exit(0)" || exit 1

# Run the live stock ingestion service
ENTRYPOINT ["python", "ingest_live_stocks.py"]

